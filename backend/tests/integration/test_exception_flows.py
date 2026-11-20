"""Integration: SAPS-20 demo flows, queue lists, events and file download through the API (TS-04, TS-11)."""

import uuid
from decimal import Decimal
from typing import Any

import pytest

from saps.domain.users import CurrentUser, Role
from tests.integration.api_world import Api

pytestmark = pytest.mark.integration

DS12 = "ds-12/invoices/ds-12-price-outside-tolerance.pdf"
DS08 = "ds-08/invoices/ds-08-non-po.pdf"
DS01 = "ds-01/invoices/ds-01-trade-po.pdf"


def line(
    number: int, description: str, po: str | None, po_line: int | None, qty: str, price: str, amount: str
) -> dict[str, Any]:
    return {
        "lineNumber": number,
        "description": description,
        "poNumber": po,
        "poLineNumber": po_line,
        "quantity": qty,
        "unitPrice": price,
        "lineAmount": amount,
    }


async def _fix_and_rematch(api: Api, sample: str, body: dict[str, Any]) -> tuple[uuid.UUID, dict[str, Any]]:
    """Claim, correct, let the worker re-match; returns the invoice after the re-match."""
    invoice_id = await api.sample(sample)
    assert (await api.claim("alice", invoice_id)).status_code == 200
    response = await api.update("alice", invoice_id, body)
    assert response.status_code == 202, response.text
    await api.rematch(invoice_id)
    return invoice_id, await api.get(invoice_id)


# Demo scenarios: the member corrects the data and matching runs again -----------------------------


async def test_ds09_correct_the_po_number(api: Api) -> None:
    body = {"lines": [line(1, "Printer paper, A3", "0100009", 1, "3", "30.00", "90.00")]}
    _, invoice = await _fix_and_rematch(api, "ds-09/invoices/ds-09-invalid-po-number.pdf", body)
    assert (invoice["status"], invoice["assignedTo"]) == ("PENDING_REVIEW", None)
    [ex3] = [e for e in invoice["exceptions"] if e["code"] == "EX3"]
    assert ex3["status"] == "RESOLVED" and ex3["resolvedBy"] is None  # resolved by the system (DEC-024)
    assert invoice["lines"][0]["matchStatus"] == "MATCHED"


async def test_ds13_correct_the_quantity(api: Api) -> None:
    body = {"lines": [line(1, "Monitor stand", "0100013", 1, "6", "18.00", "108.00")]}
    _, invoice = await _fix_and_rematch(api, "ds-13/invoices/ds-13-quantity-above-expected.pdf", body)
    assert invoice["status"] == "PENDING_REVIEW" and invoice["lines"][0]["expectedQuantity"] == "6.000"


async def test_ds07_enter_the_data_manually_after_ex1(api: Api) -> None:  # EC-06
    body = {
        "vendorCode": "V001",
        "vendorName": "Alpha Office Supplies Co.",
        "invoiceNumber": "MANUAL-0007",
        "invoiceDate": "2026-12-13",
        "totalAmount": "49.50",
        "lines": [line(1, "Desk organizer", "0100017", 1, "5", "9.00", "45.00")],
    }
    invoice_id = await api.sample("ds-07/unregistered/ds-07-unknown-invoice.pdf")
    before = await api.get(invoice_id)
    assert [e["code"] for e in before["exceptions"]] == ["EX1"] and before["lines"] == []
    await api.claim("alice", invoice_id)
    assert (await api.update("alice", invoice_id, body)).status_code == 202
    await api.rematch(invoice_id)
    invoice = await api.get(invoice_id)
    assert invoice["status"] == "PENDING_REVIEW" and invoice["invoiceNumber"] == "MANUAL-0007"
    assert invoice["exceptions"][0]["status"] == "RESOLVED"


async def test_ds11_remove_the_non_trade_line(api: Api) -> None:
    body = {"lines": [line(1, "Filing cabinet", "0100011", 1, "1", "120.00", "120.00")]}
    _, invoice = await _fix_and_rematch(api, "ds-11/invoices/ds-11-trade-and-non-trade.pdf", body)
    assert invoice["status"] == "PENDING_REVIEW" and len(invoice["lines"]) == 1
    assert invoice["invoiceType"] == "TRADE_PO"


async def test_removed_lines_release_their_exceptions(api: Api) -> None:
    invoice_id = await api.sample("ds-14/invoices/ds-14-missing-goods-receipt.pdf")  # EX8 on line 1
    await api.claim("alice", invoice_id)
    body = {"lines": [line(2, "Network cable, 5 m", "0100014", 1, "12", "3.50", "42.00")]}
    assert (await api.update("alice", invoice_id, body)).status_code == 202
    invoice = await api.get(invoice_id)
    assert [ln["lineNumber"] for ln in invoice["lines"]] == [2]
    [ex8] = invoice["exceptions"]
    assert (ex8["status"], ex8["invoiceLineId"], ex8["resolvedBy"]["displayName"]) == (
        "RESOLVED",
        None,
        "Member",
    )
    await api.rematch(invoice_id)  # the new line has no goods receipt either
    again = await api.get(invoice_id)
    [open_ex8] = [e for e in again["exceptions"] if e["status"] == "OPEN"]
    assert open_ex8["code"] == "EX8" and open_ex8["invoiceLineId"] == again["lines"][0]["id"]


async def test_failed_rematch_message_still_answers_202(
    api: Api,
) -> None:  # EC-05: the sweeper (SAPS-37) recovers it
    invoice_id = await api.sample(DS12)
    await api.claim("alice", invoice_id)
    api.queue.fail = True
    response = await api.update(
        "alice", invoice_id, {"lines": [line(1, "USB keyboard", "0100012", 1, "4", "20.00", "80.00")]}
    )
    assert response.status_code == 202 and response.json()["status"] == "MATCHING"
    assert api.queue.rematch == []


# Queue and lists ----------------------------------------------------------------------------------


async def test_the_exception_queue(api: Api) -> None:
    ds12, ds08, ds01 = await api.sample(DS12), await api.sample(DS08), await api.sample(DS01)

    async def ids(who: str, query: str) -> list[str]:
        response = await api.request(who, "GET", f"/v1/invoices?{query}")
        assert response.status_code == 200, response.text
        return [item["id"] for item in response.json()["items"]]

    assert await ids("alice", "status=EXCEPTION&assignee=unassigned") == [
        str(ds08),
        str(ds12),
    ]  # newest first
    assert await ids("manager", "status=EXCEPTION") == [str(ds08), str(ds12)]
    assert await ids("alice", "status=EXCEPTION&status=PENDING_REVIEW") == [str(ds01), str(ds08), str(ds12)]
    assert await ids("alice", "invoiceType=NON_PO") == [str(ds08)]
    await api.claim("alice", ds12)
    assert await ids("alice", "status=EXCEPTION&assignee=unassigned") == [str(ds08)]
    assert await ids("alice", "status=EXCEPTION&assignee=me") == [str(ds12)]
    assert await ids("bob", "status=EXCEPTION&assignee=me") == []
    row = (await api.request("alice", "GET", "/v1/invoices?assignee=me")).json()["items"][0]
    assert row["openExceptionCodes"] == ["EX6"] and row["assignedTo"]["displayName"] == "Member"
    assert row["vendorName"] == "Alpha Office Supplies Co." and row["totalAmount"] == "90.64"


async def test_paging_and_tenant_scope(api: Api) -> None:
    created = [await api.sample(DS12), await api.sample(DS08), await api.sample(DS01)]
    seen: list[str] = []
    token: str | None = None
    while True:
        query = "pageSize=1" + (f"&pageToken={token}" if token else "")
        page = (await api.request("alice", "GET", f"/v1/invoices?{query}")).json()
        assert len(page["items"]) == 1
        seen.append(page["items"][0]["id"])
        token = page["nextPageToken"]
        if token is None:
            break
    assert seen == [str(i) for i in reversed(created)]
    assert (await api.request("alice", "GET", "/v1/invoices?pageToken=not-a-token")).status_code == 400
    assert (await api.request("alice", "GET", "/v1/invoices?pageSize=0")).status_code == 400
    api.users["stranger"] = CurrentUser(
        uuid.uuid4(), uuid.uuid4(), "x", "X", Role.ACCOUNTING_MEMBER
    )  # ADR-0007
    assert (await api.request("stranger", "GET", "/v1/invoices")).json() == {
        "items": [],
        "nextPageToken": None,
    }
    assert (await api.request("stranger", "GET", f"/v1/invoices/{created[0]}/events")).status_code == 404


# Events (TS-11) ------------------------------------------------------------------------------------


async def test_every_action_is_recorded(api: Api) -> None:
    invoice_id = await api.sample(DS12)
    await api.claim("alice", invoice_id)
    await api.release("manager", invoice_id)
    await api.claim("bob", invoice_id)
    fix = {"lines": [line(1, "USB keyboard", "0100012", 1, "4", "20.00", "80.00")]}
    assert (
        await api.update("bob", invoice_id, {"invoiceNumber": "AOS-2026-1013-A", **fix})
    ).status_code == 202
    await api.rematch(invoice_id)

    response = await api.request("alice", "GET", f"/v1/invoices/{invoice_id}/events")
    events = response.json()["items"]
    assert [(e["action"], e["actor"]) for e in events] == [
        ("EXTRACT", "system"),
        ("MATCH", "system"),
        ("CLAIM", "Member"),
        ("RELEASE", "Manager"),
        ("CLAIM", "Bob"),
        ("UPDATE_FIELDS", "Bob"),
        ("MATCH", "system"),
    ]
    update = events[5]
    assert (update["statusFrom"], update["statusTo"]) == ("EXCEPTION", "MATCHING")
    assert update["details"]["rematch"] is True
    assert update["details"]["fields"] == {
        "invoiceNumber": {"old": "AOS-2026-1013", "new": "AOS-2026-1013-A"}
    }
    old_line, new_line = update["details"]["lines"]["old"][0], update["details"]["lines"]["new"][0]
    assert Decimal(old_line["unitPrice"]) == Decimal("20.60") and Decimal(new_line["unitPrice"]) == Decimal(
        "20.00"
    )
    assert events[-1]["statusTo"] == "PENDING_REVIEW"

    second = await api.request("alice", "GET", f"/v1/invoices/{invoice_id}/events?pageSize=3")
    first_page = second.json()
    assert len(first_page["items"]) == 3 and first_page["nextPageToken"]
    rest = (
        await api.request(
            "alice",
            "GET",
            f"/v1/invoices/{invoice_id}/events?pageSize=10&pageToken={first_page['nextPageToken']}",
        )
    ).json()
    assert [e["id"] for e in first_page["items"] + rest["items"]] == [e["id"] for e in events]
    assert rest["nextPageToken"] is None
    assert (
        await api.request("alice", "GET", f"/v1/invoices/{invoice_id}/events?pageToken=x")
    ).status_code == 400
    assert (await api.request("alice", "GET", f"/v1/invoices/{uuid.uuid4()}/events")).status_code == 404


async def test_resolve_and_reject_are_recorded(api: Api) -> None:
    resolved, rejected = await api.sample(DS12), await api.sample("ds-10/invoices/ds-10-po-not-found.pdf")
    for invoice_id in (resolved, rejected):
        await api.claim("alice", invoice_id)
    await api.resolve("alice", resolved)
    await api.reject("alice", rejected, "PO does not exist.")

    last = (await api.request("alice", "GET", f"/v1/invoices/{resolved}/events")).json()["items"][-1]
    assert (last["action"], last["statusFrom"], last["statusTo"], last["actor"]) == (
        "RESOLVE",
        "EXCEPTION",
        "PENDING_REVIEW",
        "Member",
    )
    assert last["details"] == {"codes": ["EX6"], "threshold": "300.00"}
    last = (await api.request("alice", "GET", f"/v1/invoices/{rejected}/events")).json()["items"][-1]
    assert (last["action"], last["statusTo"], last["details"]) == (
        "REJECT",
        "REJECTED",
        {"reason": "PO does not exist."},
    )


# File ---------------------------------------------------------------------------------------------


async def test_download_the_file(api: Api) -> None:
    invoice_id = await api.sample(DS12)
    content = b"%PDF-1.7 a file that is longer than one chunk of the fake storage"
    api.storage.objects[await api.storage_key(invoice_id)] = (content, "application/pdf")
    for who in ("alice", "manager"):
        response = await api.request(who, "GET", f"/v1/invoices/{invoice_id}/file")
        assert response.status_code == 200 and response.content == content
        assert response.headers["content-type"] == "application/pdf"
        assert (
            response.headers["content-disposition"]
            == "inline; filename*=UTF-8''ds-12-price-outside-tolerance.pdf"
        )


async def test_missing_file_or_invoice(api: Api) -> None:
    invoice_id = await api.sample(DS12)  # nothing stored under its key
    missing = await api.request("alice", "GET", f"/v1/invoices/{invoice_id}/file")
    assert missing.status_code == 404 and missing.json()["detail"] == "The invoice file is not available."
    assert (await api.request("alice", "GET", f"/v1/invoices/{uuid.uuid4()}/file")).status_code == 404
