"""Shared helpers for integration tests of the invoice pipeline (SAPS-18, SAPS-19, SAPS-23)."""

import hashlib
import uuid
from datetime import UTC, datetime
from pathlib import Path

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
from saps.domain.users import Role

FIXTURES = Path(__file__).parents[2] / "fixtures"
EXTRACTION = DummyExtractionAdapter(FIXTURES)
ERP = DummyErpAdapter(FIXTURES)
NO_LOGIN = "!"


def _file_info(file: Path) -> tuple[str, int]:
    return hashlib.sha256(file.read_bytes()).hexdigest(), file.stat().st_size


async def new_tenant(engine: AsyncEngine) -> tuple[uuid.UUID, uuid.UUID]:
    """A fresh tenant with one member and one manager, so scenarios never share PO quantities (ADR-0007)."""
    async with session_factory(engine)() as session, session.begin():
        tenant = Tenant(name=f"Test tenant {uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()
        session.add(MatchingSettings(tenant_id=tenant.id))
        member = UserAccount(
            tenant_id=tenant.id, username=f"m-{uuid.uuid4().hex[:10]}", display_name="Member",
            password_hash=NO_LOGIN, role=Role.ACCOUNTING_MEMBER,
        )  # fmt: skip
        manager = UserAccount(
            tenant_id=tenant.id, username=f"g-{uuid.uuid4().hex[:10]}", display_name="Manager",
            password_hash=NO_LOGIN, role=Role.ACCOUNTING_MANAGER,
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
