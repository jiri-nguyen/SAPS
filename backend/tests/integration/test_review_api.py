"""Integration: SAPS-21 final review through the API on a real PostgreSQL (TS-01 … TS-04, demo chains)."""

import asyncio
import uuid

import pytest

from tests.integration.api_world import Api

pytestmark = pytest.mark.integration

DS01 = "ds-01/invoices/ds-01-trade-po.pdf"  # matched, 209.00 → Pending review
DS03 = "ds-03/invoices/ds-03-above-threshold.pdf"  # 495.00 → Pending approval
DS12 = "ds-12/invoices/ds-12-price-outside-tolerance.pdf"  # Exception
DS17 = "ds-17/invoices/ds-17-rejected-at-review.pdf"  # matched, 49.50 → Pending review


async def _reviewable(api: Api, sample: str = DS01) -> uuid.UUID:
    invoice_id = await api.sample(sample)
    assert (await api.get(invoice_id))["status"] == "PENDING_REVIEW"
    return invoice_id


async def _actions(api: Api, invoice_id: uuid.UUID) -> list[tuple[str, str]]:
    events = (await api.request("alice", "GET", f"/v1/invoices/{invoice_id}/events")).json()["items"]
    return [(e["action"], e["actor"]) for e in events]


# TS-01 / BR-02 ---------------------------------------------------------------------------------------


async def test_confirm_completes_the_invoice(api: Api) -> None:
    invoice_id = await _reviewable(api)
    response = await api.confirm("alice", invoice_id)  # alice uploaded it: no four-eyes rule (DEC-041)
    assert response.status_code == 200 and response.headers["etag"].startswith('W/"')
    body = response.json()
    assert (body["status"], body["assignedTo"]) == ("COMPLETED", None)
    assert (await _actions(api, invoice_id))[-1] == ("CONFIRM", "Member")
    last = (await api.request("alice", "GET", f"/v1/invoices/{invoice_id}/events")).json()["items"][-1]
    assert (last["statusFrom"], last["statusTo"]) == ("PENDING_REVIEW", "COMPLETED")


async def test_any_member_reviews_without_a_claim(api: Api) -> None:  # BR-02
    invoice_id = await _reviewable(api)
    assert (await api.confirm("bob", invoice_id)).status_code == 200


# TS-02 -----------------------------------------------------------------------------------------------


async def test_reject_at_review_needs_a_reason_and_notifies_nobody(api: Api) -> None:  # BR-04, EC-02
    invoice_id = await _reviewable(api, DS17)
    before = await api.notifications(invoice_id)
    for body in ({}, {"reason": ""}, {"reason": "   "}):
        response = await api.request("bob", "POST", f"/v1/invoices/{invoice_id}/rejection", json=body)
        assert response.status_code == 400
    response = await api.reject("bob", invoice_id, "Delivered to the wrong site.")
    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["rejectedReason"]) == ("REJECTED", "Delivered to the wrong site.")
    assert await api.notifications(invoice_id) == before  # DEC-040
    assert (await _actions(api, invoice_id))[-1] == ("REJECT", "Bob")


# TS-03 -----------------------------------------------------------------------------------------------


async def test_two_members_acting_at_once_one_wins(api: Api) -> None:  # EC-01
    invoice_id = await _reviewable(api)
    responses = await asyncio.gather(api.confirm("alice", invoice_id), api.reject("bob", invoice_id, "No."))
    assert sorted(r.status_code for r in responses) == [200, 409]
    status = (await api.get(invoice_id))["status"]
    assert status in {"COMPLETED", "REJECTED"}
    actions = [action for action, _ in await _actions(api, invoice_id)]
    assert actions.count("CONFIRM") + actions.count("REJECT") == 1


# TS-04 -----------------------------------------------------------------------------------------------


async def test_managers_cannot_confirm_or_reject_at_review(api: Api) -> None:  # EC-03
    invoice_id = await _reviewable(api)
    for response in (await api.confirm("manager", invoice_id), await api.reject("manager", invoice_id)):
        assert response.status_code == 403
    assert (await api.get(invoice_id))["status"] == "PENDING_REVIEW"


@pytest.mark.parametrize(("sample", "label"), [(DS12, "Exception"), (DS03, "Pending approval")])
async def test_confirm_only_in_pending_review(api: Api, sample: str, label: str) -> None:  # EC-04
    invoice_id = await api.sample(sample)
    response = await api.confirm("alice", invoice_id)
    assert response.status_code == 409 and label in response.json()["detail"]


async def test_final_states_cannot_be_changed(api: Api) -> None:
    invoice_id = await _reviewable(api)
    await api.confirm("alice", invoice_id)
    again = await api.confirm("bob", invoice_id)
    assert again.status_code == 409 and "Completed" in again.json()["detail"]
    assert (await api.reject("bob", invoice_id)).status_code == 409
    assert (await api.confirm("alice", uuid.uuid4())).status_code == 404


# Demo chains (Test Strategy §11) ------------------------------------------------------------------------


async def test_ds03_approved_then_confirmed(api: Api) -> None:
    invoice_id = await api.sample(DS03)
    assert (await api.decide("manager", invoice_id, "APPROVED")).json()["status"] == "PENDING_REVIEW"
    body = (await api.confirm("bob", invoice_id)).json()
    assert (
        body["status"] == "COMPLETED" and body["approval"]["decision"] == "APPROVED"
    )  # BR-05: shown at review
    assert [a for a, _ in await _actions(api, invoice_id)] == ["EXTRACT", "MATCH", "APPROVE", "CONFIRM"]


async def test_ds12_corrected_then_confirmed(api: Api) -> None:
    invoice_id = await api.sample(DS12)
    await api.claim("alice", invoice_id)
    line = {"lineNumber": 1, "description": "USB keyboard", "poNumber": "0100012", "poLineNumber": 1}
    fix = {"lines": [{**line, "quantity": "4", "unitPrice": "20.00", "lineAmount": "80.00"}]}
    assert (await api.update("alice", invoice_id, fix)).status_code == 202
    await api.rematch(invoice_id)
    assert (await api.confirm("bob", invoice_id)).json()["status"] == "COMPLETED"


async def test_the_review_queue(api: Api) -> None:
    waiting = await _reviewable(api)
    await api.sample(DS12)  # Exception: not in the review queue
    page = (await api.request("bob", "GET", "/v1/invoices?status=PENDING_REVIEW")).json()
    assert [item["id"] for item in page["items"]] == [str(waiting)]
    await api.confirm("bob", waiting)
    assert (await api.request("bob", "GET", "/v1/invoices?status=PENDING_REVIEW")).json()["items"] == []
