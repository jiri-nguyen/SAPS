"""Integration: SAPS-20 rules through the API on a real PostgreSQL (TS-01 … TS-09)."""

import asyncio
import uuid

import pytest
from sqlalchemy import select

from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.models import Notification, UserAccount
from saps.domain.invoices import NotificationType
from tests.integration.api_world import Api

pytestmark = pytest.mark.integration

DS12 = "ds-12/invoices/ds-12-price-outside-tolerance.pdf"  # EX6, 4 x 20.60 (PO price 20.00), total 90.64
DS08 = "ds-08/invoices/ds-08-non-po.pdf"  # EX2, total 450.00
DS13 = "ds-13/invoices/ds-13-quantity-above-expected.pdf"  # EX7
DS01 = "ds-01/invoices/ds-01-trade-po.pdf"  # Pending review, total 209.00
PRICE_OK = {
    "lines": [
        {
            "lineNumber": 1,
            "description": "USB keyboard",
            "poNumber": "0100012",
            "poLineNumber": 1,
            "quantity": "4",
            "unitPrice": "20.00",
            "lineAmount": "80.00",
        }
    ]
}


async def _codes(api: Api, invoice_id: uuid.UUID) -> list[str]:
    body = await api.get(invoice_id)
    return sorted({e["code"] for e in body["exceptions"] if e["status"] == "OPEN"}, key=lambda c: int(c[2:]))


# TS-01 -----------------------------------------------------------------------------------------------


async def test_claim_and_second_claim(api: Api) -> None:
    invoice_id = await api.sample(DS12)
    first = await api.claim("alice", invoice_id)
    assert first.status_code == 200 and first.json()["assignedTo"]["displayName"] == "Member"
    assert first.headers["etag"].startswith('W/"')
    second = await api.claim("bob", invoice_id)
    assert second.status_code == 409 and "already claimed" in second.json()["detail"]
    assert (await api.claim("alice", invoice_id)).status_code == 200  # claiming again changes nothing


async def test_parallel_claims_have_one_winner(api: Api) -> None:  # EC-01
    invoice_id = await api.sample(DS12)
    responses = await asyncio.gather(api.claim("alice", invoice_id), api.claim("bob", invoice_id))
    assert sorted(r.status_code for r in responses) == [200, 409]


async def test_only_invoices_in_exception_can_be_claimed(api: Api) -> None:
    invoice_id = await api.sample(DS01)  # Pending review
    response = await api.claim("alice", invoice_id)
    assert response.status_code == 409 and "Pending review" in response.json()["detail"]
    assert (await api.claim("alice", uuid.uuid4())).status_code == 404


# TS-02 -----------------------------------------------------------------------------------------------


async def test_non_claimants_and_managers_cannot_change_the_invoice(api: Api) -> None:
    invoice_id = await api.sample(DS12)
    unclaimed = await api.update("alice", invoice_id, PRICE_OK)
    assert unclaimed.status_code == 403 and unclaimed.json()["detail"] == "Claim the invoice first."
    await api.claim("alice", invoice_id)
    for call in (
        api.update("bob", invoice_id, PRICE_OK),
        api.resolve("bob", invoice_id),
        api.reject("bob", invoice_id),
    ):
        response = await call
        assert (
            response.status_code == 403
            and response.json()["detail"] == "The invoice is claimed by another member."
        )
    for call in (
        api.claim("manager", invoice_id),
        api.update("manager", invoice_id, PRICE_OK),
        api.resolve("manager", invoice_id),
        api.reject("manager", invoice_id),
    ):
        response = await call
        assert response.status_code == 403
        assert response.json()["detail"] == "Your role is not allowed for this operation."


# TS-03 -----------------------------------------------------------------------------------------------


async def test_release_rules(api: Api) -> None:
    invoice_id = await api.sample(DS12)
    assert (await api.release("alice", invoice_id)).status_code == 409  # not claimed
    await api.claim("alice", invoice_id)
    assert (await api.release("bob", invoice_id)).status_code == 403  # another member's claim
    assert (await api.release("alice", invoice_id)).status_code == 204
    assert (await api.get(invoice_id))["assignedTo"] is None
    await api.claim("bob", invoice_id)
    assert (
        await api.release("manager", invoice_id)
    ).status_code == 204  # a manager releases any claim (DEC-036)
    assert (await api.get(invoice_id))["assignedTo"] is None
    assert (await api.claim("alice", invoice_id)).status_code == 200  # back in the queue


# TS-04 -----------------------------------------------------------------------------------------------


async def test_matching_field_change_queues_a_rematch(api: Api) -> None:
    invoice_id = await api.sample(DS12)
    await api.claim("alice", invoice_id)
    response = await api.update("alice", invoice_id, PRICE_OK)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "MATCHING" and body["assignedTo"]["displayName"] == "Member"  # the claim stays
    assert body["lines"][0]["unitPrice"] == "20.0000"
    assert api.queue.rematch == [invoice_id]


async def test_other_fields_are_saved_without_rematch(api: Api) -> None:
    invoice_id = await api.sample(DS12)
    await api.claim("alice", invoice_id)
    response = await api.update(
        "alice",
        invoice_id,
        {"vendorName": "Alpha Office Supplies Co. (corrected)", "invoiceDate": "2026-12-20"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "EXCEPTION" and body["vendorName"].endswith("(corrected)")
    assert body["invoiceDate"] == "2026-12-20" and api.queue.rematch == []


async def test_update_without_a_real_change_saves_nothing(api: Api) -> None:  # EC-08
    invoice_id = await api.sample(DS12)
    await api.claim("alice", invoice_id)
    before = await api.etag(invoice_id)
    response = await api.update("alice", invoice_id, {"vendorCode": "V001"}, etag=before)
    assert response.status_code == 200 and response.headers["etag"] == before
    events = await api.request("alice", "GET", f"/v1/invoices/{invoice_id}/events")
    assert [e["action"] for e in events.json()["items"]].count("UPDATE_FIELDS") == 0


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"vendorCode": None},
        {"vendorCode": ""},
        {"vendorCode": "V" * 21},
        {"status": "COMPLETED"},
        {"totalAmount": "1.234"},
        {"lines": []},
        {"lines": [{"lineNumber": 1, "poNumber": "123"}]},
        {"lines": [{"lineNumber": 0}]},
        {"lines": [{"lineNumber": 1, "quantity": "-1"}]},
    ],
)
async def test_invalid_updates_are_400(api: Api, body: dict[str, object]) -> None:
    invoice_id = await api.sample(DS12)
    await api.claim("alice", invoice_id)
    response = await api.update("alice", invoice_id, body)
    assert response.status_code == 400 and response.headers["content-type"] == "application/problem+json"


async def test_duplicate_line_numbers_are_422(api: Api) -> None:
    invoice_id = await api.sample(DS12)
    await api.claim("alice", invoice_id)
    line = PRICE_OK["lines"][0]
    response = await api.update("alice", invoice_id, {"lines": [line, line]})
    assert response.status_code == 422 and "unique line numbers" in response.json()["detail"]


# TS-05 -----------------------------------------------------------------------------------------------


async def test_stale_and_missing_etag(api: Api) -> None:  # EC-02
    invoice_id = await api.sample(DS12)
    await api.claim("alice", invoice_id)
    stale = await api.etag(invoice_id)
    assert (await api.update("alice", invoice_id, {"vendorName": "Changed"}, etag=stale)).status_code == 200
    for call in (
        api.update("alice", invoice_id, {"vendorName": "Again"}, etag=stale),
        api.resolve("alice", invoice_id, etag=stale),
    ):
        response = await call
        assert response.status_code == 412 and "changed since you loaded it" in response.json()["detail"]
    missing = await api.request("alice", "PATCH", f"/v1/invoices/{invoice_id}", json={"vendorName": "X"})
    assert missing.status_code == 428
    missing = await api.request("alice", "POST", f"/v1/invoices/{invoice_id}/resolution")
    assert missing.status_code == 428
    current = await api.etag(invoice_id)  # an unquoted or strong form of the same ETag is accepted too
    assert (
        await api.update("alice", invoice_id, {"vendorName": "Fine"}, etag=current.removeprefix("W/"))
    ).status_code == 200


# TS-06 -----------------------------------------------------------------------------------------------


async def test_nothing_can_be_done_while_matching(api: Api) -> None:  # EC-03
    invoice_id = await api.sample(DS12)
    await api.claim("alice", invoice_id)
    assert (await api.update("alice", invoice_id, PRICE_OK)).status_code == 202
    for call in (
        api.update("alice", invoice_id, {"vendorName": "X"}),
        api.resolve("alice", invoice_id),
        api.reject("alice", invoice_id),
        api.claim("bob", invoice_id),
        api.release("alice", invoice_id),
    ):
        response = await call
        assert response.status_code == 409 and response.json()["detail"] == "Re-matching is in progress."


# TS-07 -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sample", "code", "status", "requires_approval"),
    [
        (DS08, "EX2", "PENDING_APPROVAL", True),  # 450.00 is above the threshold of 300
        (DS12, "EX6", "PENDING_REVIEW", False),
        (DS13, "EX7", "PENDING_REVIEW", False),
    ],
)
async def test_acceptable_exceptions_are_resolved(
    api: Api, sample: str, code: str, status: str, requires_approval: bool
) -> None:
    invoice_id = await api.sample(sample)
    assert await _codes(api, invoice_id) == [code]
    await api.claim("alice", invoice_id)
    response = await api.resolve("alice", invoice_id)
    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["requiresApproval"], body["assignedTo"]) == (status, requires_approval, None)
    assert body["approvalThresholdApplied"] == "300.00"
    [exception] = [e for e in body["exceptions"] if e["code"] == code]
    assert exception["status"] == "RESOLVED" and exception["resolvedBy"]["displayName"] == "Member"


async def test_a_duplicate_can_be_accepted_as_is(api: Api) -> None:  # EX9 (and EX7 of the same invoice)
    await api.sample(DS01)
    second = await api.sample("ds-15/invoices/ds-15-duplicate-scan.png")
    assert await _codes(api, second) == ["EX7", "EX9"]
    await api.claim("bob", second)
    response = await api.resolve("bob", second)
    assert response.status_code == 200 and response.json()["status"] == "PENDING_REVIEW"


@pytest.mark.parametrize(
    ("sample", "codes"),
    [
        ("ds-09/invoices/ds-09-invalid-po-number.pdf", "EX3"),
        ("ds-10/invoices/ds-10-po-not-found.pdf", "EX4"),
        ("ds-11/invoices/ds-11-trade-and-non-trade.pdf", "EX5"),
        ("ds-14/invoices/ds-14-missing-goods-receipt.pdf", "EX8"),
        ("ds-20/invoices/ds-20-vendor-mismatch.pdf", "EX10"),
        ("ds-07/unregistered/ds-07-unknown-invoice.pdf", "EX1"),
    ],
)
async def test_other_exceptions_cannot_be_accepted_as_is(api: Api, sample: str, codes: str) -> None:  # EC-04
    invoice_id = await api.sample(sample)
    await api.claim("alice", invoice_id)
    response = await api.resolve("alice", invoice_id)
    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == f"{codes} cannot be accepted as is: correct the data or reject the invoice."
    )
    assert (await api.get(invoice_id))["status"] == "EXCEPTION"


async def test_resolve_with_a_missed_exception_among_acceptable_ones(api: Api) -> None:
    invoice_id = await api.sample("ds-09/invoices/ds-09-invalid-po-number.pdf")
    await api.claim("alice", invoice_id)
    assert (await api.resolve("alice", invoice_id)).status_code == 422
    assert await _codes(api, invoice_id) == ["EX3"]  # nothing was resolved


# TS-08 -----------------------------------------------------------------------------------------------


async def test_reject_needs_a_reason(api: Api) -> None:  # EC-09
    invoice_id = await api.sample("ds-10/invoices/ds-10-po-not-found.pdf")
    await api.claim("alice", invoice_id)
    for body in ({}, {"reason": ""}, {"reason": "   "}, {"reason": "x" * 1001}):
        response = await api.request("alice", "POST", f"/v1/invoices/{invoice_id}/rejection", json=body)
        assert response.status_code == 400
    response = await api.reject("alice", invoice_id, "  PO 0199999 does not exist.  ")
    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["rejectedReason"], body["assignedTo"]) == (
        "REJECTED",
        "PO 0199999 does not exist.",
        None,
    )
    assert (await api.claim("bob", invoice_id)).status_code == 409  # final state


async def test_reject_is_only_for_invoices_in_exception(api: Api) -> None:
    invoice_id = await api.sample(DS01)  # Pending review: rejecting there comes with SAPS-21
    response = await api.reject("alice", invoice_id)
    assert response.status_code == 409 and "Pending review" in response.json()["detail"]


# TS-09 -----------------------------------------------------------------------------------------------


async def _notifications(api: Api, invoice_id: uuid.UUID) -> dict[str, list[NotificationType]]:
    async with session_factory(api.engine)() as session:
        rows = await session.execute(
            select(UserAccount.display_name, Notification.type, Notification.created_at)
            .join(UserAccount, UserAccount.id == Notification.recipient_id)
            .where(Notification.invoice_id == invoice_id)
            .order_by(Notification.created_at)
        )
    result: dict[str, list[NotificationType]] = {}
    for name, kind, _ in rows:
        result.setdefault(name, []).append(kind)
    return result


async def test_claim_ends_when_rematch_passes_and_resolve_notifies(api: Api) -> None:  # BR-09, BR-10
    invoice_id = await api.sample(DS12)
    assert await _notifications(api, invoice_id) == {
        "Member": [NotificationType.EXCEPTION_RAISED],
        "Bob": [NotificationType.EXCEPTION_RAISED],
    }
    await api.claim("alice", invoice_id)
    assert (await api.update("alice", invoice_id, PRICE_OK)).status_code == 202
    await api.rematch(invoice_id)  # the SAPS Worker
    body = await api.get(invoice_id)
    assert (body["status"], body["assignedTo"]) == ("PENDING_REVIEW", None)
    assert (await _notifications(api, invoice_id))["Bob"][-1] is NotificationType.REVIEW_REQUESTED


async def test_exception_again_after_rematch_notifies_only_the_claimant(api: Api) -> None:  # BR-10, DEC-037
    invoice_id = await api.sample(DS12)
    await api.claim("alice", invoice_id)
    still_wrong = {"lines": [{**PRICE_OK["lines"][0], "unitPrice": "21.00", "lineAmount": "84.00"}]}
    assert (await api.update("alice", invoice_id, still_wrong)).status_code == 202
    await api.rematch(invoice_id)
    body = await api.get(invoice_id)
    assert body["status"] == "EXCEPTION" and body["assignedTo"]["displayName"] == "Member"  # the claim stays
    notified = await _notifications(api, invoice_id)
    assert notified["Member"] == [NotificationType.EXCEPTION_RAISED] * 2
    assert notified["Bob"] == [NotificationType.EXCEPTION_RAISED]  # only the first time


async def test_resolve_notifies_the_next_step(api: Api) -> None:
    approval = await api.sample(DS08)
    await api.claim("alice", approval)
    await api.resolve("alice", approval)
    assert (await _notifications(api, approval))["Manager"] == [NotificationType.APPROVAL_REQUESTED]
    review = await api.sample(DS12)
    await api.claim("alice", review)
    await api.resolve("alice", review)
    assert (await _notifications(api, review))["Bob"][-1] is NotificationType.REVIEW_REQUESTED
