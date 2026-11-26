"""Invoice jobs of the SAPS Worker: composition of ports and adapters, one transaction per job (ADR-0004)."""

import logging
import time
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from saps.adapters.erp.dummy_erp import DummyErpAdapter
from saps.adapters.extraction.dummy_extraction import DummyExtractionAdapter
from saps.adapters.persistence.db import get_engine, session_factory
from saps.adapters.persistence.matching_repository import SqlMatchingRepository
from saps.adapters.persistence.models import Invoice
from saps.adapters.persistence.processing_repository import SqlProcessingRepository
from saps.application.matching import MatchingService, MatchOutcome
from saps.application.processing import FailedProcessingService, ProcessInvoiceService, ProcessOutcome
from saps.config import Settings, get_settings
from saps.domain.invoices import ExceptionCode
from saps.ports.erp import ErpDataPort
from saps.ports.extraction import ExtractionPort

log = logging.getLogger("saps.worker.matching")
processing_log = logging.getLogger("saps.worker.processing")


@lru_cache
def erp_adapter(name: str, fixtures_dir: Path) -> ErpDataPort:
    """Selected by ERP_ADAPTER; only `dummy` exists in the PoC (ADR-0001)."""
    if name != "dummy":
        raise ValueError(f"Unknown ERP_ADAPTER: {name}")
    return DummyErpAdapter(fixtures_dir)


@lru_cache
def extraction_adapter(name: str, fixtures_dir: Path) -> ExtractionPort:
    """Selected by EXTRACTION_ADAPTER; only `dummy` exists in the PoC (ADR-0001, DEC-012)."""
    if name != "dummy":
        raise ValueError(f"Unknown EXTRACTION_ADAPTER: {name}")
    return DummyExtractionAdapter(fixtures_dir)


def load_adapters(settings: Settings) -> None:
    """Build the adapters at worker start-up: broken fixtures stop the worker before any job (EC-04)."""
    extraction_adapter(settings.extraction_adapter, settings.fixtures_dir)
    erp_adapter(settings.erp_adapter, settings.fixtures_dir)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _log_matching(outcome: MatchOutcome, started: float) -> None:
    for other in outcome.duplicate_of:
        log.info(
            "duplicate_found", extra={"invoice_id": str(outcome.invoice_id), "other_invoice_id": str(other)}
        )
    if ExceptionCode.EX9 in outcome.resolved:
        log.info("duplicate_cleared", extra={"invoice_id": str(outcome.invoice_id)})
    log.info(
        "matching_completed",
        extra={
            "invoice_id": str(outcome.invoice_id),
            "tenant_id": str(outcome.tenant_id),
            "invoice_type": outcome.invoice_type.value if outcome.invoice_type else None,
            "status": outcome.status.value,
            "exception_codes": [code.value for code in outcome.open_codes],
            "duration_ms": round((time.perf_counter() - started) * 1000),
        },
    )


async def tenant_of(invoice_id: UUID, tenant_id: UUID | None) -> UUID | None:
    """The company of a job.

    Messages sent before SAPS-41 carry no company: it is read once with the system role (EC-05; accepted for
    one release). None when the invoice does not exist.
    """
    if tenant_id is not None:
        return tenant_id
    log.info("message_without_tenant", extra={"invoice_id": str(invoice_id)})
    async with session_factory(get_engine(get_settings().system_database_url))() as session:
        found: UUID | None = await session.scalar(select(Invoice.tenant_id).where(Invoice.id == invoice_id))
    return found


def _sessions(tenant_id: UUID) -> async_sessionmaker[AsyncSession]:
    """Sessions of the job's company on the `saps_app` connection (SAPS-41)."""
    return session_factory(get_engine(get_settings().app_database_url), tenant_id)


async def run_matching(invoice_id: UUID, tenant_id: UUID | None = None) -> MatchOutcome | None:
    """Lock the invoice, match it and commit; a stale or duplicate message changes nothing (SAPS-19 EC-03)."""
    settings = get_settings()
    started = time.perf_counter()
    erp = erp_adapter(settings.erp_adapter, settings.fixtures_dir)
    tenant = await tenant_of(invoice_id, tenant_id)
    if tenant is None:
        log.info("matching_skipped", extra={"invoice_id": str(invoice_id)})
        return None
    async with _sessions(tenant)() as session, session.begin():
        outcome = await MatchingService(SqlMatchingRepository(session), erp, _utc_now).match(invoice_id)
    if outcome is None:
        log.info("matching_skipped", extra={"invoice_id": str(invoice_id)})
        return None
    _log_matching(outcome, started)
    return outcome


async def run_processing(invoice_id: UUID, tenant_id: UUID | None = None) -> ProcessOutcome | None:
    """`process_invoice`: extraction, then matching, in one transaction (SAPS-18 BR-01, ADR-0004)."""
    settings = get_settings()
    started = time.perf_counter()
    extraction = extraction_adapter(settings.extraction_adapter, settings.fixtures_dir)
    erp = erp_adapter(settings.erp_adapter, settings.fixtures_dir)
    tenant = await tenant_of(invoice_id, tenant_id)
    if tenant is None:
        processing_log.info("processing_skipped", extra={"invoice_id": str(invoice_id)})
        return None
    async with _sessions(tenant)() as session, session.begin():
        matching = MatchingService(SqlMatchingRepository(session), erp, _utc_now)
        service = ProcessInvoiceService(SqlProcessingRepository(session), extraction, matching, _utc_now)
        outcome = await service.process(invoice_id)
    if outcome is None:
        processing_log.info("processing_skipped", extra={"invoice_id": str(invoice_id)})
        return None
    if outcome.held:  # SAPS-52 BR-03: received on a closed day, nothing was extracted or matched
        processing_log.info(
            "invoice_held", extra={"invoice_id": str(outcome.invoice_id), "tenant_id": str(outcome.tenant_id)}
        )
        return outcome
    processing_log.info(
        "extraction_completed",
        extra={
            "invoice_id": str(outcome.invoice_id),
            "tenant_id": str(outcome.tenant_id),
            "found": outcome.found,
            "line_count": outcome.line_count,
            "unreadable_reason": outcome.unreadable_reason,
            "duration_ms": round((time.perf_counter() - started) * 1000),
        },
    )
    if outcome.matching is not None:
        _log_matching(outcome.matching, started)
    return outcome


async def run_failure(invoice_id: UUID, reason: str, tenant_id: UUID | None = None) -> bool:
    """`process_invoice_failed`: EX1 after the last retry in a new transaction (SAPS-38).

    Never raises: a failure here is logged and the invoice stays in Uploaded for the sweeper (EC-04).
    """
    try:
        tenant = await tenant_of(invoice_id, tenant_id)
        if tenant is None:
            processing_log.info("process_failure_skipped", extra={"invoice_id": str(invoice_id)})
            return False
        async with _sessions(tenant)() as session, session.begin():
            raised = await FailedProcessingService(SqlProcessingRepository(session), _utc_now).fail(
                invoice_id, reason
            )
    except Exception:
        processing_log.exception("process_failure_not_recorded", extra={"invoice_id": str(invoice_id)})
        return False
    if raised:
        processing_log.info(
            "process_failure_recorded", extra={"invoice_id": str(invoice_id), "reason": reason}
        )
    else:
        processing_log.info("process_failure_skipped", extra={"invoice_id": str(invoice_id)})
    return raised
