"""The processing calendar of a company (SAPS-52, DEC-062). Pure domain code: no framework imports (ADR-0001).

A company closes days with rules: a monthly day range, a weekday, a specific date. A day matching any rule is
closed; every other day is open. Days are days of the company's time zone; there are no times of day.
"""

import calendar
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

MAX_RULES = 100
MAX_LABEL = 100
LOOK_AHEAD_DAYS = 366  # no open day within a year: "until further notice" (SAPS-52 EC-05)


class RuleKind(StrEnum):
    MONTHLY_RANGE = "MONTHLY_RANGE"
    WEEKDAY = "WEEKDAY"
    DATE = "DATE"


@dataclass(frozen=True)
class CalendarRule:
    kind: RuleKind
    from_day: int | None = None  # MONTHLY_RANGE: 1 to 31
    to_day: int | None = None
    weekday: int | None = None  # WEEKDAY: 1 (Monday) to 7 (Sunday)
    day: date | None = None  # DATE
    label: str | None = None


def rule_errors(rules: Sequence[CalendarRule]) -> dict[str, str]:
    """BR-01, EC-10: the field (`rules[2].fromDay`) and the message of every rule that is not valid."""
    errors: dict[str, str] = {}
    if len(rules) > MAX_RULES:
        errors["rules"] = f"At most {MAX_RULES} rules."
    for index, rule in enumerate(rules):
        where = f"rules[{index}]"
        if rule.label is not None and len(rule.label) > MAX_LABEL:
            errors[f"{where}.label"] = f"At most {MAX_LABEL} characters."
        if rule.kind is RuleKind.MONTHLY_RANGE:
            for name, value in (("fromDay", rule.from_day), ("toDay", rule.to_day)):
                if value is None:
                    errors[f"{where}.{name}"] = "A monthly range needs a first and a last day."
                elif not 1 <= value <= 31:
                    errors[f"{where}.{name}"] = "The day of the month is 1 to 31."
            if rule.weekday is not None or rule.day is not None:
                errors[where] = "A monthly range has only a first and a last day."
        elif rule.kind is RuleKind.WEEKDAY:
            if rule.weekday is None:
                errors[f"{where}.weekday"] = "A weekday rule needs a weekday."
            elif not 1 <= rule.weekday <= 7:
                errors[f"{where}.weekday"] = "The weekday is 1 (Monday) to 7 (Sunday)."
            if rule.from_day is not None or rule.to_day is not None or rule.day is not None:
                errors[where] = "A weekday rule has only a weekday."
        else:
            if rule.day is None:
                errors[f"{where}.date"] = "A date rule needs a date."
            if rule.from_day is not None or rule.to_day is not None or rule.weekday is not None:
                errors[where] = "A date rule has only a date."
    return errors


def _in_range(day: date, first: int, last: int) -> bool:
    """A monthly range, both days included; a day after the end of a month means its last day (BR-02)."""
    end_of_month = calendar.monthrange(day.year, day.month)[1]
    low, high = min(first, end_of_month), min(last, end_of_month)
    if first <= last:
        return low <= day.day <= high
    return day.day >= low or day.day <= high  # 25 to 5: the end of one month and the start of the next


def _matches(day: date, rule: CalendarRule) -> bool:
    if rule.kind is RuleKind.DATE:
        return rule.day == day
    if rule.kind is RuleKind.WEEKDAY:
        return rule.weekday == day.isoweekday()
    assert rule.from_day is not None and rule.to_day is not None
    return _in_range(day, rule.from_day, rule.to_day)


def is_closed(day: date, rules: Sequence[CalendarRule]) -> bool:
    return any(_matches(day, rule) for rule in rules)


def next_open_day(day: date, rules: Sequence[CalendarRule]) -> date | None:
    """The first open day after `day` (EC-05: None when none comes within a year)."""
    for offset in range(1, LOOK_AHEAD_DAYS + 1):
        candidate = day + timedelta(days=offset)
        if not is_closed(candidate, rules):
            return candidate
    return None


def local_today(now: datetime, time_zone: str) -> date:
    """Today in the company's time zone (BR-02)."""
    return now.astimezone(ZoneInfo(time_zone)).date()
