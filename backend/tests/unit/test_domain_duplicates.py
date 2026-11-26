"""SAPS-23 duplicate rules (TS-02, BR-04)."""

from uuid import uuid4

import pytest

from saps.domain.duplicates import (
    COMPARED_STATUSES,
    DuplicateCandidate,
    duplicate_finding,
    normalize_invoice_number,
)
from saps.domain.invoices import ExceptionCode, InvoiceStatus


@pytest.mark.parametrize(
    "number", ["INV-0001", "inv 0001", "INV0001", "INV.0001", "INV/0001", " Inv - 0001 "]
)
def test_variants_normalize_to_the_same_key(number: str) -> None:
    assert normalize_invoice_number(number) == "inv0001"


def test_leading_zeros_are_kept() -> None:
    assert normalize_invoice_number("INV-0001") != normalize_invoice_number("INV-001")


@pytest.mark.parametrize("number", [None, "", " - ./ "])
def test_no_key_without_a_number(number: str | None) -> None:
    assert normalize_invoice_number(number) is None


def test_compared_statuses() -> None:  # BR-03
    assert set(COMPARED_STATUSES) == set(InvoiceStatus) - {
        InvoiceStatus.UPLOADED,
        InvoiceStatus.MATCHING,
        InvoiceStatus.REJECTED,
        InvoiceStatus.ON_HOLD,  # no data yet, like Uploaded (SAPS-52)
    }


def test_ex9_names_every_other_invoice() -> None:  # BR-04, EC-05
    one = duplicate_finding([DuplicateCandidate(uuid4(), "A-1", InvoiceStatus.COMPLETED)])
    assert (one.code, one.line_id) == (ExceptionCode.EX9, None)
    assert one.message == "Duplicate of invoice A-1 (Completed)."
    two = duplicate_finding(
        [
            DuplicateCandidate(uuid4(), "A-1", InvoiceStatus.COMPLETED),
            DuplicateCandidate(uuid4(), "a 1", InvoiceStatus.EXCEPTION),
        ]
    )
    assert two.message == "Duplicate of invoices A-1 (Completed), a 1 (Exception)."
