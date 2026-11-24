"""Integration: SAPS-24 notifications through the API on a real PostgreSQL (TS-01 … TS-05)."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import func, select, update

from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.models import Notification, UserAccount
from saps.adapters.persistence.notification_repository import SqlNotifications
from saps.domain.invoices import NotificationType
from saps.domain.users import CurrentUser, Role
from tests.integration.api_world import Api
from tests.integration.pipeline import FIXTURES, process, uploaded

pytestmark = pytest.mark.integration

PATH = "/v1/notifications"
DS01 = "ds-01/invoices/ds-01-trade-po.pdf"  # → Pending review
DS03 = "ds-03/invoices/ds-03-above-threshold.pdf"  # → Pending approval
DS12 = "ds-12/invoices/ds-12-price-outside-tolerance.pdf"  # → Exception (EX6)


async def _list(api: Api, who: str, query: str = "") -> dict[str, Any]:
    response = await api.request(who, "GET", f"{PATH}{query}")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def _types(api: Api, who: str, query: str = "") -> list[str]:
    return [item["type"] for item in (await _list(api, who, query))["items"]]


async def _add_notifications(api: Api, invoice_id: uuid.UUID, who: str, count: int) -> list[uuid.UUID]:
    """`count` notifications for a user, created one second apart (paging scenarios)."""
    user = api.users[who]
    start = datetime.now(UTC) - timedelta(minutes=5)
    ids = [uuid.uuid4() for _ in range(count)]
    async with session_factory(api.engine)() as session, session.begin():
        session.add_all(
            Notification(
                id=notification_id,
                tenant_id=user.tenant_id,
                recipient_id=user.user_id,
                invoice_id=invoice_id,
                type=NotificationType.REVIEW_REQUESTED,
                message=f"Test notification {i}.",
                created_at=start + timedelta(seconds=i),
            )
            for i, notification_id in enumerate(ids)
        )
    return ids


# TS-01 / BR-01 -----------------------------------------------------------------------------------------


async def test_the_exception_reaches_the_members_and_not_the_manager(api: Api) -> None:
    invoice_id = await api.sample(DS12)
    for who in ("alice", "bob"):
        page = await _list(api, who)
        assert page["unreadCount"] == 1 and page["nextPageToken"] is None
        [item] = page["items"]
        assert (item["type"], item["invoiceId"], item["readAt"]) == (
            "EXCEPTION_RAISED",
            str(invoice_id),
            None,
        )
        assert "has exceptions: EX6" in item["message"] and item["createdAt"]
    assert await _list(api, "manager") == {"items": [], "nextPageToken": None, "unreadCount": 0}


async def test_approval_then_review_notify_the_right_roles_newest_first(api: Api) -> None:
    waiting = await api.sample(DS03)
    assert await _types(api, "manager") == ["APPROVAL_REQUESTED"]
    assert await _types(api, "manager2") == ["APPROVAL_REQUESTED"]
    assert await _types(api, "alice") == []  # members are not asked before the approval
    await api.decide("manager", waiting, "APPROVED")
    reviewed = await api.sample(DS01)
    assert await _types(api, "alice") == ["REVIEW_REQUESTED", "REVIEW_REQUESTED"]
    items = (await _list(api, "bob"))["items"]
    assert [i["invoiceId"] for i in items] == [str(reviewed), str(waiting)]  # newest first
    assert await _types(api, "manager") == ["APPROVAL_REQUESTED"]  # no new one for managers


# TS-05 / BR-06, EC-03 ----------------------------------------------------------------------------------


async def test_mark_one_read_is_idempotent_and_updates_the_count(api: Api) -> None:
    await api.sample(DS12)
    await api.sample(DS01)
    first, second = (await _list(api, "alice"))["items"]
    assert (await _list(api, "alice"))["unreadCount"] == 2

    assert (await api.request("alice", "POST", f"{PATH}/{first['id']}/read")).status_code == 204
    assert (await api.request("alice", "POST", f"{PATH}/{first['id']}/read")).status_code == 204  # EC-03
    page = await _list(api, "alice")
    assert page["unreadCount"] == 1
    assert [(i["id"], i["readAt"] is not None) for i in page["items"]] == [
        (first["id"], True),
        (second["id"], False),
    ]
    assert [i["id"] for i in (await _list(api, "alice", "?unreadOnly=true"))["items"]] == [second["id"]]
    assert (await _list(api, "bob"))["unreadCount"] == 2  # read state is per user


async def test_a_read_notification_keeps_its_first_read_time(api: Api) -> None:
    await api.sample(DS12)
    [item] = (await _list(api, "alice"))["items"]
    await api.request("alice", "POST", f"{PATH}/{item['id']}/read")
    read_at = (await _list(api, "alice"))["items"][0]["readAt"]
    await api.request("alice", "POST", f"{PATH}/{item['id']}/read")
    assert (await _list(api, "alice"))["items"][0]["readAt"] == read_at


async def test_mark_all_read_touches_only_the_caller(api: Api) -> None:
    await api.sample(DS12)
    await api.sample(DS01)
    assert (await api.request("alice", "POST", f"{PATH}/read-all")).status_code == 204
    assert (await api.request("alice", "POST", f"{PATH}/read-all")).status_code == 204  # idempotent
    page = await _list(api, "alice")
    assert page["unreadCount"] == 0 and all(i["readAt"] for i in page["items"]) and len(page["items"]) == 2
    assert await _types(api, "alice", "?unreadOnly=true") == []
    assert (await _list(api, "bob"))["unreadCount"] == 2


async def test_another_users_or_unknown_notification_is_not_found(api: Api) -> None:  # EC-02
    await api.sample(DS12)
    [item] = (await _list(api, "alice"))["items"]
    for who, notification_id in (("bob", item["id"]), ("manager", item["id"]), ("alice", str(uuid.uuid4()))):
        response = await api.request(who, "POST", f"{PATH}/{notification_id}/read")
        assert response.status_code == 404 and response.json()["title"] == "Not Found"
    assert (await _list(api, "alice"))["unreadCount"] == 1  # nothing changed


async def test_notifications_of_another_tenant_are_invisible(api: Api) -> None:
    await api.sample(DS12)
    other = await uploaded(api.engine, FIXTURES / DS12)  # a new tenant with its own members
    await process(api.engine, other)
    async with session_factory(api.engine)() as session:
        foreign = await session.scalar(select(Notification.id).where(Notification.invoice_id == other))
    assert foreign is not None
    assert (await _list(api, "alice"))["unreadCount"] == 1
    assert (await api.request("alice", "POST", f"{PATH}/{foreign}/read")).status_code == 404
    await api.request("alice", "POST", f"{PATH}/read-all")
    async with session_factory(api.engine)() as session:
        still_unread = await session.scalar(select(Notification.read_at).where(Notification.id == foreign))
    assert still_unread is None


async def test_paging_follows_the_newest_first_order(api: Api) -> None:
    invoice_id = await api.sample(DS12)
    ids = await _add_notifications(api, invoice_id, "alice", 5)  # older than the real one
    first = await _list(api, "alice", "?pageSize=2")
    assert first["unreadCount"] == 6 and first["nextPageToken"] is not None
    seen = [i["id"] for i in first["items"]]
    token = first["nextPageToken"]
    while token is not None:
        page = await _list(api, "alice", f"?pageSize=2&pageToken={token}")
        seen += [i["id"] for i in page["items"]]
        token = page["nextPageToken"]
    assert len(seen) == 6 and len(set(seen)) == 6
    assert seen[1:] == [str(i) for i in reversed(ids)]  # after the real notification: newest first
    assert (await _list(api, "alice", "?pageSize=6"))["nextPageToken"] is None


async def test_bad_page_parameters_are_a_bad_request(api: Api) -> None:
    for query in ("?pageToken=nope", "?pageSize=0", "?pageSize=101", "?unreadOnly=maybe"):
        response = await api.request("alice", "GET", f"{PATH}{query}")
        assert response.status_code == 400, query


async def test_the_manager_can_use_the_inbox_too(api: Api) -> None:
    waiting = await api.sample(DS03)
    [item] = (await _list(api, "manager"))["items"]
    assert item["invoiceId"] == str(waiting)
    assert (await api.request("manager", "POST", f"{PATH}/{item['id']}/read")).status_code == 204
    assert (await _list(api, "manager"))["unreadCount"] == 0
    assert (await _list(api, "manager2"))["unreadCount"] == 1


# TS-04 / BR-03 -----------------------------------------------------------------------------------------


async def test_inactive_users_and_users_created_later_receive_nothing(api: Api) -> None:
    async with session_factory(api.engine)() as session, session.begin():
        await session.execute(
            update(UserAccount).where(UserAccount.id == api.users["bob"].user_id).values(is_active=False)
        )
    await api.sample(DS12)
    assert (await _list(api, "alice"))["unreadCount"] == 1
    assert (await _list(api, "bob"))["unreadCount"] == 0  # inactive when the exception was raised

    async with session_factory(api.engine)() as session, session.begin():
        newcomer = UserAccount(
            tenant_id=api.world.tenant[0], username=f"n-{uuid.uuid4().hex[:8]}", display_name="Newcomer",
            role=Role.ACCOUNTING_MEMBER,
        )  # fmt: skip
        session.add(newcomer)
        await session.flush()
        api.users["newcomer"] = CurrentUser(
            newcomer.id, newcomer.tenant_id, newcomer.username, newcomer.display_name, newcomer.role
        )
    assert await _list(api, "newcomer") == {"items": [], "nextPageToken": None, "unreadCount": 0}
    await api.sample(DS01)
    assert await _types(api, "newcomer") == ["REVIEW_REQUESTED"]  # only what happens after joining


# TS-03 / BR-02, EC-05 ----------------------------------------------------------------------------------


async def test_notifications_roll_back_with_the_status_change(api: Api) -> None:
    invoice_id = await uploaded(api.engine, FIXTURES / DS12, api.world.tenant)
    recipients = [api.users["alice"].user_id, api.users["bob"].user_id]
    with pytest.raises(RuntimeError, match="status change failed"):
        async with session_factory(api.engine)() as session, session.begin():
            await SqlNotifications(session).add_notifications(
                api.world.tenant[0], invoice_id, recipients, NotificationType.EXCEPTION_RAISED, "Lost."
            )
            raise RuntimeError("status change failed")
    async with session_factory(api.engine)() as session:
        count = await session.scalar(
            select(func.count()).select_from(Notification).where(Notification.invoice_id == invoice_id)
        )
    assert count == 0
