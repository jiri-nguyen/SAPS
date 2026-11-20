import hashlib
import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from saps.adapters.extraction.dummy_extraction import DummyExtractionAdapter, SampleSetError
from saps.ports.extraction import StoredFile

FIXTURES = Path(__file__).parents[2] / "fixtures"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


async def test_finds_a_sample_by_sha256_only() -> None:
    adapter = DummyExtractionAdapter(FIXTURES)
    assert adapter.sample_count == 19
    pdf = FIXTURES / "ds-01/invoices/ds-01-trade-po.pdf"
    result = await adapter.extract(StoredFile(_sha(pdf), "invoices/x/y", "application/pdf"))
    assert result is not None and result.invoice_number == "AOS-2026-1001" and len(result.lines) == 2
    unknown = FIXTURES / "ds-07/unregistered/ds-07-unknown-invoice.pdf"
    assert await adapter.extract(StoredFile(_sha(unknown), "k", "application/pdf")) is None


def _sample_set(tmp_path: Path, entries: list[dict[str, str]]) -> Path:
    folder = tmp_path / "ds-01" / "invoices"
    folder.mkdir(parents=True)
    shutil.copy(FIXTURES / "ds-01/invoices/ds-01-trade-po.json", folder / "a.json")
    (folder / "a.pdf").write_bytes(b"%PDF-a")
    (tmp_path / "manifest.json").write_text(json.dumps({"samples": entries}))
    return tmp_path


ENTRY = {"sha256": "a" * 64, "file": "ds-01/invoices/a.pdf", "data": "ds-01/invoices/a.json"}


@pytest.mark.parametrize(
    ("entries", "error"),
    [
        ([{**ENTRY, "file": "../secret.pdf"}], "unexpected path"),
        ([{**ENTRY, "file": "ds-01/invoices/missing.pdf"}], "does not exist"),
        ([ENTRY, ENTRY], "listed twice"),
    ],
)
def test_inconsistent_sample_sets_fail_at_load(
    tmp_path: Path, entries: list[dict[str, str]], error: str
) -> None:
    with pytest.raises(SampleSetError, match=error):
        DummyExtractionAdapter(_sample_set(tmp_path, entries))


def test_invalid_result_json_fails_at_load(tmp_path: Path) -> None:
    root = _sample_set(tmp_path, [ENTRY])
    (root / "ds-01/invoices/a.json").write_text('{"currency": "USD", "lines": [], "unknown": 1}')
    with pytest.raises(ValidationError):
        DummyExtractionAdapter(root)
