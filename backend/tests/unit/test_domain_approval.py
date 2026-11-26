import pytest

from saps.domain.approval import NEXT_STATUS, CommentRequiredError, checked_comment
from saps.domain.invoices import ApprovalDecision, InvoiceStatus, ensure_transition


def test_next_status() -> None:  # BR-04, BR-05
    assert NEXT_STATUS[ApprovalDecision.APPROVED] is InvoiceStatus.POSTING  # SAPS-49 BR-01
    assert NEXT_STATUS[ApprovalDecision.REJECTED] is InvoiceStatus.REJECTED
    for status in NEXT_STATUS.values():
        ensure_transition(InvoiceStatus.PENDING_APPROVAL, status)  # the lifecycle allows both


@pytest.mark.parametrize("comment", [None, "", "   "])
def test_reject_needs_a_comment(comment: str | None) -> None:  # EC-02
    with pytest.raises(CommentRequiredError, match="comment is required"):
        checked_comment(ApprovalDecision.REJECTED, comment)


def test_comments_are_trimmed_and_optional_for_an_approval() -> None:
    assert checked_comment(ApprovalDecision.REJECTED, "  PO is wrong.  ") == "PO is wrong."
    assert checked_comment(ApprovalDecision.APPROVED, None) is None
    assert checked_comment(ApprovalDecision.APPROVED, "  ") is None
    assert checked_comment(ApprovalDecision.APPROVED, "Looks fine.") == "Looks fine."
