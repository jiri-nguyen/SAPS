"""The dummy sample set is consistent (SAPS-18 TS-04, TS-05, TS-06); runs in CI."""

import hashlib
import json
import re
from pathlib import Path

import pytest
from pypdf import PdfReader

from saps.adapters.extraction.dummy_extraction import MANIFEST, ExtractedInvoiceFixture, Manifest, load_sample
from saps.domain.extraction import unusable_reason

FIXTURES = Path(__file__).parents[2] / "fixtures"
MANIFEST_DATA = Manifest.model_validate_json((FIXTURES / MANIFEST).read_bytes())
SAMPLES = MANIFEST_DATA.samples
NO_SAMPLE_NEEDED = {"ds-19"}  # sign-in and role access only


def test_every_sample_file_matches_its_manifest_hash() -> None:  # TS-04, EC-05
    for entry in SAMPLES:
        content = (FIXTURES / entry.file).read_bytes()
        assert hashlib.sha256(content).hexdigest() == entry.sha256, f"{entry.file}: run `make fixtures`"


def test_every_result_is_listed_once_with_one_file() -> None:
    listed = sorted(entry.data for entry in SAMPLES)
    on_disk = sorted(p.relative_to(FIXTURES).as_posix() for p in FIXTURES.glob("*/invoices/*.json"))
    assert listed == on_disk
    for entry in SAMPLES:
        assert Path(entry.file).stem == Path(entry.data).stem
        siblings = [
            p
            for p in (FIXTURES / entry.data).parent.glob(f"{Path(entry.data).stem}.*")
            if p.suffix != ".json"
        ]
        assert [p.name for p in siblings] == [Path(entry.file).name]


def test_every_result_is_valid_and_usable() -> None:  # TS-04, BR-04
    for entry in SAMPLES:
        assert unusable_reason(load_sample(FIXTURES / entry.data).to_domain()) is None, entry.data


def test_committed_schema_is_up_to_date() -> None:
    committed = json.loads((FIXTURES / "schema" / "extracted-invoice.schema.json").read_text())
    assert committed == ExtractedInvoiceFixture.model_json_schema(), "run `make fixtures`"


def test_every_demo_scenario_has_its_samples() -> None:  # TS-05, BR-07
    scenarios = {f"ds-{n:02d}" for n in range(1, 21)} - NO_SAMPLE_NEEDED
    with_samples = {Path(entry.data).parts[0] for entry in SAMPLES}
    unregistered = {p.parts[-3] for p in FIXTURES.glob("*/unregistered/*.*") if p.suffix != ".json"}
    assert scenarios == with_samples | unregistered
    assert unregistered == {"ds-07"}


def test_unregistered_files_are_not_in_the_sample_set() -> None:  # DS-07 → EX1
    hashes = {entry.sha256 for entry in SAMPLES}
    files = [p for p in FIXTURES.glob("*/unregistered/*") if p.suffix != ".json"]
    assert files
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() not in hashes for p in files)


def test_each_supported_file_type_has_a_sample() -> None:
    assert {Path(entry.file).suffix for entry in SAMPLES} == {".pdf", ".png", ".jpg"}


@pytest.mark.parametrize("entry", [e for e in SAMPLES if e.file.endswith(".pdf")], ids=lambda e: e.file)
def test_pdf_shows_the_values_of_its_json(entry) -> None:
    text = " ".join(page.extract_text() for page in PdfReader(FIXTURES / entry.file).pages)
    text = re.sub(r"\s+", " ", text)
    sample = load_sample(FIXTURES / entry.data)
    expected = [sample.invoice_number, sample.vendor_name, str(sample.total_amount)]
    for line in sample.lines:
        expected += [line.po_number, str(line.quantity), str(line.unit_price), str(line.line_amount)]
    for value in expected:
        if value is not None:
            assert value in text, f"{entry.file}: {value!r} not shown"
