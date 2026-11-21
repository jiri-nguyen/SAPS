"""SAPS-37 sweeper use case with in-memory ports (TS-01)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from saps.application.sweeper import BATCH_LIMIT, SweeperService
from saps.domain.invoices import InvoiceStatus
from saps.ports.sweeper import StuckInvoice
from tests.fakes import MemoryQueue

TENANT = uuid4()


class MemoryRepo:
    def __init__(self, stuck: list[StuckInvoice], locked: bool = True) -> None:
        self.stuck = stuck
        self.locked = locked
        self.asked: list[tuple[int, int]] = []
        self.marked: list[tuple[StuckInvoice, str]] = []

    async def try_lock(self) -> bool:
        return self.locked

    async def lock_stuck(self, older_than_seconds: int, limit: int) -> list[StuckInvoice]:
        self.asked.append((older_than_seconds, limit))
        return self.stuck

    async def mark_resent(self, invoice: StuckInvoice, message: str) -> None:
        self.marked.append((invoice, message))


def _uow(repo: MemoryRepo):  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def uow() -> AsyncIterator[MemoryRepo]:
        yield repo

    return uow


def _invoice(status: InvoiceStatus) -> StuckInvoice:
    return StuckInvoice(uuid4(), TENANT, status)


async def test_uploaded_gets_process_and_matching_gets_rematch() -> None:  # BR-02
    uploaded, matching = _invoice(InvoiceStatus.UPLOADED), _invoice(InvoiceStatus.MATCHING)
    repo, queue = MemoryRepo([uploaded, matching]), MemoryQueue()
    resent = await SweeperService(_uow(repo), queue, 60).sweep()
    assert (queue.sent, queue.rematch) == ([uploaded.id], [matching.id])
    assert repo.marked == [(uploaded, "process_invoice"), (matching, "rematch_invoice")]  # BR-04
    assert resent is not None and [(r.invoice_id, r.tenant_id, r.message) for r in resent] == [
        (uploaded.id, TENANT, "process_invoice"),
        (matching.id, TENANT, "rematch_invoice"),
    ]
    assert repo.asked == [(60, BATCH_LIMIT)]  # BR-01, BR-06


async def test_no_lock_means_no_sweep() -> None:  # EC-01
    repo, queue = MemoryRepo([_invoice(InvoiceStatus.UPLOADED)], locked=False), MemoryQueue()
    assert await SweeperService(_uow(repo), queue, 60).sweep() is None
    assert (queue.sent, queue.rematch, repo.asked) == ([], [], [])


async def test_nothing_stuck_is_an_empty_sweep() -> None:
    assert await SweeperService(_uow(MemoryRepo([])), MemoryQueue(), 60).sweep() == []


async def test_a_failing_send_raises_before_marking() -> None:  # EC-03
    repo = MemoryRepo([_invoice(InvoiceStatus.UPLOADED)])
    with pytest.raises(ConnectionError):
        await SweeperService(_uow(repo), MemoryQueue(fail=True), 60).sweep()
    assert repo.marked == []


async def test_the_batch_limit_is_passed_on() -> None:  # BR-06
    repo = MemoryRepo([])
    await SweeperService(_uow(repo), MemoryQueue(), 15, limit=2).sweep()
    assert repo.asked == [(15, 2)]
