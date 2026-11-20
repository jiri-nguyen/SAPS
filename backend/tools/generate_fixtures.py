"""Generate the dummy sample set from its JSON extraction results (SAPS-18 BR-06, §3.8).

Run `make fixtures` in backend/. For each `fixtures/<scenario>/invoices/<name>.json` it renders the invoice
file the demo audience sees (PDF, or PNG / JPEG for the samples below) from the same values the system uses,
then writes `fixtures/manifest.json` (SHA-256 → file and JSON) and the JSON schema of a result.
Files under `fixtures/<scenario>/unregistered/` are rendered but never listed: unknown files (DS-07, EX1).
Output is deterministic, so running the generator twice changes nothing.
"""

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from saps.adapters.extraction.dummy_extraction import MANIFEST, ExtractedInvoiceFixture, load_sample

FIXTURES = Path(__file__).parents[1] / "fixtures"
SCHEMA = FIXTURES / "schema" / "extracted-invoice.schema.json"
BILL_TO = "PoC Customer"
# At least one sample per supported type (SAPS-18 §3.8); all others are PDF.
IMAGE_FORMATS = {
    "ds-02/invoices/ds-02-non-trade-po.json": "jpg",
    "ds-15/invoices/ds-15-duplicate-scan.json": "png",
}
COLUMNS = ("Line", "Description", "PO number", "PO line", "Quantity", "Unit price", "Amount")


def _text(value: object) -> str:
    return "" if value is None else str(value)


def invoice_text(sample: ExtractedInvoiceFixture, scenario: str) -> list[list[str] | str]:
    """The printed content, top to bottom: strings are text lines, lists are table rows."""
    rows: list[list[str] | str] = [
        f"{_text(sample.vendor_name)}   (vendor code {_text(sample.vendor_code)})",
        "INVOICE",
        f"Invoice number: {_text(sample.invoice_number)}",
        f"Invoice date: {_text(sample.invoice_date)}",
        f"Bill to: {BILL_TO}",
        f"Currency: {sample.currency}",
        "",
        list(COLUMNS),
    ]
    for line in sample.lines:
        rows.append(
            [
                str(line.line_number),
                _text(line.description),
                _text(line.po_number),
                _text(line.po_line_number),
                _text(line.quantity),
                _text(line.unit_price),
                _text(line.line_amount),
            ]
        )
    rows += [
        "",
        f"Subtotal: {_text(sample.subtotal_amount)}",
        f"Tax: {_text(sample.tax_amount)}",
        f"Total: {_text(sample.total_amount)}",
        "",
        f"Synthetic sample for the Smart-AP-Suite PoC demo, scenario {scenario.upper()}. Not a real invoice.",
    ]
    return rows


COLUMN_X = (
    40,
    75,
    270,
    345,
    395,
    455,
    520,
)  # left edges in points (PDF) and in pixels at 1 px = 1 pt (images)


def render_pdf(rows: list[list[str] | str], path: Path) -> None:
    canvas = Canvas(str(path), pagesize=A4, invariant=1)  # invariant: no timestamps or random IDs
    _, height = A4
    y = height - 50
    for row in rows:
        if isinstance(row, str):
            canvas.setFont(
                "Helvetica-Bold" if row == "INVOICE" else "Helvetica", 14 if row == "INVOICE" else 10
            )
            canvas.drawString(40, y, row)
        else:
            canvas.setFont("Helvetica-Bold" if row[0] == COLUMNS[0] else "Helvetica", 9)
            for x, cell in zip(COLUMN_X, row, strict=True):
                canvas.drawString(x, y, cell[:34])
        y -= 18
    canvas.showPage()
    canvas.save()


def render_image(rows: list[list[str] | str], path: Path, fmt: str) -> None:
    scale = 2
    image = Image.new("RGB", (595 * scale, (len(rows) * 18 + 80) * scale), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=10 * scale)
    y = 40
    for row in rows:
        cells = [(40, row)] if isinstance(row, str) else list(zip(COLUMN_X, row, strict=True))
        for x, cell in cells:
            draw.text(
                (x * scale, y * scale),
                cell[:34] if not isinstance(row, str) else cell,
                fill="black",
                font=font,
            )
        y += 18
    if fmt == "png":
        image.save(path, format="PNG", optimize=False)
    else:
        image.save(path, format="JPEG", quality=90, optimize=False, progressive=False)


def render(json_path: Path) -> Path:
    relative = json_path.relative_to(FIXTURES).as_posix()
    fmt = IMAGE_FORMATS.get(relative, "pdf")
    sample = load_sample(json_path)
    rows = invoice_text(sample, json_path.parts[-3])
    target = json_path.with_suffix(f".{fmt}")
    for stale in json_path.parent.glob(f"{json_path.stem}.*"):
        if stale.suffix != ".json" and stale != target:
            stale.unlink()
    if fmt == "pdf":
        render_pdf(rows, target)
    else:
        render_image(rows, target, fmt)
    return target


def main() -> int:
    entries = []
    for json_path in sorted(FIXTURES.glob("*/invoices/*.json")):
        file = render(json_path)
        entries.append(
            {
                "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                "file": file.relative_to(FIXTURES).as_posix(),
                "data": json_path.relative_to(FIXTURES).as_posix(),
            }
        )
    for json_path in sorted(FIXTURES.glob("*/unregistered/*.json")):
        render(json_path)
    (FIXTURES / MANIFEST).write_text(json.dumps({"samples": entries}, indent=2) + "\n")
    SCHEMA.parent.mkdir(exist_ok=True)
    SCHEMA.write_text(json.dumps(ExtractedInvoiceFixture.model_json_schema(), indent=2) + "\n")
    print(f"{len(entries)} samples, manifest and schema written to {FIXTURES}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
