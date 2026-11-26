"""Mock ERP Posting Adapter (ADR-0013, DEC-064): accepts every posting until MuleSoft and the ERP exist.

The document number is derived from the invoice ID, so posting the same invoice again gives the same number.
"""

import hashlib

from saps.ports.erp_posting import PostingRequest, PostingResult


class MockErpPostingAdapter:
    async def post(self, request: PostingRequest) -> PostingResult:
        digest = hashlib.sha256(str(request.invoice_id).encode()).hexdigest()
        return PostingResult(f"MOCK-{digest[:10].upper()}")
