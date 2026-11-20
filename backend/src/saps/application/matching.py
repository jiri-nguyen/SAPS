"""Matching use case (SAPS-19), run by `rematch_invoice` and by `process_invoice` (SAPS-18)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from saps.application.notifications import notify_status
from saps.domain.invoices import (
    ExceptionCode,
    InvoiceStatus,
    InvoiceType,
    ensure_transition,
)
from saps.domain.matching import Finding, decide, derive_invoice_type, evaluate
from saps.ports.erp import ErpDataPort
from saps.ports.matching import InvoiceForMatching, MatchingRepository, MatchUpdate, NewException

SYSTEM_ACTOR = "system"
MATCH_ACTION = "MATCH"
# EX9 belongs to the duplicate check (SAPS-23); matching never opens or resolves it.
MATCHING_CODES = frozenset(ExceptionCode) - {ExceptionCode.EX9}


@dataclass(frozen=True)
class MatchOutcome:
    invoice_id: UUID
    tenant_id: UUID
    invoice_type: InvoiceType | None
    status: InvoiceStatus
    open_codes: tuple[ExceptionCode, ...]
    opened: tuple[ExceptionCode, ...]
    resolved: tuple[ExceptionCode, ...]


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

        rules = await self._repo.get_rules(invoice.tenant_id)
        derivation = derive_invoice_type(invoice.invoice)
        purchase_orders, receipts, invoiced = {}, [], {}
        if derivation.po_lines:
            purchase_orders = await self._erp.get_purchase_orders(derivation.po_numbers)
            if derivation.invoice_type is InvoiceType.TRADE_PO:
                receipts = await self._erp.get_goods_receipt_lines(derivation.po_numbers)
            keys = derivation.po_line_keys
            await self._repo.lock_po_lines(invoice.tenant_id, keys)
            invoiced = await self._repo.already_invoiced(invoice.tenant_id, keys, invoice.id)
        result = evaluate(invoice.invoice, derivation, rules, purchase_orders, receipts, invoiced)

        opened, resolved, messages = _reconcile(invoice, result.findings)
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
        )


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
