"""Shared helpers for integration tests of the invoice pipeline (SAPS-18, SAPS-19, SAPS-23)."""

import hashlib
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from saps.adapters.erp.dummy_erp import DummyErpAdapter
from saps.adapters.extraction.dummy_extraction import DummyExtractionAdapter
from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.matching_repository import SqlMatchingRepository
from saps.adapters.persistence.models import Invoice, MatchingSettings, Tenant, UserAccount
from saps.adapters.persistence.processing_repository import SqlProcessingRepository
from saps.application.matching import MatchingService, MatchOutcome
from saps.application.processing import ProcessInvoiceService, ProcessOutcome
from saps.domain.invoices import InvoiceStatus
from saps.domain.matching import GoodsReceiptLine, PurchaseOrder, PurchasingInfoRecord
from saps.domain.users import CurrentUser, Role

FIXTURES = Path(__file__).parents[2] / "fixtures"
EXTRACTION = DummyExtractionAdapter(FIXTURES)


class _AnyCompanyErp:
    """Serves the `vn` demo catalogue to every company: the test companies have random codes (SAPS-42); ERP
    selection per company is tested in test_dummy_erp and test_companies."""

    def __init__(self, erp: DummyErpAdapter, company: str = "vn") -> None:
        self._erp, self._company = erp, company

    async def get_purchase_orders(
        self, company_code: str, po_numbers: Sequence[str]
    ) -> dict[str, PurchaseOrder]:
        return await self._erp.get_purchase_orders(self._company, po_numbers)

    async def get_goods_receipt_lines(
        self, company_code: str, po_numbers: Sequence[str]
    ) -> list[GoodsReceiptLine]:
        return await self._erp.get_goods_receipt_lines(self._company, po_numbers)

    async def get_purchasing_info_records(
        self, company_code: str, keys: Sequence[tuple[str, str]]
    ) -> list[PurchasingInfoRecord]:
        return await self._erp.get_purchasing_info_records(self._company, keys)


ERP = _AnyCompanyErp(DummyErpAdapter(FIXTURES))


def _file_info(file: Path) -> tuple[str, int]:
    return hashlib.sha256(file.read_bytes()).hexdigest(), file.stat().st_size


async def new_tenant(engine: AsyncEngine) -> tuple[uuid.UUID, uuid.UUID]:
    """A fresh tenant with one member and one manager, so scenarios never share PO quantities (ADR-0007)."""
    async with session_factory(engine)() as session, session.begin():
        suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(name=f"Test tenant {suffix}", code=f"t-{suffix}")
        session.add(tenant)
        await session.flush()
        session.add(MatchingSettings(tenant_id=tenant.id))
        member = UserAccount(
            tenant_id=tenant.id, username=f"m-{uuid.uuid4().hex[:10]}", display_name="Member",
            role=Role.ACCOUNTING_MEMBER,
        )  # fmt: skip
        manager = UserAccount(
            tenant_id=tenant.id, username=f"g-{uuid.uuid4().hex[:10]}", display_name="Manager",
            role=Role.ACCOUNTING_MANAGER,
        )  # fmt: skip
        session.add_all([member, manager])
        await session.flush()
        return tenant.id, member.id


async def uploaded(
    engine: AsyncEngine, file: Path, tenant: tuple[uuid.UUID, uuid.UUID] | None = None
) -> uuid.UUID:
    """An Uploaded invoice for a sample file, in a new tenant unless one is given."""
    tenant_id, member_id = tenant or await new_tenant(engine)
    sha, size = _file_info(file)
    async with session_factory(engine)() as session, session.begin():
        invoice = Invoice(
            tenant_id=tenant_id, status=InvoiceStatus.UPLOADED, uploaded_by=member_id, file_name=file.name,
            file_content_type="application/pdf", file_size_bytes=size, file_sha256=sha,
            file_storage_key=f"invoices/x/{sha}", idempotency_key=uuid.uuid4().hex,
        )  # fmt: skip
        session.add(invoice)
        await session.flush()
        return invoice.id


async def process(engine: AsyncEngine, invoice_id: uuid.UUID) -> ProcessOutcome | None:
    async with session_factory(engine)() as session, session.begin():
        clock = lambda: datetime.now(UTC)  # noqa: E731
        matching = MatchingService(SqlMatchingRepository(session), ERP, clock)
        service = ProcessInvoiceService(SqlProcessingRepository(session), EXTRACTION, matching, clock)
        return await service.process(invoice_id)


async def rematch(engine: AsyncEngine, invoice_id: uuid.UUID) -> MatchOutcome | None:
    async with session_factory(engine)() as session, session.begin():
        clock = lambda: datetime.now(UTC)  # noqa: E731
        return await MatchingService(SqlMatchingRepository(session), ERP, clock).match(invoice_id)


@dataclass(frozen=True)
class World:
    """One tenant with two Accounting Members and one Accounting Manager (SAPS-20 tests)."""

    tenant: tuple[uuid.UUID, uuid.UUID]  # (tenant id, first member id), as `uploaded` expects
    alice: CurrentUser
    bob: CurrentUser
    manager: CurrentUser
    manager2: CurrentUser


async def new_world(engine: AsyncEngine) -> World:
    tenant_id, alice_id = await new_tenant(engine)
    async with session_factory(engine)() as session, session.begin():
        bob = UserAccount(
            tenant_id=tenant_id, username=f"b-{uuid.uuid4().hex[:10]}", display_name="Bob",
            role=Role.ACCOUNTING_MEMBER,
        )  # fmt: skip
        manager2 = UserAccount(
            tenant_id=tenant_id, username=f"h-{uuid.uuid4().hex[:10]}", display_name="Second Manager",
            role=Role.ACCOUNTING_MANAGER,
        )  # fmt: skip
        session.add_all([bob, manager2])
        await session.flush()
        users = (
            (await session.execute(select(UserAccount).where(UserAccount.tenant_id == tenant_id)))
            .scalars()
            .all()
        )
        by_id = {u.id: u for u in users}

    def current(user: UserAccount) -> CurrentUser:
        return CurrentUser(user.id, tenant_id, user.username, user.display_name, user.role)

    managers = {u.display_name: u for u in users if u.role is Role.ACCOUNTING_MANAGER}
    return World(
        (tenant_id, alice_id),
        current(by_id[alice_id]),
        current(bob),
        current(managers["Manager"]),
        current(managers["Second Manager"]),
    )
