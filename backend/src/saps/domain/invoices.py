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
    """Exception codes EX1 … EX10 (DEC-033)."""

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
    _S.UPLOADED: frozenset({_S.MATCHING, _S.EXCEPTION}),
    _S.MATCHING: frozenset({_S.EXCEPTION, _S.PENDING_APPROVAL, _S.PENDING_REVIEW}),
    _S.EXCEPTION: frozenset({_S.MATCHING, _S.PENDING_APPROVAL, _S.PENDING_REVIEW, _S.REJECTED}),
    _S.PENDING_APPROVAL: frozenset({_S.PENDING_REVIEW, _S.REJECTED}),
    _S.PENDING_REVIEW: frozenset({_S.COMPLETED, _S.REJECTED}),
    _S.COMPLETED: frozenset(),
    _S.REJECTED: frozenset(),
}


class InvalidTransitionError(Exception):
    """A status change that the invoice lifecycle (data model §5) does not allow."""


def ensure_transition(current: InvoiceStatus, target: InvoiceStatus) -> None:
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransitionError(f"{current} -> {target}")
