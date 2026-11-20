from pathlib import Path
from uuid import uuid4

import pytest

from saps.worker import jobs


def test_only_the_dummy_adapters_exist() -> None:
    with pytest.raises(ValueError, match="Unknown ERP_ADAPTER: sap"):
        jobs.erp_adapter("sap", Path("fixtures"))
    with pytest.raises(ValueError, match="Unknown EXTRACTION_ADAPTER: ocr"):
        jobs.extraction_adapter("ocr", Path("fixtures"))


async def test_rematch_actor_runs_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    from saps.worker import actors

    called: list[object] = []

    async def fake_run(invoice_id: object) -> None:
        called.append(invoice_id)

    monkeypatch.setattr(actors, "run_matching", fake_run)
    invoice_id = uuid4()
    await actors.rematch_invoice.fn.__wrapped__(str(invoice_id))
    assert called == [invoice_id]


def test_duplicate_logs(monkeypatch: pytest.MonkeyPatch) -> None:  # SAPS-23 §3.9
    from saps.application.matching import MatchOutcome
    from saps.domain.invoices import ExceptionCode, InvoiceStatus

    messages: list[tuple[str, dict[str, object]]] = []
    monkeypatch.setattr(jobs.log, "info", lambda msg, extra: messages.append((msg, extra)))
    invoice_id, other = uuid4(), uuid4()
    found = MatchOutcome(
        invoice_id,
        uuid4(),
        None,
        InvoiceStatus.EXCEPTION,
        (ExceptionCode.EX9,),
        (ExceptionCode.EX9,),
        (),
        (other,),
    )
    cleared = MatchOutcome(
        invoice_id, uuid4(), None, InvoiceStatus.PENDING_REVIEW, (), (), (ExceptionCode.EX9,)
    )
    jobs._log_matching(found, 0.0)
    jobs._log_matching(cleared, 0.0)
    names = [m for m, _ in messages]
    assert names == ["duplicate_found", "matching_completed", "duplicate_cleared", "matching_completed"]
    assert messages[0][1] == {"invoice_id": str(invoice_id), "other_invoice_id": str(other)}
