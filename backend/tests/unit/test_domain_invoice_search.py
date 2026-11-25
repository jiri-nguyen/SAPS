"""Rules of the invoice search (SAPS-46 TS-01)."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from saps.domain.invoice_search import (
    InvalidSearchError,
    SearchCriteria,
    invoice_number_needle,
    local_day_bounds,
    validate,
)


def test_no_filter_is_valid_and_uses_nothing() -> None:  # EC-01
    criteria = SearchCriteria()
    validate(criteria)
    assert criteria.used() == []


def test_used_names_the_filters_without_their_values() -> None:
    criteria = SearchCriteria(vendor="alpha", total_min=Decimal("0"), po_number="0100012")
    assert criteria.used() == ["vendor", "po_number", "total_min"]


@pytest.mark.parametrize(
    ("criteria", "field"),
    [
        (
            SearchCriteria(invoice_date_from=date(2027, 3, 2), invoice_date_to=date(2027, 3, 1)),
            "invoiceDateFrom",
        ),
        (SearchCriteria(uploaded_from=date(2027, 3, 2), uploaded_to=date(2027, 3, 1)), "uploadedFrom"),
        (SearchCriteria(total_min=Decimal("10"), total_max=Decimal("9.99")), "totalMin"),
        (SearchCriteria(total_min=Decimal("-1")), "totalMin"),
        (SearchCriteria(total_max=Decimal("-0.01")), "totalMax"),
    ],
)
def test_invalid_filters_name_the_field(criteria: SearchCriteria, field: str) -> None:  # EC-03, BR-07
    with pytest.raises(InvalidSearchError) as caught:
        validate(criteria)
    assert caught.value.field == field and caught.value.message


def test_equal_ends_and_open_ends_are_valid() -> None:
    validate(SearchCriteria(invoice_date_from=date(2027, 3, 1), invoice_date_to=date(2027, 3, 1)))
    validate(SearchCriteria(total_min=Decimal("5"), total_max=Decimal("5")))
    validate(SearchCriteria(uploaded_to=date(2027, 3, 1)))


@pytest.mark.parametrize(
    ("typed", "needle"),
    [
        ("AOS 2026-1013", "aos20261013"),
        ("aos/2026.1013", "aos20261013"),
        (" 0001 ", "0001"),
        ("", None),
        (None, None),
    ],
)
def test_the_invoice_number_is_normalized_like_the_duplicate_check(
    typed: str | None, needle: str | None
) -> None:
    assert invoice_number_needle(typed) == needle  # EC-06


def test_singapore_days_start_eight_hours_before_the_utc_day() -> None:  # EC-07
    start, end = local_day_bounds(date(2027, 3, 1), date(2027, 3, 1), "Asia/Singapore")
    assert start == datetime(2027, 2, 28, 16, 0, tzinfo=UTC)
    assert end == datetime(2027, 3, 1, 16, 0, tzinfo=UTC)
    early = datetime(
        2027, 2, 28, 16, 30, tzinfo=UTC
    )  # 00:30 on 1 March in Singapore, still 28 February in UTC
    late = datetime(2027, 3, 1, 16, 30, tzinfo=UTC)  # 00:30 on 2 March in Singapore
    assert start <= early < end and not start <= late < end


def test_open_ends_stay_open() -> None:
    assert local_day_bounds(None, None, "UTC") == (None, None)
    start, end = local_day_bounds(date(2027, 3, 1), None, "UTC")
    assert start == datetime(2027, 3, 1, tzinfo=UTC) and end is None
    start, end = local_day_bounds(None, date(2027, 3, 1), "UTC")
    assert start is None and end == datetime(2027, 3, 2, tzinfo=UTC)


def test_a_zone_with_daylight_saving_uses_the_offset_of_each_day() -> None:
    start, end = local_day_bounds(
        date(2027, 3, 14), date(2027, 3, 14), "America/New_York"
    )  # clocks go forward
    assert start == datetime(2027, 3, 14, 5, 0, tzinfo=UTC)  # still UTC-5 at midnight
    assert end == datetime(2027, 3, 15, 4, 0, tzinfo=UTC)  # UTC-4 by the next midnight: a 23-hour day
