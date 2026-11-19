"""Idempotent seed of the PoC tenant, its matching settings and the demo users (SAPS-27 BR-09, §3.8).

Run: `python -m saps.seed` (the SAPS API container runs it after the migrations).
Skipped when SEED_USER_PASSWORD is empty.
"""

import asyncio
import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.models import MatchingSettings, Tenant, UserAccount
from saps.config import get_settings
from saps.domain.users import Role
from saps.logging_config import configure_logging
from saps.ports.auth import PasswordHasher

DEMO_TENANT = "PoC Customer"
DEMO_USERS: tuple[tuple[str, str, Role], ...] = (
    ("member1", "Accounting Member 1", Role.ACCOUNTING_MEMBER),
    ("member2", "Accounting Member 2", Role.ACCOUNTING_MEMBER),
    ("manager1", "Accounting Manager 1", Role.ACCOUNTING_MANAGER),
    ("manager2", "Accounting Manager 2", Role.ACCOUNTING_MANAGER),
)
DEFAULT_PRICE_TOLERANCE_USD = Decimal("0.5")  # DEC-006, DEC-015
DEFAULT_APPROVAL_THRESHOLD_USD = Decimal("300")  # DEC-009, DEC-015

log = logging.getLogger("saps.seed")


async def seed(session: AsyncSession, password: str, hasher: PasswordHasher) -> None:
    tenant = (await session.execute(select(Tenant).where(Tenant.name == DEMO_TENANT))).scalar_one_or_none()
    if tenant is None:
        tenant = Tenant(name=DEMO_TENANT)
        session.add(tenant)
        await session.flush()

    if await session.get(MatchingSettings, tenant.id) is None:
        session.add(
            MatchingSettings(
                tenant_id=tenant.id,
                price_tolerance_usd=DEFAULT_PRICE_TOLERANCE_USD,
                approval_threshold_usd=DEFAULT_APPROVAL_THRESHOLD_USD,
            )
        )

    password_hash = hasher.hash(password)
    for username, display_name, role in DEMO_USERS:
        user = (
            await session.execute(select(UserAccount).where(UserAccount.username == username))
        ).scalar_one_or_none()
        if user is None:
            session.add(
                UserAccount(
                    tenant_id=tenant.id,
                    username=username,
                    display_name=display_name,
                    role=role,
                    password_hash=password_hash,
                )
            )
        else:
            user.display_name, user.role, user.password_hash, user.is_active = (
                display_name,
                role,
                password_hash,
                True,
            )
    await session.flush()


async def _run(database_url: str, password: str) -> None:
    from saps.adapters.security.argon2_hasher import Argon2PasswordHasher

    engine = create_async_engine(database_url)
    try:
        async with session_factory(engine)() as session, session.begin():
            await seed(session, password, Argon2PasswordHasher())
    finally:
        await engine.dispose()


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    password = settings.seed_user_password.get_secret_value() if settings.seed_user_password else ""
    if not password:
        log.warning("seed_skipped", extra={"reason": "SEED_USER_PASSWORD is empty"})
        return
    asyncio.run(_run(settings.database_url, password))
    log.info("seed_completed", extra={"tenant": DEMO_TENANT, "users": len(DEMO_USERS)})


if __name__ == "__main__":
    main()
