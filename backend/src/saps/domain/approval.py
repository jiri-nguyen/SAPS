"""Approval rules (SAPS-22). Pure domain code: no framework imports (ADR-0001)."""

from saps.domain.invoices import ApprovalDecision, InvoiceStatus

NEXT_STATUS = {
    ApprovalDecision.APPROVED: InvoiceStatus.POSTING,  # SAPS-49 BR-01 (DEC-063): posted, no final review
    ApprovalDecision.REJECTED: InvoiceStatus.REJECTED,  # BR-05 (DEC-014): a final state
}


class CommentRequiredError(Exception):
    """EC-02: a rejection needs a comment."""


def checked_comment(decision: ApprovalDecision, comment: str | None) -> str | None:
    """The comment to store: required (not blank) when rejecting, optional when approving."""
    text = comment.strip() if comment else ""
    if decision is ApprovalDecision.REJECTED and not text:
        raise CommentRequiredError("A comment is required to reject the invoice.")
    return text or None
