"""Invoice states and codes (data model §4.1, §5). Pure domain code: no framework imports (ADR-0001)."""

from enum import StrEnum


class InvoiceStatus(StrEnum):
    """Invoice lifecycle states, approved in MTG-20261128 R2."""

    UPLOADED = "UPLOADED"
    MATCHING = "MATCHING"
    EXCEPTION = "EXCEPTION"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    PENDING_REVIEW = "PENDING_REVIEW"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    ON_HOLD = "ON_HOLD"  # received on a closed day of the processing calendar (SAPS-52)
    POSTING = "POSTING"  # waiting to be posted to the ERP (SAPS-49, DEC-064)
    POSTED = "POSTED"  # posted; final


class InvoiceType(StrEnum):
    """Derived from the PO numbers on the lines (DEC-005)."""

    TRADE_PO = "TRADE_PO"
    NON_TRADE_PO = "NON_TRADE_PO"
    NON_PO = "NON_PO"


class MatchStatus(StrEnum):
    NOT_MATCHED = "NOT_MATCHED"
    MATCHED = "MATCHED"
    MISMATCH = "MISMATCH"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ExceptionCode(StrEnum):
    """Exception codes EX1 … EX13 (DEC-033, DEC-068)."""

    EX1 = "EX1"
    EX2 = "EX2"
    EX3 = "EX3"
    EX4 = "EX4"
    EX5 = "EX5"
    EX6 = "EX6"
    EX7 = "EX7"
    EX8 = "EX8"
    EX9 = "EX9"
    EX10 = "EX10"
    EX11 = "EX11"
    EX12 = "EX12"
    EX13 = "EX13"


class ExceptionStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class ApprovalDecision(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class NotificationType(StrEnum):
    """Recipients by type (DEC-021)."""

    EXCEPTION_RAISED = "EXCEPTION_RAISED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    REVIEW_REQUESTED = "REVIEW_REQUESTED"


_S = InvoiceStatus
ALLOWED_TRANSITIONS: dict[InvoiceStatus, frozenset[InvoiceStatus]] = {
    _S.UPLOADED: frozenset({_S.MATCHING, _S.EXCEPTION, _S.ON_HOLD}),
    _S.MATCHING: frozenset({_S.EXCEPTION, _S.PENDING_APPROVAL, _S.POSTING}),
    _S.EXCEPTION: frozenset({_S.MATCHING, _S.REJECTED}),
    _S.PENDING_APPROVAL: frozenset({_S.POSTING, _S.REJECTED}),
    # Pending review and Completed exist only for invoices of earlier versions (DEC-063): the migration moves
    # Pending review to Posting.
    _S.PENDING_REVIEW: frozenset({_S.POSTING}),
    _S.COMPLETED: frozenset(),
    _S.REJECTED: frozenset(),
    _S.ON_HOLD: frozenset({_S.UPLOADED}),
    _S.POSTING: frozenset({_S.POSTED}),
    _S.POSTED: frozenset(),
}


class InvalidTransitionError(Exception):
    """A status change that the invoice lifecycle (data model §5) does not allow."""


def ensure_transition(current: InvoiceStatus, target: InvoiceStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(f"{current} -> {target}")
