"""Extraction Port (ADR-0001): invoice data from a stored file. Dummy sample set in the PoC (SAPS-18)."""

from dataclasses import dataclass
from typing import Protocol

from saps.domain.extraction import ExtractedInvoice


@dataclass(frozen=True)
class StoredFile:
    sha256: str
    storage_key: str
    content_type: str


class ExtractionPort(Protocol):
    async def extract(self, file: StoredFile) -> ExtractedInvoice | None:
        """The extraction result, or None when the file cannot be read (dummy: not in the sample set)."""
        ...
