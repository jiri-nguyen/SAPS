"""Calendar service, "Process now" and the release timer with in-memory ports (SAPS-52 TS-01 to TS-05)."""

import logging
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest

from saps.application.exception_handling import ConflictError
from saps.application.invoices import InvoiceNotFoundError
from saps.application.processing_calendar import (
    HoldReleaseService,
    InvalidCalendarError,
    InvoiceHoldService,
    ProcessingCalendarService,
)
from saps.domain.invoices import InvoiceStatus
from saps.domain.processing_calendar import CalendarRule, RuleKind
from saps.domain.users import CurrentUser, Role
from saps.ports.invoice_hold import HeldInvoice
from saps.ports.processing_calendar import CalendarSnapshot, CalendarView, Company
from tests.fakes import MemoryQueue

NOW = datetime(2027, 3, 26, 9, 0, tzinfo=UTC)  # Friday 26 March 2027
MANAGER = CurrentUser(uuid4(), uuid4(), "manager1@sg.example.com", "Manager 1", Role.ACCOUNTING_MANAGER)
RANGE_25_TO_5 = CalendarRule(RuleKind.MONTHLY_RANGE, from_day=25, to_day=5)
SATURDAY = CalendarRule(RuleKind.WEEKDAY, weekday=6)


class FakeCalendars:
    def __init__(self, rules: Sequence[CalendarRule] = (), zone: str = "Asia/Singapore") -> None:
        self.rules, self.zone = tuple(rules), zone
        self.replaced: list[tuple[UUID, tuple[CalendarRule, ...], str]] = []

    async def get(self, tenant_id: UUID) -> CalendarView:
        changed, by = (NOW, "Manager 1") if self.rules else (None, None)
        return CalendarView(self.rules, self.zone, changed, by)

    async def replace(self, tenant_id: UUID, rules: Sequence[CalendarRule], actor: str) -> None:
        self.rules = tuple(rules)
        self.replaced.append((tenant_id, self.rules, actor))


def _calendar_service(calendars: FakeCalendars, now: datetime = NOW) -> ProcessingCalendarService:
    return ProcessingCalendarService(calendars, lambda: now)  # type: ignore[arg-type]


async def test_an_open_company_has_no_banner_date() -> None:
    status = await _calendar_service(FakeCalendars([SATURDAY])).get(MANAGER)  # 26 March 2027 is a Friday
    assert (status.closed_today, status.open_again_on) == (False, None)


async def test_a_closed_company_names_the_first_open_day() -> None:  # BR-08
    status = await _calendar_service(FakeCalendars([RANGE_25_TO_5])).get(MANAGER)
    assert status.closed_today and status.open_again_on == date(2027, 4, 6)
    assert status.view.time_zone == "Asia/Singapore"


async def test_a_company_that_never_opens_again_has_no_date() -> None:  # EC-05
    every_day = [CalendarRule(RuleKind.WEEKDAY, weekday=n) for n in range(1, 8)]
    status = await _calendar_service(FakeCalendars(every_day)).get(MANAGER)
    assert status.closed_today and status.open_again_on is None


async def test_today_is_a_day_of_the_company_time_zone() -> None:
    late = datetime(2027, 3, 26, 17, 30, tzinfo=UTC)  # 01:30 on Saturday 27 March in Singapore
    assert (await _calendar_service(FakeCalendars([SATURDAY]), late).get(MANAGER)).closed_today
    assert not (await _calendar_service(FakeCalendars([SATURDAY], "UTC"), late).get(MANAGER)).closed_today


async def test_replacing_saves_the_rules_for_the_company_and_logs(caplog: pytest.LogCaptureFixture) -> None:
    calendars = FakeCalendars()
    with caplog.at_level(logging.INFO):
        status = await _calendar_service(calendars).replace(MANAGER, [RANGE_25_TO_5, SATURDAY])
    assert calendars.replaced == [(MANAGER.tenant_id, (RANGE_25_TO_5, SATURDAY), MANAGER.username)]
    assert status.closed_today and "processing_calendar_changed" in caplog.text


async def test_invalid_rules_save_nothing() -> None:  # EC-10
    calendars = FakeCalendars()
    with pytest.raises(InvalidCalendarError) as caught:
        await _calendar_service(calendars).replace(MANAGER, [CalendarRule(RuleKind.WEEKDAY, weekday=9)])
    assert list(caught.value.fields) == ["rules[0].weekday"] and calendars.replaced == []


# "Process now" --------------------------------------------------------------------------------------------


class FakeHoldRepo:
    def __init__(self, invoice: HeldInvoice | None) -> None:
        self.invoice = invoice
        self.released: list[tuple[str, datetime]] = []

    async def lock_invoice(self, tenant_id: UUID, invoice_id: UUID) -> HeldInvoice | None:
        return self.invoice if self.invoice and self.invoice.tenant_id == tenant_id else None

    async def release_by_manager(self, invoice: HeldInvoice, *, actor: str, now: datetime) -> None:
        self.released.append((actor, now))


class FakeUow:
    def __init__(self, repo: FakeHoldRepo) -> None:
        self.repo, self.committed = repo, 0

    def __call__(self) -> FakeUow:
        return self

    async def __aenter__(self) -> FakeHoldRepo:
        return self.repo

    async def __aexit__(self, *exc: object) -> None:
        self.committed += 1 if exc[0] is None else 0


def _held(status: InvoiceStatus = InvoiceStatus.ON_HOLD) -> HeldInvoice:
    return HeldInvoice(uuid4(), MANAGER.tenant_id, status)


async def test_process_now_releases_and_sends_the_message() -> None:  # BR-06
    invoice, queue = _held(), MemoryQueue()
    uow = FakeUow(FakeHoldRepo(invoice))
    await InvoiceHoldService(uow, queue, lambda: NOW).release(MANAGER, invoice.id)  # type: ignore[arg-type]
    assert uow.repo.released == [(MANAGER.username, NOW)] and uow.committed == 1
    assert queue.tenant_of == {invoice.id: MANAGER.tenant_id}


async def test_process_now_refuses_an_invoice_that_is_not_on_hold() -> None:  # EC-07
    invoice, queue = _held(InvoiceStatus.UPLOADED), MemoryQueue()
    service = InvoiceHoldService(FakeUow(FakeHoldRepo(invoice)), queue, lambda: NOW)  # type: ignore[arg-type]
    with pytest.raises(ConflictError):
        await service.release(MANAGER, invoice.id)
    assert queue.sent == []


async def test_process_now_for_another_companys_invoice_is_not_found() -> None:  # EC-08
    other = HeldInvoice(uuid4(), uuid4(), InvoiceStatus.ON_HOLD)
    service = InvoiceHoldService(FakeUow(FakeHoldRepo(other)), MemoryQueue(), lambda: NOW)  # type: ignore[arg-type]
    with pytest.raises(InvoiceNotFoundError):
        await service.release(MANAGER, other.id)


async def test_a_failed_send_keeps_the_release(caplog: pytest.LogCaptureFixture) -> None:  # EC-06, sweeper
    invoice = _held()
    uow = FakeUow(FakeHoldRepo(invoice))
    with caplog.at_level(logging.WARNING):
        await InvoiceHoldService(uow, MemoryQueue(fail=True), lambda: NOW).release(MANAGER, invoice.id)  # type: ignore[arg-type]
    assert uow.committed == 1 and "process_invoice_not_sent" in caplog.text


# The release timer ----------------------------------------------------------------------------------------


class FakeHeld:
    def __init__(self, companies: dict[Company, CalendarSnapshot], held: dict[UUID, list[UUID]]) -> None:
        self.companies, self.held = companies, held
        self.asked: list[tuple[UUID, int]] = []
        self.postings: dict[UUID, list[UUID]] = defaultdict(list)  # held postings (DEC-070)
        self.asked_postings: list[tuple[UUID, int]] = []

    async def list_companies(self) -> list[Company]:
        return list(self.companies)

    async def snapshot(self, tenant_id: UUID) -> CalendarSnapshot:
        return next(s for c, s in self.companies.items() if c.tenant_id == tenant_id)

    async def release_oldest(self, tenant_id: UUID, limit: int, *, now: datetime) -> list[UUID]:
        self.asked.append((tenant_id, limit))
        ids, self.held[tenant_id] = self.held[tenant_id][:limit], self.held[tenant_id][limit:]
        return ids

    async def release_postings(self, tenant_id: UUID, limit: int, *, now: datetime) -> list[UUID]:
        self.asked_postings.append((tenant_id, limit))
        ids, self.postings[tenant_id] = self.postings[tenant_id][:limit], self.postings[tenant_id][limit:]
        return ids


async def test_the_timer_releases_only_the_companies_that_are_open_oldest_first() -> None:  # BR-05, EC-09
    open_company, closed_company = Company(uuid4(), "Open"), Company(uuid4(), "Closed")
    held = {open_company.tenant_id: [uuid4() for _ in range(5)], closed_company.tenant_id: [uuid4()]}
    first_three = list(held[open_company.tenant_id][:3])
    repo = FakeHeld(
        {
            open_company: CalendarSnapshot((SATURDAY,), "UTC"),  # Friday: open
            closed_company: CalendarSnapshot((RANGE_25_TO_5,), "UTC"),
        },
        held,
    )
    queue = MemoryQueue()
    released = await HoldReleaseService(repo, queue, lambda: NOW, 3).release_due()  # type: ignore[arg-type]
    assert released == 3 and queue.sent == first_three  # a batch of 3, the oldest first
    assert repo.asked == [(open_company.tenant_id, 3)]  # the closed company is not even asked
    assert set(queue.tenant_of.values()) == {open_company.tenant_id}
    assert len(held[open_company.tenant_id]) == 2 and len(held[closed_company.tenant_id]) == 1


async def test_the_timer_sends_held_postings_of_open_companies_only() -> None:  # DEC-070, SAPS-49 BR-11
    open_company, closed_company = Company(uuid4(), "Open"), Company(uuid4(), "Closed")
    repo = FakeHeld(
        {
            open_company: CalendarSnapshot((SATURDAY,), "UTC"),
            closed_company: CalendarSnapshot((RANGE_25_TO_5,), "UTC"),
        },
        {open_company.tenant_id: [], closed_company.tenant_id: []},
    )
    waiting = [uuid4() for _ in range(3)]
    repo.postings[open_company.tenant_id] = list(waiting)
    repo.postings[closed_company.tenant_id] = [uuid4()]
    queue = MemoryQueue()
    released = await HoldReleaseService(repo, queue, lambda: NOW, 2).release_due()  # type: ignore[arg-type]
    assert released == 2 and queue.posting == waiting[:2] and queue.sent == []  # a batch of 2, oldest first
    assert repo.asked_postings == [(open_company.tenant_id, 2)]  # the closed company is not asked


async def test_a_failed_send_of_a_held_posting_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    company = Company(uuid4(), "Open")
    repo = FakeHeld({company: CalendarSnapshot((), "UTC")}, {company.tenant_id: []})
    repo.postings[company.tenant_id] = [uuid4()]
    with caplog.at_level(logging.WARNING):
        released = await HoldReleaseService(repo, MemoryQueue(fail=True), lambda: NOW, 10).release_due()  # type: ignore[arg-type]
    assert released == 1 and caplog.text.count("posting_not_sent") == 1


async def test_a_failed_send_does_not_stop_the_release(caplog: pytest.LogCaptureFixture) -> None:
    company = Company(uuid4(), "Open")
    repo = FakeHeld({company: CalendarSnapshot((), "UTC")}, {company.tenant_id: [uuid4(), uuid4()]})
    with caplog.at_level(logging.WARNING):
        released = await HoldReleaseService(repo, MemoryQueue(fail=True), lambda: NOW, 10).release_due()  # type: ignore[arg-type]
    assert released == 2 and caplog.text.count("process_invoice_not_sent") == 2


async def test_nothing_held_releases_nothing() -> None:
    company = Company(uuid4(), "Open")
    repo = FakeHeld({company: CalendarSnapshot((), "UTC")}, {company.tenant_id: []})
    assert await HoldReleaseService(repo, MemoryQueue(), lambda: NOW, 10).release_due() == 0  # type: ignore[arg-type]
