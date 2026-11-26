"""SAPS-37 sweeper use case with in-memory ports (TS-01)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import pytest

from saps.application.sweeper import BATCH_LIMIT, GaveUp, SweeperService, SweepResult
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
        self.gave_up: list[StuckInvoice] = []

    async def try_lock(self) -> bool:
        return self.locked

    async def lock_stuck(self, older_than_seconds: int, limit: int) -> list[StuckInvoice]:
        self.asked.append((older_than_seconds, limit))
        return self.stuck

    async def mark_resent(self, invoice: StuckInvoice, message: str) -> None:
        self.marked.append((invoice, message))

    async def mark_gave_up(self, invoice: StuckInvoice) -> None:
        self.gave_up.append(invoice)


def _uow(repo: MemoryRepo):  # type: ignore[no-untyped-def]
    @asynccontextmanager
    async def uow() -> AsyncIterator[MemoryRepo]:
        yield repo

    return uow


def _invoice(status: InvoiceStatus, resends: int = 0) -> StuckInvoice:
    return StuckInvoice(uuid4(), TENANT, status, resends)


async def test_uploaded_gets_process_and_matching_gets_rematch() -> None:  # BR-02
    uploaded, matching = _invoice(InvoiceStatus.UPLOADED), _invoice(InvoiceStatus.MATCHING)
    repo, queue = MemoryRepo([uploaded, matching]), MemoryQueue()
    result = await SweeperService(_uow(repo), queue, 60).sweep()
    assert (queue.sent, queue.rematch) == ([uploaded.id], [matching.id])
    assert repo.marked == [(uploaded, "process_invoice"), (matching, "rematch_invoice")]  # BR-04
    assert result is not None and [(r.invoice_id, r.tenant_id, r.message) for r in result.resent] == [
        (uploaded.id, TENANT, "process_invoice"),
        (matching.id, TENANT, "rematch_invoice"),
    ]
    assert repo.asked == [(60, BATCH_LIMIT)]  # BR-01, BR-06


async def test_no_lock_means_no_sweep() -> None:  # EC-01
    repo, queue = MemoryRepo([_invoice(InvoiceStatus.UPLOADED)], locked=False), MemoryQueue()
    assert await SweeperService(_uow(repo), queue, 60).sweep() is None
    assert (queue.sent, queue.rematch, repo.asked) == ([], [], [])


async def test_nothing_stuck_is_an_empty_sweep() -> None:
    assert await SweeperService(_uow(MemoryRepo([])), MemoryQueue(), 60).sweep() == SweepResult([], [])


async def test_a_failing_send_raises_before_marking() -> None:  # EC-03
    repo = MemoryRepo([_invoice(InvoiceStatus.UPLOADED)])
    with pytest.raises(ConnectionError):
        await SweeperService(_uow(repo), MemoryQueue(fail=True), 60).sweep()
    assert repo.marked == []


async def test_the_batch_limit_is_passed_on() -> None:  # BR-06
    repo = MemoryRepo([])
    await SweeperService(_uow(repo), MemoryQueue(), 15, limit=2).sweep()
    assert repo.asked == [(15, 2)]


async def test_an_uploaded_invoice_over_the_limit_is_given_up_without_a_send() -> None:  # SAPS-38 BR-05
    last, over = _invoice(InvoiceStatus.UPLOADED, 2), _invoice(InvoiceStatus.UPLOADED, 3)
    repo, queue = MemoryRepo([last, over]), MemoryQueue()
    result = await SweeperService(_uow(repo), queue, 60, max_resends=3).sweep()
    assert queue.sent == [last.id]  # the third re-send is still allowed
    assert repo.gave_up == [over] and [m[0] for m in repo.marked] == [last]
    assert result is not None and result.gave_up == [GaveUp(over.id, TENANT, 3)]


async def test_a_matching_invoice_is_never_limited() -> None:  # SAPS-38 BR-05
    matching = _invoice(InvoiceStatus.MATCHING, 50)
    repo, queue = MemoryRepo([matching]), MemoryQueue()
    result = await SweeperService(_uow(repo), queue, 60, max_resends=3).sweep()
    assert (
        queue.rematch == [matching.id] and repo.gave_up == [] and result is not None and result.gave_up == []
    )


async def test_posting_gets_post_invoice_with_the_same_resend_limit() -> None:  # SAPS-49 BR-12
    posting, exhausted = _invoice(InvoiceStatus.POSTING), _invoice(InvoiceStatus.POSTING, resends=3)
    repo, queue = MemoryRepo([posting, exhausted]), MemoryQueue()
    result = await SweeperService(_uow(repo), queue, 60, max_resends=3).sweep()
    assert queue.posting == [posting.id] and queue.sent == [] and queue.rematch == []
    assert repo.marked == [(posting, "post_invoice")] and repo.gave_up == [exhausted]
    assert result is not None and [r.message for r in result.resent] == ["post_invoice"]
