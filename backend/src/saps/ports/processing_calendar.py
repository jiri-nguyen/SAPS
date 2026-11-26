"""Persistence ports of the processing calendar (SAPS-52)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from saps.domain.processing_calendar import CalendarRule


@dataclass(frozen=True)
class CalendarSnapshot:
    """What a job needs to decide whether a day is closed: the rules and the company's time zone."""

    rules: tuple[CalendarRule, ...]
    time_zone: str


@dataclass(frozen=True)
class CalendarView:
    rules: tuple[CalendarRule, ...]
    time_zone: str
    updated_at: datetime | None  # the latest change of a rule; None without rules
    updated_by: str | None  # display name of that user


class ProcessingCalendarRepository(Protocol):
    async def get(self, tenant_id: UUID) -> CalendarView: ...

    async def replace(self, tenant_id: UUID, rules: Sequence[CalendarRule], actor: str) -> None:
        """All rules of the company are replaced, in the order given (BR-07)."""
        ...


@dataclass(frozen=True)
class Company:
    tenant_id: UUID
    name: str


class HeldInvoiceRepository(Protocol):
    """The release of held invoices by the calendar timer (BR-05); one company per call."""

    async def list_companies(self) -> list[Company]:
        """Active companies."""
        ...

    async def snapshot(self, tenant_id: UUID) -> CalendarSnapshot: ...

    async def release_oldest(self, tenant_id: UUID, limit: int, *, now: datetime) -> list[UUID]:
        """Up to `limit` invoices On hold, oldest first, back to Uploaded (`RELEASE_HOLD`); committed."""
        ...
