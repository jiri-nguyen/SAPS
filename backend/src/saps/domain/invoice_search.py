"""Rules of the invoice search (SAPS-46, DEC-057). Pure domain code: no framework imports (ADR-0001)."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from saps.domain.duplicates import normalize_invoice_number
from saps.domain.mail_intake import IntakeChannel


class InvalidSearchError(ValueError):
    """A filter that cannot be searched (BR-07); `field` names the one at fault."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


@dataclass(frozen=True)
class SearchCriteria:
    """The filters of the screen "All invoices" as the caller gave them; every one is optional (BR-02)."""

    vendor: str | None = None
    invoice_number: str | None = None
    po_number: str | None = None
    invoice_date_from: date | None = None
    invoice_date_to: date | None = None
    uploaded_from: date | None = None
    uploaded_to: date | None = None
    total_min: Decimal | None = None
    total_max: Decimal | None = None
    channel: IntakeChannel | None = None

    def used(self) -> list[str]:
        """Names of the filters in use, for the log (never their values)."""
        return [name for name, value in vars(self).items() if value not in (None, "")]


def validate(criteria: SearchCriteria) -> None:
    """BR-07: a "from" after its "to", a negative amount, or a minimum above the maximum."""
    _ordered("invoiceDateFrom", criteria.invoice_date_from, "invoiceDateTo", criteria.invoice_date_to)
    _ordered("uploadedFrom", criteria.uploaded_from, "uploadedTo", criteria.uploaded_to)
    for name, amount in (("totalMin", criteria.total_min), ("totalMax", criteria.total_max)):
        if amount is not None and amount < 0:
            raise InvalidSearchError(name, "The amount cannot be negative.")
    _ordered("totalMin", criteria.total_min, "totalMax", criteria.total_max)


def _ordered[T: (date, Decimal)](low_name: str, low: T | None, high_name: str, high: T | None) -> None:
    if low is not None and high is not None and low > high:
        raise InvalidSearchError(low_name, f"{low_name} must not be after {high_name}.")


def invoice_number_needle(value: str | None) -> str | None:
    """The text to look for in the normalized invoice number; case, spaces and `-` `.` `/` are ignored."""
    return normalize_invoice_number(value)


def local_day_bounds(
    first: date | None, last: date | None, time_zone: str
) -> tuple[datetime | None, datetime | None]:
    """The UTC instants `[start, end)` of the company's local days `first` to `last`, both included (BR-04).

    An upload shortly before midnight in Singapore is on that local day, not on the UTC day (EC-07).
    """
    zone = ZoneInfo(time_zone)

    def midnight(day: date) -> datetime:
        return datetime.combine(day, time.min, tzinfo=zone).astimezone(UTC)

    start = midnight(first) if first is not None else None
    end = midnight(last + timedelta(days=1)) if last is not None else None
    return start, end
