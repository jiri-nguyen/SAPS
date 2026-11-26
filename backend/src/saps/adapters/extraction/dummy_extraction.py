"""Dummy Extraction Adapter (ADR-0001, DEC-012): extraction results looked up by the file's SHA-256.

`<FIXTURES_DIR>/manifest.json` lists every sample (SHA-256, sample file, JSON result).
All results are loaded and validated once; a broken manifest or result fails at load time,
not during a demo (SAPS-18 EC-04).
"""

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from saps.domain.extraction import ExtractedInvoice, ExtractedLine
from saps.ports.extraction import StoredFile

MANIFEST = "manifest.json"
_SAFE_PATH = re.compile(r"ds-\d{2}/invoices/[a-z0-9-]+\.(json|pdf|png|jpg)")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExtractedLineFixture(_Model):
    line_number: int
    description: str | None = None
    po_number: str | None = None
    po_line_number: int | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    line_amount: Decimal | None = None
    do_number: str | None = None


class ExtractedInvoiceFixture(_Model):
    """Schema of `<scenario>/invoices/<name>.json` (exported to `schema/extracted-invoice.schema.json`).

    Decimals are written as strings. Business limits (USD only, lines required) are domain rules (BR-04).
    """

    model_config = ConfigDict(
        extra="forbid", frozen=True, title="ExtractedInvoice", json_schema_extra={"$id": "extracted-invoice"}
    )

    vendor_code: str | None = None
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    subtotal_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None
    lines: list[ExtractedLineFixture]

    def to_domain(self) -> ExtractedInvoice:
        return ExtractedInvoice(
            vendor_code=self.vendor_code,
            vendor_name=self.vendor_name,
            invoice_number=self.invoice_number,
            invoice_date=self.invoice_date,
            currency=self.currency,
            subtotal_amount=self.subtotal_amount,
            tax_amount=self.tax_amount,
            total_amount=self.total_amount,
            lines=[ExtractedLine(**line.model_dump()) for line in self.lines],
        )


class ManifestEntry(_Model):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    file: str
    data: str


class Manifest(_Model):
    samples: list[ManifestEntry]


class SampleSetError(ValueError):
    """The dummy sample set is inconsistent."""


def load_sample(path: Path) -> ExtractedInvoiceFixture:
    return ExtractedInvoiceFixture.model_validate_json(path.read_bytes())


class DummyExtractionAdapter:
    def __init__(self, fixtures_dir: Path) -> None:
        manifest = Manifest.model_validate_json((fixtures_dir / MANIFEST).read_bytes())
        self._results: dict[str, ExtractedInvoice] = {}
        for entry in manifest.samples:
            for relative in (entry.file, entry.data):
                if not _SAFE_PATH.fullmatch(relative):
                    raise SampleSetError(f"{MANIFEST}: unexpected path {relative}")
                if not (fixtures_dir / relative).is_file():
                    raise SampleSetError(f"{MANIFEST}: {relative} does not exist")
            if entry.sha256 in self._results:
                raise SampleSetError(f"{MANIFEST}: SHA-256 {entry.sha256} is listed twice")
            self._results[entry.sha256] = load_sample(fixtures_dir / entry.data).to_domain()

    @property
    def sample_count(self) -> int:
        return len(self._results)

    async def extract(self, file: StoredFile) -> ExtractedInvoice | None:
        return self._results.get(file.sha256)
