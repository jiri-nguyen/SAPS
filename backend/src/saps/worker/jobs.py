"""Invoice jobs of the SAPS Worker: composition of ports and adapters, one transaction per job (ADR-0004)."""

import logging
import time
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from saps.adapters.erp.dummy_erp import DummyErpAdapter
from saps.adapters.persistence.db import get_engine, session_factory
from saps.adapters.persistence.matching_repository import SqlMatchingRepository
from saps.application.matching import MatchingService, MatchOutcome
from saps.config import get_settings
from saps.ports.erp import ErpDataPort

log = logging.getLogger("saps.worker.matching")


@lru_cache
def erp_adapter(name: str, fixtures_dir: Path) -> ErpDataPort:
    """Selected by ERP_ADAPTER; only `dummy` exists in the PoC (ADR-0001)."""
    if name != "dummy":
        raise ValueError(f"Unknown ERP_ADAPTER: {name}")
    return DummyErpAdapter(fixtures_dir)


def _utc_now() -> datetime:
    return datetime.now(UTC)


async def run_matching(invoice_id: UUID) -> MatchOutcome | None:
    """Lock the invoice, match it and commit; a stale or duplicate message changes nothing (SAPS-19 EC-03)."""
    settings = get_settings()
    started = time.perf_counter()
    erp = erp_adapter(settings.erp_adapter, settings.fixtures_dir)
    async with session_factory(get_engine(settings.database_url))() as session, session.begin():
        outcome = await MatchingService(SqlMatchingRepository(session), erp, _utc_now).match(invoice_id)
    if outcome is None:
        log.info("matching_skipped", extra={"invoice_id": str(invoice_id)})
        return None
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
    return outcome
