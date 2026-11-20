"""Request-scoped dependencies: database session, auth service, current user, role checks (SAPS-27)."""

from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from saps.adapters.persistence.db import get_engine, session_factory
from saps.adapters.persistence.exception_repository import SqlExceptionUnitOfWork
from saps.adapters.persistence.invoice_repository import SqlInvoiceRepository
from saps.adapters.persistence.matching_settings_repository import SqlMatchingSettingsRepository
from saps.adapters.persistence.notification_inbox import SqlNotificationInbox
from saps.adapters.persistence.user_repository import SqlUserRepository
from saps.adapters.queue.dramatiq_queue import DramatiqJobQueue
from saps.adapters.security.argon2_hasher import Argon2PasswordHasher
from saps.adapters.storage.s3_storage import S3FileStorage
from saps.application.approval import ApprovalService
from saps.application.auth import AuthService
from saps.application.exception_handling import ExceptionHandlingService
from saps.application.matching_settings import MatchingSettingsService
from saps.application.notifications import NotificationInboxService
from saps.application.review import ReviewService
from saps.application.upload import UploadInvoiceService
from saps.config import get_settings
from saps.domain.users import AccessDeniedError, CurrentUser, Role, SessionPolicy, ensure_role
from saps.ports.file_storage import FileStoragePort
from saps.ports.invoices import InvoiceReader
from saps.ports.job_queue import JobQueuePort
from saps.worker.broker import build_broker

SESSION_COOKIE = "saps_session"


@lru_cache
def password_hasher() -> Argon2PasswordHasher:
    return Argon2PasswordHasher()


def session_policy() -> SessionPolicy:
    settings = get_settings()
    return SessionPolicy(
        idle_timeout=timedelta(minutes=settings.session_idle_timeout_minutes),
        absolute_timeout=timedelta(hours=settings.session_absolute_timeout_hours),
    )


def utc_now() -> datetime:
    return datetime.now(UTC)


async def db_session() -> AsyncIterator[AsyncSession]:
    """One transaction per request; committed when the request succeeds."""
    engine = get_engine(get_settings().database_url)
    async with session_factory(engine)() as session, session.begin():
        yield session


DbSession = Annotated[AsyncSession, Depends(db_session)]


def auth_service(session: DbSession) -> AuthService:
    return AuthService(SqlUserRepository(session), password_hasher(), session_policy(), utc_now)


Auth = Annotated[AuthService, Depends(auth_service)]

_UNAUTHORIZED = HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign-in required.")


async def current_user(request: Request, auth: Auth) -> CurrentUser:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise _UNAUTHORIZED
    user = await auth.resolve(token)
    if user is None:
        raise _UNAUTHORIZED
    return user


User = Annotated[CurrentUser, Depends(current_user)]


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


async def invoice_repository() -> SqlInvoiceRepository:
    """Async, so the engine is created on the request's event loop."""
    return SqlInvoiceRepository(session_factory(get_engine(get_settings().database_url)))


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
) -> ExceptionHandlingService:
    """SAPS-20: one transaction per operation, with its own sessions (the row lock ends with it)."""
    sessions = session_factory(get_engine(get_settings().database_url))
    return ExceptionHandlingService(SqlExceptionUnitOfWork(sessions), repository, queue, utc_now)


async def approval_service(
    repository: Annotated[SqlInvoiceRepository, Depends(invoice_repository)],
) -> ApprovalService:
    """SAPS-22: one transaction per decision; the invoice row lock makes the first decision win."""
    sessions = session_factory(get_engine(get_settings().database_url))
    return ApprovalService(SqlExceptionUnitOfWork(sessions), repository, utc_now)


async def review_service(
    repository: Annotated[SqlInvoiceRepository, Depends(invoice_repository)],
) -> ReviewService:
    """SAPS-21: one transaction per confirmation; the invoice row lock makes the first action win."""
    sessions = session_factory(get_engine(get_settings().database_url))
    return ReviewService(SqlExceptionUnitOfWork(sessions), repository, utc_now)


# --- Matching settings (SAPS-28) ------------------------------------------------------------------------


def matching_settings_service(session: DbSession) -> MatchingSettingsService:
    """Runs in the request's transaction; the settings row lock ends with it."""
    return MatchingSettingsService(SqlMatchingSettingsRepository(session))


# --- Notifications (SAPS-24) ----------------------------------------------------------------------------


def notification_service(session: DbSession) -> NotificationInboxService:
    """Runs in the request's transaction; every operation is scoped to the caller."""
    return NotificationInboxService(SqlNotificationInbox(session), utc_now)
