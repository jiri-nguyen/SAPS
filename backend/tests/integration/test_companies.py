"""Integration: SAPS-42 demo companies and per-company ERP data on a real PostgreSQL (TS-01, TS-03, TS-04)."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

from saps.adapters.demo.companies import DemoCompanies, DemoCompany, DemoUser
from saps.adapters.erp.dummy_erp import DummyErpAdapter
from saps.adapters.persistence.db import session_factory, set_tenant
from saps.adapters.persistence.matching_repository import SqlMatchingRepository
from saps.adapters.persistence.models import Invoice, MatchingSettings, Tenant, UserAccount
from saps.adapters.persistence.processing_repository import SqlProcessingRepository
from saps.application.matching import MatchingService
from saps.application.processing import ProcessInvoiceService
from saps.domain.invoices import InvoiceStatus
from saps.domain.users import Role
from saps.seed import LEGACY_TENANT, seed
from saps.seed import _run as run_seed
from tests.integration.pipeline import EXTRACTION, FIXTURES, uploaded

pytestmark = pytest.mark.integration

DS01 = FIXTURES / "ds-01/invoices/ds-01-trade-po.pdf"
ERP = DummyErpAdapter(FIXTURES)


def _clock() -> datetime:
    return datetime.now(UTC)


def _companies(*codes: str) -> DemoCompanies:
    return DemoCompanies(
        companies=[
            DemoCompany(
                code=code,
                name=f"Demo {code.upper()}",
                email_domain=f"{code}.example.com",
                keycloak_group=f"/companies/{code}",
                mailbox_address=f"ap@{code}.example.com",
                time_zone="Asia/Singapore",
                users=[
                    DemoUser(
                        username=f"member1@{code}.example.com", display_name="M1", role=Role.ACCOUNTING_MEMBER
                    ),
                    DemoUser(
                        username=f"manager1@{code}.example.com",
                        display_name="G1",
                        role=Role.ACCOUNTING_MANAGER,
                    ),
                ],
                erp=["ds-*/erp/*.json"],
            )
            for code in codes
        ]
    )


async def _seed(engine: AsyncEngine, companies: DemoCompanies) -> tuple[int, int]:
    async with session_factory(engine)() as session, session.begin():
        return await seed(session, companies)


# TS-01 / BR-02, BR-05, EC-04 ----------------------------------------------------------------------


async def test_a_poc_database_becomes_the_first_demo_company(engine: AsyncEngine) -> None:
    suffix = uuid.uuid4().hex[:6]
    first, second = f"p{suffix}", f"q{suffix}"
    async with session_factory(engine)() as session, session.begin():  # the PoC: one tenant, four demo users
        poc = Tenant(name=LEGACY_TENANT, code=f"tenant-{suffix}")
        session.add(poc)
        await session.flush()
        session.add(MatchingSettings(tenant_id=poc.id))
        for username, role in (
            ("member1", Role.ACCOUNTING_MEMBER),
            ("member2", Role.ACCOUNTING_MEMBER),
            ("manager1", Role.ACCOUNTING_MANAGER),
            ("manager2", Role.ACCOUNTING_MANAGER),
        ):
            session.add(
                UserAccount(
                    tenant_id=poc.id,
                    username=username,
                    display_name=username,
                    role=role,
                )
            )
        poc_id = poc.id
    member = await _username_id(engine, "member1")
    invoice_id = await uploaded(engine, DS01, (poc_id, member))

    assert await _seed(engine, _companies(first, second)) == (2, 4)
    assert await _seed(engine, _companies(first, second)) == (2, 4)  # idempotent

    async with session_factory(engine)() as session:
        tenants = (
            (
                await session.execute(
                    select(Tenant).where(Tenant.code.in_([first, second])).order_by(Tenant.code)
                )
            )
            .scalars()
            .all()
        )
        assert [t.code for t in tenants] == [first, second]
        assert tenants[0].id == poc_id  # the PoC company was kept, not duplicated
        assert (
            tenants[0].name,
            tenants[0].email_domain,
            tenants[0].mailbox_address,
            tenants[0].time_zone,
        ) == (
            f"Demo {first.upper()}",
            f"{first}.example.com",
            f"ap@{first}.example.com",
            "Asia/Singapore",
        )
        names = sorted(
            (
                await session.execute(select(UserAccount.username).where(UserAccount.tenant_id == poc_id))
            ).scalars()
        )
        assert names == sorted(
            [
                f"manager1@{first}.example.com",
                "manager2",
                f"member1@{first}.example.com",
                f"member2@{first}.example.com",
            ]
        )  # renamed, manager2 kept
        assert await session.scalar(select(Invoice.tenant_id).where(Invoice.id == invoice_id)) == poc_id
        assert await session.get(MatchingSettings, tenants[1].id) is not None


async def _username_id(engine: AsyncEngine, username: str) -> uuid.UUID:
    async with session_factory(engine)() as session:
        user_id = await session.scalar(select(UserAccount.id).where(UserAccount.username == username))
    assert user_id is not None
    return user_id


# TS-03 / BR-03, BR-04, EC-01 ----------------------------------------------------------------------


async def _company(engine: AsyncEngine, code: str) -> tuple[uuid.UUID, uuid.UUID]:
    async with session_factory(engine)() as session:
        tenant_id = await session.scalar(select(Tenant.id).where(Tenant.code == code))
    assert tenant_id is not None
    return tenant_id, await _username_id(engine, f"member1@{code}.example.com")


async def _process(engine: AsyncEngine, invoice_id: uuid.UUID, tenant_id: uuid.UUID) -> InvoiceStatus:
    """What the SAPS Worker does, with the real per-company ERP adapter."""
    async with session_factory(engine)() as session, session.begin():
        await set_tenant(session, tenant_id)
        matching = MatchingService(SqlMatchingRepository(session), ERP, _clock)
        outcome = await ProcessInvoiceService(
            SqlProcessingRepository(session), EXTRACTION, matching, _clock
        ).process(invoice_id)
    assert outcome is not None and outcome.matching is not None
    return outcome.matching.status


async def test_each_company_matches_against_its_own_erp_data(engine: AsyncEngine, database_url: str) -> None:
    await run_seed(database_url)
    vn, sg = await _company(engine, "vn"), await _company(engine, "sg")

    first_vn = await uploaded(engine, DS01, vn)
    assert await _process(engine, first_vn, vn[0]) is InvoiceStatus.PENDING_REVIEW
    same_in_sg = await uploaded(engine, DS01, sg)  # same sample file, other company (BR-04)
    assert (
        await _process(engine, same_in_sg, sg[0]) is InvoiceStatus.PENDING_REVIEW
    )  # no EX9, quantities not used
    second_vn = await uploaded(engine, DS01, vn)
    assert (
        await _process(engine, second_vn, vn[0]) is InvoiceStatus.EXCEPTION
    )  # in VN: duplicate, quantity taken


# TS-04 / EC-05 ------------------------------------------------------------------------------------


@pytest.mark.parametrize("field", ["code", "email_domain", "keycloak_group", "mailbox_address"])
async def test_company_details_are_unique(engine: AsyncEngine, field: str) -> None:
    suffix = uuid.uuid4().hex[:8]
    values = {
        "code": f"u{suffix}",
        "email_domain": f"{suffix}.example.com",
        "keycloak_group": f"/companies/{suffix}",
        "mailbox_address": f"ap@{suffix}.example.com",
    }
    async with session_factory(engine)() as session, session.begin():
        session.add(Tenant(name=f"Unique {suffix} A", **values))
    clash = {
        "code": f"v{suffix}",
        "email_domain": f"other-{suffix}.example.com",
        "keycloak_group": f"/companies/other-{suffix}",
        "mailbox_address": f"ap@other-{suffix}.example.com",
        field: values[field],
    }
    with pytest.raises(IntegrityError):
        async with session_factory(engine)() as session, session.begin():
            session.add(Tenant(name=f"Unique {suffix} B", **clash))
