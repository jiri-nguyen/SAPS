"""The processing calendar rules (SAPS-52 TS-01)."""

from datetime import UTC, date, datetime

import pytest

from saps.domain.invoices import InvalidTransitionError, InvoiceStatus, ensure_transition
from saps.domain.processing_calendar import (
    CalendarRule,
    RuleKind,
    is_closed,
    local_today,
    next_open_day,
    rule_errors,
)


def rng(first: int, last: int) -> CalendarRule:
    return CalendarRule(RuleKind.MONTHLY_RANGE, from_day=first, to_day=last)


def weekday(number: int) -> CalendarRule:
    return CalendarRule(RuleKind.WEEKDAY, weekday=number)


def on(day: date) -> CalendarRule:
    return CalendarRule(RuleKind.DATE, day=day)


def test_an_empty_calendar_is_always_open() -> None:
    assert not is_closed(date(2027, 3, 1), [])
    assert next_open_day(date(2027, 3, 1), []) == date(2027, 3, 2)


@pytest.mark.parametrize(
    ("day", "closed"),
    [
        (date(2027, 3, 24), False),
        (date(2027, 3, 25), True),  # both ends included (BR-02)
        (date(2027, 3, 31), True),
        (date(2027, 4, 1), True),
        (date(2027, 4, 5), True),
        (date(2027, 4, 6), False),
        (date(2027, 12, 31), True),  # across a year end
        (date(2028, 1, 5), True),
        (date(2028, 1, 6), False),
    ],
)
def test_a_range_from_the_25th_to_the_5th_runs_into_the_next_month(day: date, closed: bool) -> None:  # EC-01
    assert is_closed(day, [rng(25, 5)]) is closed


@pytest.mark.parametrize(
    ("day", "closed"),
    [
        (date(2027, 2, 27), False),
        (date(2027, 2, 28), True),  # 30 in February means its last day (BR-02, EC-02)
        (date(2028, 2, 28), False),  # leap year: the last day is the 29th
        (date(2028, 2, 29), True),
        (date(2027, 4, 29), False),
        (date(2027, 4, 30), True),
        (date(2027, 3, 1), True),
        (date(2027, 3, 5), True),
        (date(2027, 3, 6), False),
    ],
)
def test_a_day_after_the_end_of_a_month_means_its_last_day(day: date, closed: bool) -> None:
    assert is_closed(day, [rng(30, 5)]) is closed


def test_a_range_inside_one_month_and_a_single_day_range() -> None:
    assert [is_closed(date(2027, 3, d), [rng(10, 12)]) for d in (9, 10, 11, 12, 13)] == [
        False,
        True,
        True,
        True,
        False,
    ]
    assert is_closed(date(2027, 5, 10), [rng(10, 10)])  # EC-03
    assert not is_closed(date(2027, 5, 11), [rng(10, 10)])
    assert is_closed(date(2027, 2, 28), [rng(31, 31)])  # the last day of February


def test_weekdays_and_dates() -> None:
    weekend = [weekday(6), weekday(7)]
    assert [is_closed(date(2027, 3, d), weekend) for d in (5, 6, 7, 8)] == [
        False,
        True,
        True,
        False,
    ]  # Fri to Mon
    holiday = [on(date(2027, 4, 30))]
    assert is_closed(date(2027, 4, 30), holiday) and not is_closed(date(2027, 5, 1), holiday)


def test_any_matching_rule_closes_the_day() -> None:
    rules = [rng(25, 5), weekday(7), on(date(2027, 3, 10))]
    assert is_closed(date(2027, 3, 10), rules) and is_closed(date(2027, 3, 14), rules)  # a Sunday
    assert not is_closed(date(2027, 3, 11), rules)


def test_the_next_open_day_skips_the_closed_ones() -> None:
    rules = [rng(25, 5), weekday(6), weekday(7)]
    assert next_open_day(date(2027, 3, 24), rules) == date(2027, 3, 24) + (
        date(2027, 4, 6) - date(2027, 3, 24)
    )
    assert next_open_day(date(2027, 3, 31), rules) == date(2027, 4, 6)  # 6 April 2027 is a Tuesday
    assert next_open_day(date(2027, 3, 12), [weekday(6), weekday(7)]) == date(2027, 3, 15)  # Friday to Monday


def test_a_company_closed_every_day_has_no_open_day() -> None:  # EC-05
    every_day = [weekday(n) for n in range(1, 8)]
    assert is_closed(date(2027, 3, 1), every_day)
    assert next_open_day(date(2027, 3, 1), every_day) is None
    assert next_open_day(date(2027, 3, 1), [rng(1, 31)]) is None


def test_the_day_is_a_day_of_the_company_time_zone() -> None:  # EC-04
    late_utc = datetime(2027, 3, 1, 17, 30, tzinfo=UTC)
    assert local_today(late_utc, "UTC") == date(2027, 3, 1)
    assert local_today(late_utc, "Asia/Singapore") == date(2027, 3, 2)
    assert local_today(late_utc, "America/Los_Angeles") == date(2027, 3, 1)


def test_valid_rules_have_no_errors() -> None:
    rules = [
        rng(25, 5),
        weekday(1),
        on(date(2027, 4, 30)),
        CalendarRule(RuleKind.WEEKDAY, weekday=7, label="Sunday"),
    ]
    assert rule_errors(rules) == {}
    assert rule_errors([]) == {}


@pytest.mark.parametrize(
    ("rule", "field"),
    [
        (CalendarRule(RuleKind.MONTHLY_RANGE, from_day=0, to_day=5), "rules[0].fromDay"),
        (CalendarRule(RuleKind.MONTHLY_RANGE, from_day=25, to_day=32), "rules[0].toDay"),
        (CalendarRule(RuleKind.MONTHLY_RANGE, from_day=25), "rules[0].toDay"),
        (CalendarRule(RuleKind.MONTHLY_RANGE, to_day=5), "rules[0].fromDay"),
        (CalendarRule(RuleKind.MONTHLY_RANGE, from_day=1, to_day=5, weekday=3), "rules[0]"),
        (CalendarRule(RuleKind.WEEKDAY, weekday=8), "rules[0].weekday"),
        (CalendarRule(RuleKind.WEEKDAY, weekday=0), "rules[0].weekday"),
        (CalendarRule(RuleKind.WEEKDAY), "rules[0].weekday"),
        (CalendarRule(RuleKind.WEEKDAY, weekday=1, from_day=1), "rules[0]"),
        (CalendarRule(RuleKind.DATE), "rules[0].date"),
        (CalendarRule(RuleKind.DATE, day=date(2027, 1, 1), weekday=1), "rules[0]"),
        (CalendarRule(RuleKind.WEEKDAY, weekday=1, label="x" * 101), "rules[0].label"),
    ],
)
def test_invalid_rules_name_their_field(rule: CalendarRule, field: str) -> None:  # EC-10
    assert field in rule_errors([rule])


def test_the_errors_name_the_index_and_more_than_100_rules_are_refused() -> None:
    errors = rule_errors([weekday(1), weekday(1), CalendarRule(RuleKind.DATE)])
    assert list(errors) == ["rules[2].date"]
    assert "rules" in rule_errors([weekday(1)] * 101)
    assert rule_errors([weekday(1)] * 100) == {}


def test_the_lifecycle_has_the_hold_and_the_release() -> None:
    ensure_transition(InvoiceStatus.UPLOADED, InvoiceStatus.ON_HOLD)
    ensure_transition(InvoiceStatus.ON_HOLD, InvoiceStatus.UPLOADED)
    for target in (InvoiceStatus.MATCHING, InvoiceStatus.EXCEPTION, InvoiceStatus.COMPLETED):
        with pytest.raises(InvalidTransitionError):
            ensure_transition(InvoiceStatus.ON_HOLD, target)
    with pytest.raises(InvalidTransitionError):
        ensure_transition(InvoiceStatus.MATCHING, InvoiceStatus.ON_HOLD)
