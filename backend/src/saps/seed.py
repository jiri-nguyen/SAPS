"""Idempotent seed of the demo companies, their matching settings and users (SAPS-27 BR-09, SAPS-42 BR-02).

Run: `python -m saps.seed` (the SAPS API container runs it after the migrations).
Skipped when SEED_USER_PASSWORD is empty: that is the password of the same demo users in Keycloak (SAPS-43);
the SAPS Database keeps no password (SAPS-44).
"""

import asyncio
import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from saps.adapters.demo.companies import DemoCompanies, load_demo_companies
from saps.adapters.persistence.db import session_factory, set_tenant
from saps.adapters.persistence.models import MatchingSettings, Tenant, UserAccount
from saps.config import get_settings
from saps.logging_config import configure_logging

LEGACY_TENANT = (
    "PoC Customer"  # the single company of the PoC; becomes the first demo company (SAPS-42 BR-05)
)
LEGACY_USERS = (
    "member1",
    "member2",
    "manager1",
)  # renamed to the e-mail style of that company; manager2 is kept
DEFAULT_PRICE_TOLERANCE_USD = Decimal("0.5")  # DEC-006, DEC-015
DEFAULT_APPROVAL_THRESHOLD_USD = Decimal("300")  # DEC-009, DEC-015

log = logging.getLogger("saps.seed")


async def seed(session: AsyncSession, companies: DemoCompanies) -> tuple[int, int]:
    """Create or update the demo companies, their matching settings and users; idempotent (SAPS-42 BR-02).

    Returns the number of companies and users seeded.
    """
    users = 0
    for index, company in enumerate(companies.companies):
        tenant = (
            await session.execute(select(Tenant).where(Tenant.code == company.code))
        ).scalar_one_or_none()
        legacy = None
        if tenant is None and index == 0:
            legacy = (
                await session.execute(select(Tenant).where(Tenant.name == LEGACY_TENANT))
            ).scalar_one_or_none()
            tenant = legacy
        if tenant is None:
            tenant = Tenant(name=company.name, code=company.code)
            session.add(tenant)
        tenant.name = company.name
        tenant.code = company.code
        tenant.email_domain = company.email_domain
        tenant.keycloak_group = company.keycloak_group
        tenant.mailbox_address = company.mailbox_address
        tenant.time_zone = company.time_zone
        await session.flush()
        # The rows below are tenant-owned: set the company, so this also works for a migration user that is
        # not a superuser and therefore is subject to row-level security (SAPS-41, Amazon RDS).
        await set_tenant(session, tenant.id)

        if await session.get(MatchingSettings, tenant.id) is None:
            session.add(
                MatchingSettings(
                    tenant_id=tenant.id,
                    price_tolerance_usd=DEFAULT_PRICE_TOLERANCE_USD,
                    approval_threshold_usd=DEFAULT_APPROVAL_THRESHOLD_USD,
                )
            )
        if legacy is not None:
            await _rename_legacy_users(session, tenant.id, company.email_domain)

        for demo_user in company.users:
            user = (
                await session.execute(select(UserAccount).where(UserAccount.username == demo_user.username))
            ).scalar_one_or_none()
            if user is None:
                session.add(
                    UserAccount(
                        tenant_id=tenant.id,
                        username=demo_user.username,
                        display_name=demo_user.display_name,
                        role=demo_user.role,
                        email=demo_user.username.lower(),
                    )
                )
            else:
                user.display_name, user.role, user.is_active = demo_user.display_name, demo_user.role, True
                user.email = user.email or demo_user.username.lower()
            users += 1
        await session.flush()
    return len(companies.companies), users


async def _rename_legacy_users(session: AsyncSession, tenant_id: UUID, domain: str) -> None:
    for username in LEGACY_USERS:
        user = (
            await session.execute(
                select(UserAccount).where(
                    UserAccount.tenant_id == tenant_id, UserAccount.username == username
                )
            )
        ).scalar_one_or_none()
        if user is not None:
            user.username = f"{username}@{domain}"
            user.email = user.username


async def _run(database_url: str) -> tuple[int, int]:
    companies = load_demo_companies(get_settings().fixtures_dir)
    engine = create_async_engine(database_url)
    try:
        async with session_factory(engine)() as session, session.begin():
            return await seed(session, companies)
    finally:
        await engine.dispose()


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    password = settings.seed_user_password.get_secret_value() if settings.seed_user_password else ""
    if not password:
        log.warning("seed_skipped", extra={"reason": "SEED_USER_PASSWORD is empty"})
        return
    companies, users = asyncio.run(_run(settings.database_url))
    log.info("seed_completed", extra={"companies": companies, "users": users})


if __name__ == "__main__":
    main()
