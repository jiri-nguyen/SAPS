"""Integration: SAPS-22 approval through the API on a real PostgreSQL (TS-01 … TS-05, demo flows)."""

import asyncio
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import func, select, update

from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.models import Approval, MatchingSettings
from saps.domain.invoices import NotificationType
from tests.integration.api_world import Api

pytestmark = pytest.mark.integration

DS03 = "ds-03/invoices/ds-03-above-threshold.pdf"  # matched, total 495.00 → Pending approval
DS08 = "ds-08/invoices/ds-08-non-po.pdf"  # non-PO, 450.00 → EX2, accepted by a member → Pending approval
DS12 = "ds-12/invoices/ds-12-price-outside-tolerance.pdf"  # Exception


async def _waiting(api: Api, sample: str = DS03) -> uuid.UUID:
    invoice_id = await api.sample(sample)
    assert (await api.get(invoice_id))["status"] == "PENDING_APPROVAL"
    return invoice_id


async def _approvals(api: Api, invoice_id: uuid.UUID) -> int:
    async with session_factory(api.engine)() as session:
        count = await session.scalar(
            select(func.count()).select_from(Approval).where(Approval.invoice_id == invoice_id)
        )
    return count or 0


# TS-01 -----------------------------------------------------------------------------------------------


async def test_approve_goes_to_review_and_notifies_the_members(api: Api) -> None:
    invoice_id = await _waiting(api)
    waiting = await api.notifications(invoice_id)  # the managers were asked to approve, the members not yet
    assert waiting == {
        "Manager": [NotificationType.APPROVAL_REQUESTED],
        "Second Manager": [NotificationType.APPROVAL_REQUESTED],
    }
    response = await api.decide("manager", invoice_id, "APPROVED", "  Within budget.  ")
    assert response.status_code == 200 and response.headers["etag"].startswith('W/"')
    body = response.json()
    assert body["status"] == "PENDING_REVIEW"
    assert body["approval"]["decision"] == "APPROVED" and body["approval"]["comment"] == "Within budget."
    assert body["approval"]["decidedBy"]["displayName"] == "Manager"
    notified = await api.notifications(invoice_id)
    assert notified["Member"] == [NotificationType.REVIEW_REQUESTED]  # BR-04
    assert notified["Bob"] == [NotificationType.REVIEW_REQUESTED]
    assert notified["Manager"] == waiting["Manager"]  # no new notification for the managers
    assert await _approvals(api, invoice_id) == 1


async def test_approve_without_a_comment(api: Api) -> None:
    invoice_id = await _waiting(api)
    response = await api.decide("manager", invoice_id, "APPROVED")
    assert response.status_code == 200 and response.json()["approval"]["comment"] is None


# TS-02 -----------------------------------------------------------------------------------------------


async def test_reject_with_a_comment_is_final_and_notifies_nobody(api: Api) -> None:
    invoice_id = await _waiting(api)
    before = await api.notifications(invoice_id)
    response = await api.decide("manager", invoice_id, "REJECTED", "Price is not agreed.")
    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["rejectedReason"]) == ("REJECTED", "Price is not agreed.")
    assert body["approval"]["decision"] == "REJECTED"
    assert await api.notifications(invoice_id) == before  # BR-05, DEC-040
    assert (await api.decide("manager2", invoice_id, "APPROVED")).status_code == 409  # a final state


@pytest.mark.parametrize("comment", [None, "", "   "])
async def test_reject_needs_a_comment(api: Api, comment: str | None) -> None:  # EC-02
    invoice_id = await _waiting(api)
    response = await api.decide("manager", invoice_id, "REJECTED", comment)
    assert response.status_code == 422 and "comment is required" in response.json()["detail"]
    assert (await api.get(invoice_id))["status"] == "PENDING_APPROVAL"
    assert await _approvals(api, invoice_id) == 0


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"decision": "MAYBE"},
        {"decision": "APPROVED", "comment": "x" * 1001},
        {"decision": "APPROVED", "extra": 1},
    ],
)
async def test_invalid_requests_are_400(api: Api, body: dict[str, object]) -> None:
    invoice_id = await _waiting(api)
    response = await api.request("manager", "POST", f"/v1/invoices/{invoice_id}/approval", json=body)
    assert response.status_code == 400 and response.headers["content-type"] == "application/problem+json"


# TS-03 -----------------------------------------------------------------------------------------------


async def test_two_managers_deciding_at_once_one_wins(api: Api) -> None:  # EC-01, DEC-038
    invoice_id = await _waiting(api)
    responses = await asyncio.gather(
        api.decide("manager", invoice_id, "APPROVED"), api.decide("manager2", invoice_id, "REJECTED", "No.")
    )
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert await _approvals(api, invoice_id) == 1
    loser = next(r for r in responses if r.status_code == 409)
    assert "does not wait for approval" in loser.json()["detail"]


# TS-04 -----------------------------------------------------------------------------------------------


async def test_members_cannot_decide(api: Api) -> None:  # EC-03, DS-19
    invoice_id = await _waiting(api)
    for who in ("alice", "bob"):
        response = await api.decide(who, invoice_id, "APPROVED")
        assert (
            response.status_code == 403
            and response.json()["detail"] == "Your role is not allowed for this operation."
        )
    assert (await api.get(invoice_id))["status"] == "PENDING_APPROVAL"


async def test_only_invoices_waiting_for_approval(api: Api) -> None:  # EC-04
    exception = await api.sample(DS12)
    response = await api.decide("manager", exception, "APPROVED")
    assert response.status_code == 409 and "Exception" in response.json()["detail"]
    approved = await _waiting(api)
    await api.decide("manager", approved, "APPROVED")
    again = await api.decide("manager2", approved, "APPROVED")
    assert again.status_code == 409 and "Pending review" in again.json()["detail"]
    assert (await api.decide("manager", uuid.uuid4(), "APPROVED")).status_code == 404


# TS-05 -----------------------------------------------------------------------------------------------


async def test_a_threshold_change_does_not_affect_invoices_already_waiting(api: Api) -> None:  # BR-09, EC-05
    invoice_id = await _waiting(api)
    async with session_factory(api.engine)() as session, session.begin():
        await session.execute(
            update(MatchingSettings)
            .where(MatchingSettings.tenant_id == api.world.tenant[0])
            .values(approval_threshold_usd=Decimal("1000"))  # 495.00 would not need approval any more
        )
    body = await api.get(invoice_id)
    assert (body["status"], body["approvalThresholdApplied"], body["requiresApproval"]) == (
        "PENDING_APPROVAL",
        "300.00",
        True,
    )
    assert (await api.decide("manager", invoice_id, "APPROVED")).status_code == 200


# Events and demo flows --------------------------------------------------------------------------------------


async def test_decisions_are_recorded_as_events(api: Api) -> None:  # BR-08
    approved, rejected = (
        await _waiting(api),
        await _waiting(api, "ds-16/invoices/ds-16-rejected-at-approval.pdf"),
    )
    await api.decide("manager", approved, "APPROVED", "OK.")
    await api.decide("manager2", rejected, "REJECTED", "Not ordered by us.")
    last = (await api.request("alice", "GET", f"/v1/invoices/{approved}/events")).json()["items"][-1]
    assert (last["action"], last["statusFrom"], last["statusTo"], last["actor"]) == (
        "APPROVE",
        "PENDING_APPROVAL",
        "PENDING_REVIEW",
        "Manager",
    )
    assert last["details"] == {"decision": "APPROVED", "comment": "OK."}
    last = (await api.request("alice", "GET", f"/v1/invoices/{rejected}/events")).json()["items"][-1]
    assert (last["action"], last["statusTo"], last["actor"]) == ("REJECT", "REJECTED", "Second Manager")
    assert last["details"] == {"decision": "REJECTED", "comment": "Not ordered by us."}


async def test_ds08_a_member_accepts_ex2_and_the_manager_sees_it_before_approving(
    api: Api,
) -> None:  # BR-07, EC-06
    invoice_id = await api.sample(DS08)
    await api.claim("alice", invoice_id)
    assert (await api.resolve("alice", invoice_id)).json()["status"] == "PENDING_APPROVAL"
    body = await api.get(invoice_id, "manager")
    [accepted] = [e for e in body["exceptions"] if e["status"] == "RESOLVED"]
    assert (
        accepted["code"] == "EX2"
        and accepted["resolvedBy"]["displayName"] == "Member"
        and accepted["resolvedAt"]
    )
    response = await api.decide("manager", invoice_id, "APPROVED")
    assert response.status_code == 200 and response.json()["status"] == "PENDING_REVIEW"


async def test_the_manager_queue_lists_what_waits_for_approval(api: Api) -> None:
    waiting = await _waiting(api)
    await api.sample(DS12)  # in Exception: not in the approval queue
    page = (await api.request("manager", "GET", "/v1/invoices?status=PENDING_APPROVAL")).json()
    assert [item["id"] for item in page["items"]] == [str(waiting)]
    await api.decide("manager", waiting, "APPROVED")
    page = (await api.request("manager", "GET", "/v1/invoices?status=PENDING_APPROVAL")).json()
    assert page["items"] == []
