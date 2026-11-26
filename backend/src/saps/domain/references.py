"""Normalization of document references (DEC-042, DEC-065). Pure domain code (ADR-0001)."""

import re

_IGNORED = re.compile(r"[\s\-./]")


def normalize_reference(value: str | None) -> str | None:
    """Ignore case, spaces, `-`, `.` and `/`; keep leading zeros. "INV-0001" = "inv 0001". Empty → None."""
    if value is None:
        return None
    normalized = _IGNORED.sub("", value).casefold()
    return normalized or None
