from pathlib import Path
from uuid import uuid4

import pytest

from saps.worker import jobs


def test_only_the_dummy_erp_adapter_exists() -> None:
    with pytest.raises(ValueError, match="Unknown ERP_ADAPTER: sap"):
        jobs.erp_adapter("sap", Path("fixtures"))


async def test_rematch_actor_runs_matching(monkeypatch: pytest.MonkeyPatch) -> None:
    from saps.worker import actors

    called: list[object] = []

    async def fake_run(invoice_id: object) -> None:
        called.append(invoice_id)

    monkeypatch.setattr(actors, "run_matching", fake_run)
    invoice_id = uuid4()
    await actors.rematch_invoice.fn.__wrapped__(str(invoice_id))
    assert called == [invoice_id]
