from uuid import UUID

import pytest

from saps.domain.invoice_files import (
    EmptyFileError,
    FileTooLargeError,
    UnsupportedFileTypeError,
    check_file,
    clean_file_name,
    detect_content_type,
    storage_key,
)
from tests.fakes import JPEG_BYTES, PDF_BYTES, PNG_BYTES

MB = 1024 * 1024


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (PDF_BYTES, "application/pdf"),
        (PNG_BYTES, "image/png"),
        (JPEG_BYTES, "image/jpeg"),
        (b"hello", None),
        (b"", None),
    ],
)
def test_type_comes_from_magic_bytes(content: bytes, expected: str | None) -> None:
    assert detect_content_type(content[:8]) == expected


def test_check_file_accepts_up_to_the_limit() -> None:
    assert check_file(10 * MB, PDF_BYTES[:8], 10 * MB) == "application/pdf"


@pytest.mark.parametrize(
    ("size", "head", "error", "message"),
    [
        (0, b"", EmptyFileError, "The file is empty."),
        (10 * MB + 1, PDF_BYTES[:8], FileTooLargeError, "The file is larger than 10 MB."),
        (5, b"hello", UnsupportedFileTypeError, "Only PDF, JPEG and PNG files are accepted."),
    ],
)
def test_check_file_refuses(size: int, head: bytes, error: type[Exception], message: str) -> None:
    with pytest.raises(error, match=message):
        check_file(size, head, 10 * MB)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("invoice.pdf", "invoice.pdf"),
        ("C:\\Users\\me\\scan 01.png", "scan 01.png"),
        ("../../etc/passwd", "passwd"),
        ("  ", "invoice"),
        (None, "invoice"),
        ("a" * 300, "a" * 255),
    ],
)
def test_file_name_is_cleaned(name: str | None, expected: str) -> None:
    assert clean_file_name(name) == expected


def test_storage_key_contains_only_the_company_id_and_hash() -> None:  # SAPS-41 BR-06
    tenant_id = UUID("87654321-4321-8765-4321-876543218765")
    invoice_id = UUID("12345678-1234-5678-1234-567812345678")
    assert (
        storage_key(tenant_id, invoice_id, "a" * 64)
        == f"tenants/{tenant_id}/invoices/{invoice_id}/{'a' * 64}"
    )
    with pytest.raises(ValueError, match="sha256"):
        storage_key(tenant_id, invoice_id, "../x")
