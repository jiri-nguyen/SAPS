"""Matching use case (SAPS-19), run by `rematch_invoice` and by `process_invoice` (SAPS-18)."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from saps.application.notifications import notify_status
from saps.domain.duplicates import DuplicateCandidate, duplicate_finding, normalize_invoice_number
from saps.domain.invoices import (
    ExceptionCode,
    InvoiceStatus,
    InvoiceType,
    ensure_transition,
)
from saps.domain.matching import (
    Finding,
    InvoicedQuantities,
    PurchaseOrder,
    TypeDerivation,
    decide,
    derive_invoice_type,
    evaluate,
)
from saps.ports.erp import ErpDataPort
from saps.ports.matching import InvoiceForMatching, MatchingRepository, MatchUpdate, NewException

SYSTEM_ACTOR = "system"
MATCH_ACTION = "MATCH"
# Codes a matching run opens and resolves: all of them, EX9 included, because the duplicate check
# (SAPS-23) runs inside the same run (process_invoice and rematch_invoice, SAPS-23 BR-06).
MATCHING_CODES = frozenset(ExceptionCode)


@dataclass(frozen=True)
class MatchOutcome:
    invoice_id: UUID
    tenant_id: UUID
    invoice_type: InvoiceType | None
    status: InvoiceStatus
    open_codes: tuple[ExceptionCode, ...]
    opened: tuple[ExceptionCode, ...]
    resolved: tuple[ExceptionCode, ...]
    duplicate_of: tuple[UUID, ...] = ()


class MatchingService:
    def __init__(
        self, repository: MatchingRepository, erp: ErpDataPort, clock: Callable[[], datetime]
    ) -> None:
        self._repo = repository
        self._erp = erp
        self._clock = clock

    async def match(self, invoice_id: UUID) -> MatchOutcome | None:
        """Match an invoice in status Matching. Returns None for a duplicate or stale message (EC-03)."""
        invoice = await self._repo.lock_invoice(invoice_id)
        if invoice is None or invoice.status is not InvoiceStatus.MATCHING:
            return None

        duplicates = await self._find_duplicates(invoice)
        rules = await self._repo.get_rules(invoice.tenant_id)
        derivation = derive_invoice_type(invoice.invoice)
        purchase_orders, receipts, pirs, invoiced = {}, [], [], InvoicedQuantities()
        if derivation.po_lines:
            purchase_orders = await self._erp.get_purchase_orders(invoice.company_code, derivation.po_numbers)
            if derivation.invoice_type is InvoiceType.TRADE_PO:
                receipts = await self._erp.get_goods_receipt_lines(
                    invoice.company_code, derivation.po_numbers
                )
                pirs = await self._erp.get_purchasing_info_records(
                    invoice.company_code, _pir_keys(derivation, purchase_orders)
                )
            await self._repo.lock_po_lines(invoice.tenant_id, derivation.po_line_keys)
            invoiced = await self._repo.already_invoiced(invoice.tenant_id, derivation.po_numbers, invoice.id)
        result = evaluate(invoice.invoice, derivation, rules, purchase_orders, receipts, invoiced, pirs)

        findings = result.findings + ((duplicate_finding(duplicates),) if duplicates else ())
        opened, resolved, messages = _reconcile(invoice, findings)
        open_codes = sorted(
            {e.code for e in invoice.open_exceptions if e.id not in resolved} | {f.code for f in opened},
            key=_code_order,
        )
        decision = decide(bool(open_codes), invoice.invoice.total_amount, rules)
        ensure_transition(invoice.status, decision.status)

        resolved_codes = sorted(
            {e.code for e in invoice.open_exceptions if e.id in resolved}, key=_code_order
        )
        opened_codes = sorted({f.code for f in opened}, key=_code_order)
        update = MatchUpdate(
            invoice_type=result.invoice_type,
            status=decision.status,
            requires_approval=decision.requires_approval,
            rules=rules,
            lines=result.lines,
            opened=opened,
            resolved=sorted(resolved),
            messages=messages,
            event_details={
                "invoiceType": result.invoice_type.value if result.invoice_type else None,
                "opened": [c.value for c in opened_codes],
                "resolved": [c.value for c in resolved_codes],
                "priceTolerance": str(rules.price_tolerance),
                "approvalThreshold": str(rules.approval_threshold),
            },
        )
        await self._repo.save_match(
            invoice, update, actor=SYSTEM_ACTOR, action=MATCH_ACTION, now=self._clock()
        )
        await notify_status(self._repo, invoice, decision.status, open_codes)
        return MatchOutcome(
            invoice.id,
            invoice.tenant_id,
            result.invoice_type,
            decision.status,
            tuple(open_codes),
            tuple(opened_codes),
            tuple(resolved_codes),
            tuple(c.id for c in duplicates),
        )

    async def _find_duplicates(self, invoice: InvoiceForMatching) -> list[DuplicateCandidate]:
        """SAPS-23: same tenant, vendor and normalized number; no check without both values (EC-06)."""
        vendor = invoice.invoice.vendor_code
        number = normalize_invoice_number(invoice.invoice_number)
        if not vendor or number is None:
            return []
        # Held until the job commits, so two copies processed in parallel cannot both pass (EC-01).
        await self._repo.lock_duplicate_key(invoice.tenant_id, vendor, number)
        return await self._repo.find_duplicates(invoice.tenant_id, vendor, number, invoice.id)


def _pir_keys(
    derivation: TypeDerivation, purchase_orders: Mapping[str, PurchaseOrder]
) -> list[tuple[str, str]]:
    """(vendor code, material number) of the referenced PO lines: one ERP call per invoice (NFR-SCAL-001)."""
    keys: set[tuple[str, str]] = set()
    for line in derivation.po_lines:
        order = purchase_orders.get(line.po_number or "")
        po_line = order.lines.get(line.po_line_number) if order and line.po_line_number is not None else None
        if order and po_line and po_line.material_number:
            keys.add((order.vendor_code, po_line.material_number))
    return sorted(keys)


def _code_order(code: ExceptionCode) -> int:
    return int(code.value[2:])


def _reconcile(
    invoice: InvoiceForMatching, findings: tuple[Finding, ...]
) -> tuple[list[NewException], set[UUID], dict[UUID, str]]:
    """BR-14: open new findings, resolve matching exceptions that no longer occur, keep the rest."""
    existing = {(e.code, e.line_id): e for e in invoice.open_exceptions}
    found: dict[tuple[ExceptionCode, UUID | None], Finding] = {}
    for finding in findings:
        found.setdefault((finding.code, finding.line_id), finding)  # EC-01: one per code and line

    opened = [NewException(f.code, f.line_id, f.message) for key, f in found.items() if key not in existing]
    resolved = {e.id for key, e in existing.items() if e.code in MATCHING_CODES and key not in found}
    messages = {existing[key].id: f.message for key, f in found.items() if key in existing}
    return opened, resolved, messages
