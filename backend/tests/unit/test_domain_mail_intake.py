"""Rules of the mail intake (SAPS-45 TS-01)."""

from uuid import uuid4

from saps.domain.invoice_files import (
    EmptyFileError,
    FileRejectedError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from saps.domain.mail_intake import (
    AttachmentResult,
    InboundMailStatus,
    SkipReason,
    clip,
    final_status,
    mail_idempotency_key,
    overall_skip_reason,
    skip_reason_of,
)


def test_the_idempotency_key_is_stable_short_and_per_attachment() -> None:
    key = mail_idempotency_key("<abc@mail.example.net>", 2)
    assert key == mail_idempotency_key("<abc@mail.example.net>", 2)
    assert key != mail_idempotency_key("<abc@mail.example.net>", 1)
    assert key != mail_idempotency_key("<other@mail.example.net>", 2)
    assert key.startswith("mail:") and key.endswith(":2") and len(key) <= 64


def test_skip_reasons_follow_the_error() -> None:
    assert skip_reason_of(EmptyFileError()) is SkipReason.EMPTY
    assert skip_reason_of(FileTooLargeError()) is SkipReason.TOO_LARGE
    assert skip_reason_of(UnsupportedFileTypeError()) is SkipReason.UNSUPPORTED_TYPE
    assert skip_reason_of(FileRejectedError()) is SkipReason.UNSUPPORTED_TYPE


def test_a_mail_with_one_invoice_is_processed_otherwise_skipped() -> None:
    invoice = AttachmentResult(1, "a.pdf", 10, invoice_id=uuid4())
    skipped = AttachmentResult(2, "b.pdf", 0, skip_reason=SkipReason.EMPTY)
    assert final_status([skipped, invoice]) is InboundMailStatus.PROCESSED
    assert overall_skip_reason([skipped, invoice]) is None
    assert final_status([skipped]) is InboundMailStatus.SKIPPED
    assert final_status([]) is InboundMailStatus.SKIPPED
    assert overall_skip_reason([skipped]) is SkipReason.NO_VALID_ATTACHMENT


def test_clip_shortens_and_handles_missing_text() -> None:
    assert clip("  hello  ", 3) == "hel" and clip(None, 5) == ""
