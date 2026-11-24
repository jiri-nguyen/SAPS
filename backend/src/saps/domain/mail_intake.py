"""Rules of the invoice intake from company mailboxes (SAPS-45). Pure domain code (ADR-0001)."""

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from saps.domain.invoice_files import (
    EmptyFileError,
    FileRejectedError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)

MAX_SENDER = 320
MAX_SUBJECT = 500


class IntakeChannel(StrEnum):
    UPLOAD = "UPLOAD"
    MAIL = "MAIL"


class InboundMailStatus(StrEnum):
    RECEIVED = "RECEIVED"  # being imported; a crash leaves it here and the next tick finishes it (EC-06)
    PROCESSED = "PROCESSED"  # at least one invoice
    SKIPPED = "SKIPPED"  # no valid attachment (BR-06)


class SkipReason(StrEnum):
    NO_VALID_ATTACHMENT = "no_valid_attachment"
    UNSUPPORTED_TYPE = "unsupported_type"
    TOO_LARGE = "too_large"
    EMPTY = "empty"


@dataclass(frozen=True)
class AttachmentResult:
    """What became of one attachment: an invoice, or skipped with the reason (BR-07)."""

    position: int
    name: str
    size_bytes: int
    invoice_id: UUID | None = None
    skip_reason: SkipReason | None = None


def mail_idempotency_key(mail_key: str, position: int) -> str:
    """One key per attachment: a retry after a crash returns the invoice already created (BR-05).

    At most 64 characters, like every idempotency key.
    """
    digest = hashlib.sha256(mail_key.encode()).hexdigest()[:40]
    return f"mail:{digest}:{position}"


def skip_reason_of(error: FileRejectedError) -> SkipReason:
    if isinstance(error, EmptyFileError):
        return SkipReason.EMPTY
    if isinstance(error, FileTooLargeError):
        return SkipReason.TOO_LARGE
    if isinstance(error, UnsupportedFileTypeError):
        return SkipReason.UNSUPPORTED_TYPE
    return SkipReason.UNSUPPORTED_TYPE


def final_status(results: list[AttachmentResult]) -> InboundMailStatus:
    """A mail with at least one invoice counts as processed (BR-07)."""
    if any(r.invoice_id is not None for r in results):
        return InboundMailStatus.PROCESSED
    return InboundMailStatus.SKIPPED


def overall_skip_reason(results: list[AttachmentResult]) -> SkipReason | None:
    if any(r.invoice_id is not None for r in results):
        return None
    return SkipReason.NO_VALID_ATTACHMENT


def clip(value: str | None, limit: int) -> str:
    """Sender and subject are shown as text only and stored shortened (spec §3.7)."""
    return (value or "").strip()[:limit]
