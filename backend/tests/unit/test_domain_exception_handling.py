"""SAPS-20 rules: what may be accepted, what an update changes, who may release (TS-04, TS-07)."""

from dataclasses import replace
from datetime import date
from decimal import Decimal as D
from uuid import uuid4

import pytest

from saps.domain.exception_handling import (
    ACCEPTABLE_AS_IS,
    InvoiceData,
    LineData,
    UpdateRefusedError,
    apply_update,
    change_details,
    ensure_can_release,
    refused_codes,
)
from saps.domain.invoices import ExceptionCode as EX
from saps.domain.users import AccessDeniedError, CurrentUser, Role

LINE1 = LineData(1, "Paper", "0100001", 1, D("2"), D("10.00"), D("20.00"))
LINE2 = LineData(2, "Toner", "0100001", 2, D("1"), D("45.00"), D("45.00"))
DATA = InvoiceData(
    "V001", "Alpha", "INV-1", date(2026, 12, 1), D("65"), D("6.50"), D("71.50"), (LINE1, LINE2)
)


def test_only_ex2_ex6_ex7_ex9_may_be_accepted_as_is() -> None:  # BR-06, DEC-035
    assert ACCEPTABLE_AS_IS == {EX.EX2, EX.EX6, EX.EX7, EX.EX9}


def test_refused_codes_are_unique_and_in_code_order() -> None:
    assert refused_codes([EX.EX10, EX.EX2, EX.EX3, EX.EX3, EX.EX9]) == [EX.EX3, EX.EX10]
    assert refused_codes([EX.EX2, EX.EX6, EX.EX7, EX.EX9]) == []
    assert refused_codes([EX.EX13, EX.EX11, EX.EX12]) == [EX.EX11, EX.EX12, EX.EX13]  # DEC-068


@pytest.mark.parametrize(
    ("header", "matching"),
    [
        ({"vendor_code": "V002"}, True),
        ({"invoice_number": "INV-2"}, True),
        ({"vendor_name": "Alpha Ltd."}, False),
        ({"invoice_date": date(2026, 12, 2)}, True),  # DEC-069
        ({"total_amount": D("80.00")}, False),
    ],
)
def test_header_fields_and_the_matching_flag(header: dict[str, object], matching: bool) -> None:  # BR-05
    change = apply_update(DATA, header, None)
    assert change.matching is matching and change.lines is None and not change.is_empty
    (name, (old, new)), *_ = change.header.items()
    assert old == getattr(DATA, name) and new == header[name]
    assert getattr(change.data, name) == header[name]


def test_an_update_without_a_real_change_is_empty() -> None:  # EC-08
    assert apply_update(DATA, {"vendor_code": "V001", "total_amount": D("71.50")}, None).is_empty
    assert apply_update(DATA, {}, [LINE2, LINE1]).is_empty  # same lines in another order
    assert apply_update(DATA, {}, None).is_empty


@pytest.mark.parametrize(
    ("changes", "matching"),
    [
        ({"unit_price": D("10.50")}, True),
        ({"quantity": D("3")}, True),
        ({"po_number": "0100002"}, True),
        ({"po_line_number": 3}, True),
        ({"do_number": "DO-7"}, True),  # DEC-069
        ({"description": "Copy paper"}, False),
        ({"line_amount": D("21.00")}, False),
    ],
)
def test_line_fields_and_the_matching_flag(changes: dict[str, object], matching: bool) -> None:
    change = apply_update(DATA, {}, [replace(LINE1, **changes), LINE2])
    assert change.matching is matching and change.lines is not None
    assert change.lines[0] == (LINE1, LINE2) and change.data.lines[0] == replace(LINE1, **changes)


def test_lines_replace_all_lines() -> None:  # BR-04
    change = apply_update(DATA, {}, [LINE1])  # line 2 is dropped
    assert change.matching and change.data.lines == (LINE1,)
    added = apply_update(DATA, {}, [LINE1, LINE2, LineData(3, "New", None, None, D("1"), D("1"), D("1"))])
    assert added.matching and len(added.data.lines) == 3


@pytest.mark.parametrize(
    "lines", [[], [LINE1, replace(LINE2, line_number=1)], [replace(LINE1, line_number=0)]]
)
def test_invalid_line_sets_are_refused(lines: list[LineData]) -> None:
    with pytest.raises(UpdateRefusedError, match="unique line numbers"):
        apply_update(DATA, {}, lines)


def test_unknown_header_fields_are_a_programming_error() -> None:
    with pytest.raises(ValueError, match="Not editable"):
        apply_update(DATA, {"status": "COMPLETED"}, None)


def test_event_details_hold_old_and_new_values() -> None:  # BR-11
    change = apply_update(DATA, {"invoice_number": "INV-2"}, [replace(LINE1, unit_price=D("10.50")), LINE2])
    details = change_details(change)
    assert details["rematch"] is True
    assert details["fields"] == {"invoiceNumber": {"old": "INV-1", "new": "INV-2"}}
    old_lines, new_lines = details["lines"]["old"], details["lines"]["new"]
    assert old_lines[0]["unitPrice"] == "10.00" and new_lines[0]["unitPrice"] == "10.50"
    assert old_lines[0]["lineNumber"] == 1 and new_lines[1]["poNumber"] == "0100001"
    assert "lines" not in change_details(apply_update(DATA, {"vendor_name": "X"}, None))


def _user(role: Role) -> CurrentUser:
    return CurrentUser(uuid4(), uuid4(), "u", "U", role)


def test_release_rules() -> None:  # BR-03, DEC-036
    member, other, manager = (
        _user(Role.ACCOUNTING_MEMBER),
        _user(Role.ACCOUNTING_MEMBER),
        _user(Role.ACCOUNTING_MANAGER),
    )
    assert ensure_can_release(member, member.user_id) is True  # the claimant
    assert ensure_can_release(manager, other.user_id) is True  # a manager releases any claim
    assert ensure_can_release(member, None) is False  # nothing to release
    with pytest.raises(AccessDeniedError):
        ensure_can_release(member, other.user_id)
