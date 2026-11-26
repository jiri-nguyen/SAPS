"""Request-scoped dependencies: database session, auth service, current user, role checks (SAPS-27)."""

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from saps.adapters.identity.oidc import OidcIdentityProvider
from saps.adapters.persistence.db import get_engine, session_factory, set_tenant
from saps.adapters.persistence.exception_repository import SqlExceptionUnitOfWork
from saps.adapters.persistence.invoice_repository import SqlInvoiceRepository
from saps.adapters.persistence.matching_settings_repository import SqlMatchingSettingsRepository
from saps.adapters.persistence.notification_inbox import SqlNotificationInbox
from saps.adapters.persistence.processing_calendar_repository import (
    SqlHoldUnitOfWork,
    SqlProcessingCalendarRepository,
)
from saps.adapters.persistence.user_repository import SqlUserRepository
from saps.adapters.queue.dramatiq_queue import DramatiqJobQueue
from saps.adapters.security.fernet_cipher import FernetTokenCipher
from saps.adapters.storage.s3_storage import S3FileStorage
from saps.application.approval import ApprovalService
from saps.application.auth import AuthService
from saps.application.exception_handling import ExceptionHandlingService
from saps.application.matching_settings import MatchingSettingsService
from saps.application.notifications import NotificationInboxService
from saps.application.processing_calendar import InvoiceHoldService, ProcessingCalendarService
from saps.application.upload import UploadInvoiceService
from saps.config import get_settings
from saps.domain.users import AccessDeniedError, CurrentUser, Role, SessionPolicy, ensure_role
from saps.ports.file_storage import FileStoragePort
from saps.ports.identity import IdentityProvider, IdentityProviderUnavailableError, TokenCipher
from saps.ports.invoices import InvoiceReader
from saps.ports.job_queue import JobQueuePort
from saps.worker.broker import build_broker

SESSION_COOKIE = "saps_session"
CALLBACK_PATH = "/v1/session/callback"


@lru_cache
def identity_provider() -> IdentityProvider:
    """One per process: it caches the discovery document and the signing keys (SAPS-44)."""
    settings = get_settings()
    origin = settings.web_app_origin.rstrip("/")
    return OidcIdentityProvider(
        discovery_url=settings.oidc_discovery_url,
        issuer=settings.oidc_issuer,
        client_id=settings.oidc_client_id,
        client_secret=settings.oidc_client_secret.get_secret_value(),
        redirect_uri=f"{origin}{CALLBACK_PATH}",
        post_logout_redirect_uri=f"{origin}/",
        groups_claim=settings.oidc_groups_claim,
        roles_claim=settings.oidc_roles_claim,
    )


@lru_cache
def token_cipher() -> TokenCipher:
    key = get_settings().session_encryption_key
    if key is None or not key.get_secret_value():
        raise RuntimeError("SESSION_ENCRYPTION_KEY is not set (Developer Guide §6)")
    return FernetTokenCipher(key.get_secret_value())


def session_policy() -> SessionPolicy:
    settings = get_settings()
    return SessionPolicy(
        idle_timeout=timedelta(minutes=settings.session_idle_timeout_minutes),
        absolute_timeout=timedelta(hours=settings.session_absolute_timeout_hours),
    )


def utc_now() -> datetime:
    return datetime.now(UTC)


def app_engine() -> AsyncEngine:
    """The SAPS API connects as `saps_app`: row-level security applies to every query (SAPS-41)."""
    return get_engine(get_settings().app_database_url)


async def db_session() -> AsyncIterator[AsyncSession]:
    """One transaction per request; committed when the request succeeds. The company is set once the user is
    known (`tenant_session`); sign-in and session lookups set it themselves (SAPS-41 BR-05)."""
    async with session_factory(app_engine())() as session, session.begin():
        yield session


DbSession = Annotated[AsyncSession, Depends(db_session)]


def auth_service(
    session: DbSession,
    provider: Annotated[IdentityProvider, Depends(identity_provider)],
    cipher: Annotated[TokenCipher, Depends(token_cipher)],
) -> AuthService:
    return AuthService(SqlUserRepository(session), provider, cipher, session_policy(), utc_now)


Auth = Annotated[AuthService, Depends(auth_service)]

_UNAUTHORIZED = HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign-in required.")


async def current_user(request: Request, session: DbSession, auth: Auth) -> CurrentUser:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise _UNAUTHORIZED
    try:
        user = await auth.resolve(token)
    except IdentityProviderUnavailableError as exc:  # the session is kept (SAPS-44 EC-08)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Sign-in service not reachable. Try again."
        ) from exc
    if user is None:
        # A session ended by a refused refresh stays ended: keep the revocation although the request fails.
        await session.commit()
        raise _UNAUTHORIZED
    return user


User = Annotated[CurrentUser, Depends(current_user)]


async def tenant_session(session: DbSession, user: User) -> AsyncSession:
    """The request's transaction, limited to the signed-in user's company (SAPS-41)."""
    await set_tenant(session, user.tenant_id)
    return session


TenantDb = Annotated[AsyncSession, Depends(tenant_session)]


def require_roles(*roles: Role) -> Callable[[CurrentUser], Awaitable[CurrentUser]]:
    """Dependency enforcing the operation's `x-roles` (SAPS-27 BR-07)."""

    async def check(user: User) -> CurrentUser:
        try:
            ensure_role(user, roles)
        except AccessDeniedError as exc:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, "Your role is not allowed for this operation."
            ) from exc
        return user

    return check


# --- Invoices (SAPS-17) ---------------------------------------------------------------------------------


@lru_cache
def file_storage() -> FileStoragePort:
    settings = get_settings()
    return S3FileStorage(
        endpoint_url=settings.s3_endpoint_url,
        bucket=settings.s3_bucket,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key.get_secret_value(),
    )


@lru_cache
def job_queue() -> JobQueuePort:
    return DramatiqJobQueue(build_broker(get_settings()))


async def invoice_repository(user: User) -> SqlInvoiceRepository:
    """Async, so the engine is created on the request's event loop; sessions of the user's company."""
    return SqlInvoiceRepository(session_factory(app_engine(), user.tenant_id))


async def invoice_reader(
    repository: Annotated[SqlInvoiceRepository, Depends(invoice_repository)],
) -> InvoiceReader:
    return repository


async def upload_service(
    repository: Annotated[SqlInvoiceRepository, Depends(invoice_repository)],
    storage: Annotated[FileStoragePort, Depends(file_storage)],
    queue: Annotated[JobQueuePort, Depends(job_queue)],
) -> UploadInvoiceService:
    max_size_bytes = get_settings().max_upload_size_mb * 1024 * 1024
    return UploadInvoiceService(repository, repository, storage, queue, utc_now, max_size_bytes)


async def exception_service(
    repository: Annotated[SqlInvoiceRepository, Depends(invoice_repository)],
    queue: Annotated[JobQueuePort, Depends(job_queue)],
    user: User,
) -> ExceptionHandlingService:
    """SAPS-20: one transaction per operation, with its own sessions (the row lock ends with it)."""
    sessions = session_factory(app_engine(), user.tenant_id)
    return ExceptionHandlingService(SqlExceptionUnitOfWork(sessions), repository, queue, utc_now)


async def approval_service(
    repository: Annotated[SqlInvoiceRepository, Depends(invoice_repository)],
    user: User,
    queue: Annotated[JobQueuePort, Depends(job_queue)],
) -> ApprovalService:
    """SAPS-22: one transaction per decision; the invoice row lock makes the first decision win."""
    sessions = session_factory(app_engine(), user.tenant_id)
    return ApprovalService(SqlExceptionUnitOfWork(sessions), repository, queue, utc_now)


# --- Processing calendar (SAPS-52) -------------------------------------------------------------------------


def processing_calendar_service(session: TenantDb) -> ProcessingCalendarService:
    """Runs in the request's transaction: the Accounting Manager's change applies at once (BR-07)."""
    return ProcessingCalendarService(SqlProcessingCalendarRepository(session), utc_now)


async def invoice_hold_service(
    user: User, queue: Annotated[JobQueuePort, Depends(job_queue)]
) -> InvoiceHoldService:
    """Process now: one transaction, the invoice row locked, then the message is sent (SAPS-52 BR-06)."""
    sessions = session_factory(app_engine(), user.tenant_id)
    return InvoiceHoldService(SqlHoldUnitOfWork(sessions), queue, utc_now)


# --- Matching settings (SAPS-28) ------------------------------------------------------------------------


def matching_settings_service(session: TenantDb) -> MatchingSettingsService:
    """Runs in the request's transaction; the settings row lock ends with it."""
    return MatchingSettingsService(SqlMatchingSettingsRepository(session))


# --- Notifications (SAPS-24) ----------------------------------------------------------------------------


def notification_service(session: TenantDb) -> NotificationInboxService:
    """Runs in the request's transaction; every operation is scoped to the caller."""
    return NotificationInboxService(SqlNotificationInbox(session), utc_now)
