"""SAPS-49 BR-05: the fingerprint of the values an accepted exception depends on (TS-02)."""

from dataclasses import replace
from decimal import Decimal as D
from uuid import uuid4

from saps.domain.acceptance import FingerprintLine, fingerprint

LINE1 = FingerprintLine(uuid4(), 1, "0100001", 1, "DO-1", D("4"), D("10.00"))
LINE2 = FingerprintLine(uuid4(), 2, "0100002", 1, None, D("2"), D("5.00"))


def _line(line: FingerprintLine, **changes: object) -> str:
    changed = replace(line, **changes)  # type: ignore[arg-type]
    return fingerprint(line.id, "V001", "INV-1", [changed, LINE2 if line is LINE1 else LINE1])


def test_the_same_values_give_the_same_fingerprint() -> None:
    assert _line(LINE1) == _line(LINE1)
    assert len(_line(LINE1)) == 64


def test_decimals_are_compared_by_value_not_by_spelling() -> None:
    assert _line(LINE1, quantity=D("4.000"), unit_price=D("10")) == _line(LINE1)


def test_do_numbers_are_normalized_like_invoice_numbers() -> None:
    assert _line(LINE1, do_number="do 1") == _line(LINE1, do_number="DO-1")


def test_a_line_exception_depends_on_its_own_line_only() -> None:
    other = fingerprint(LINE1.id, "V001", "INV-1", [LINE1, replace(LINE2, quantity=D("99"))])
    assert other == fingerprint(LINE1.id, "V001", "INV-1", [LINE1, LINE2])  # another line changed: same


def test_a_line_exception_changes_with_each_value_it_depends_on() -> None:
    base = _line(LINE1)
    for changes in (
        {"po_number": "0100009"},
        {"po_line_number": 2},
        {"do_number": "DO-2"},
        {"quantity": D("5")},
        {"unit_price": D("10.50")},
        {"line_number": 3},
    ):
        assert _line(LINE1, **changes) != base, changes


def test_a_header_exception_depends_on_the_vendor_the_number_and_every_line() -> None:
    lines = [LINE1, LINE2]
    base = fingerprint(None, "V001", "INV-1", lines)
    assert fingerprint(None, "V001", "inv 1", lines) == base  # normalized invoice number
    assert fingerprint(None, "V001", "INV-2", lines) != base
    assert fingerprint(None, "V002", "INV-1", lines) != base
    assert fingerprint(None, "V001", "INV-1", [LINE1, replace(LINE2, quantity=D("3"))]) != base
    assert (
        fingerprint(None, "V001", "INV-1", [LINE2, LINE1]) == base
    )  # the order of the lines does not matter
    assert fingerprint(None, None, None, lines) == fingerprint(None, "", "", lines)


def test_an_unknown_line_gives_the_header_form() -> None:
    assert fingerprint(uuid4(), "V001", "INV-1", [LINE1]) == fingerprint(None, "V001", "INV-1", [LINE1])


def test_a_line_fingerprint_differs_from_a_header_fingerprint() -> None:
    assert fingerprint(LINE1.id, "V001", "INV-1", [LINE1]) != fingerprint(None, "V001", "INV-1", [LINE1])
