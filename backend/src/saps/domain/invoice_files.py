"""Rules for uploaded invoice files (SAPS-17). Pure domain code: no framework imports (ADR-0001)."""

import re
from uuid import UUID

PDF = "application/pdf"
JPEG = "image/jpeg"
PNG = "image/png"

# BR-02: the type comes from the content (magic bytes), not from the name or the declared content type.
_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"%PDF-", PDF),
    (b"\x89PNG\r\n\x1a\n", PNG),
    (b"\xff\xd8\xff", JPEG),
)
HEADER_BYTES = 8
"""Bytes needed to recognize every supported type."""

_SHA256 = re.compile(r"[0-9a-f]{64}")
_MAX_NAME = 255


class FileRejectedError(Exception):
    """The uploaded file cannot become an invoice."""


class EmptyFileError(FileRejectedError):
    pass


class FileTooLargeError(FileRejectedError):
    pass


class UnsupportedFileTypeError(FileRejectedError):
    pass


def detect_content_type(head: bytes) -> str | None:
    for signature, content_type in _SIGNATURES:
        if head.startswith(signature):
            return content_type
    return None


def check_file(size: int, head: bytes, max_size_bytes: int) -> str:
    """EC-01, EC-02: returns the content type of an acceptable file."""
    if size == 0:
        raise EmptyFileError("The file is empty.")
    if size > max_size_bytes:
        raise FileTooLargeError(f"The file is larger than {max_size_bytes // (1024 * 1024)} MB.")
    content_type = detect_content_type(head)
    if content_type is None:
        raise UnsupportedFileTypeError("Only PDF, JPEG and PNG files are accepted.")
    return content_type


def clean_file_name(name: str | None) -> str:
    """The original name without any path, at most 255 characters; only shown, never used as a storage key."""
    base = (name or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    return base[:_MAX_NAME] or "invoice"


def storage_key(invoice_id: UUID, sha256: str) -> str:
    """ADR-0006: `invoices/{invoice_id}/{sha256}`; contains no user input (§3.7)."""
    if not _SHA256.fullmatch(sha256):
        raise ValueError("sha256 must be 64 lower-case hex characters")
    return f"invoices/{invoice_id}/{sha256}"
