"""Integration: invoice list and search on a real PostgreSQL (SAPS-46 TS-02 to TS-05)."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncEngine

from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.models import InboundMail, Invoice, InvoiceLine, Tenant
from saps.domain.duplicates import normalize_invoice_number
from saps.domain.invoices import InvoiceStatus, MatchStatus
from saps.domain.mail_intake import InboundMailStatus, IntakeChannel
from tests.integration.api_world import Api
from tests.integration.pipeline import new_world

pytestmark = pytest.mark.integration


async def _invoice(
    engine: AsyncEngine,
    api: Api,
    name: str,
    *,
    created: datetime,
    mail: uuid.UUID | None = None,
    **fields: Any,
) -> uuid.UUID:
    tenant_id, member_id = api.world.tenant
    pos: list[str] = fields.pop("pos", [])
    number = fields.get("invoice_number")
    invoice = Invoice(
        tenant_id=tenant_id,
        uploaded_by=None if mail else member_id,
        channel=IntakeChannel.MAIL if mail else IntakeChannel.UPLOAD,
        inbound_mail_id=mail,
        file_name=name,
        file_content_type="application/pdf",
        file_size_bytes=10,
        file_sha256="a" * 64,
        file_storage_key=f"k/{name}",
        idempotency_key=uuid.uuid4().hex,
        created_at=created,
        invoice_number_normalized=normalize_invoice_number(number),
        **fields,
    )
    async with session_factory(engine)() as session, session.begin():
        session.add(invoice)
        await session.flush()
        for index, po in enumerate(pos, start=1):
            session.add(
                InvoiceLine(
                    tenant_id=tenant_id,
                    invoice_id=invoice.id,
                    line_number=index,
                    po_number=po,
                    po_line_number=1,
                    match_status=MatchStatus.MATCHED,
                )
            )
    return invoice.id


class Data:
    """Three invoices of one company, as in the spec scenarios."""

    a: uuid.UUID
    b: uuid.UUID
    c: uuid.UUID


async def _data(engine: AsyncEngine, api: Api, *, zone: str = "UTC") -> Data:
    tenant_id = api.world.tenant[0]
    async with session_factory(engine)() as session, session.begin():
        await session.execute(update(Tenant).where(Tenant.id == tenant_id).values(time_zone=zone))
        mail = InboundMail(
            tenant_id=tenant_id,
            mailbox_address="ap@search.example.com",
            mail_key=f"<{uuid.uuid4().hex}@v>",
            sender="v@example.net",
            subject="s",
            received_at=datetime(2027, 3, 1, tzinfo=UTC),
            status=InboundMailStatus.PROCESSED,
        )
        session.add(mail)
        await session.flush()
        mail_id = mail.id
    data = Data()
    data.a = await _invoice(
        engine, api, "a.pdf", created=datetime(2027, 3, 1, 2, 0, tzinfo=UTC), status=InvoiceStatus.COMPLETED,
        vendor_name="Alpha Office Supplies Co.", vendor_code="V001", invoice_number="AOS-2026-1013",
        invoice_date=date(2027, 1, 10), total_amount=Decimal("90.64"), pos=["0100012", "0100099"],
    )  # fmt: skip
    data.b = await _invoice(
        engine, api, "b.pdf", created=datetime(2027, 3, 1, 17, 30, tzinfo=UTC),
        status=InvoiceStatus.EXCEPTION, vendor_name="Beta Tools 100%_off", vendor_code="V002",
        invoice_number="BT 77", invoice_date=date(2027, 2, 1), total_amount=Decimal("300.00"),
        pos=["1000001"], mail=mail_id,
    )  # fmt: skip
    data.c = await _invoice(
        engine, api, "c.pdf", created=datetime(2027, 2, 28, 16, 30, tzinfo=UTC), status=InvoiceStatus.UPLOADED
    )
    return data


async def _search(api: Api, query: str, who: str = "alice") -> list[str]:
    response = await api.request(who, "GET", f"/v1/invoices?{query}")
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def _ids(*ids: uuid.UUID) -> list[str]:
    return [str(i) for i in ids]


# TS-02 / BR-02, BR-03, EC-01, EC-05, EC-06, EC-10 ---------------------------------------------------------


async def test_no_filter_lists_every_status_newest_upload_first(api: Api, engine: AsyncEngine) -> None:
    data = await _data(engine, api)
    assert await _search(api, "") == _ids(data.b, data.a, data.c)
    assert await _search(api, "", who="manager") == _ids(data.b, data.a, data.c)  # both roles


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("vendor=alpha", "a"),
        ("vendor=ALPHA%20OFFICE", "a"),
        ("vendor=v002", "b"),  # the vendor code
        ("vendor=100%25_", "b"),  # `%` and `_` are plain text (EC-10)
        ("vendor=%25", "b"),
        ("vendor=_", "b"),
        ("vendor=nobody", ""),
        ("invoiceNumber=aos%202026-1013", "a"),
        ("invoiceNumber=AOS/2026.1013", "a"),  # EC-06
        ("invoiceNumber=2026", "a"),
        ("invoiceNumber=bt77", "b"),
        ("invoiceNumber=%25", ""),
        ("poNumber=0100099", "a"),  # the second line
        ("poNumber=0100012", "a"),
        ("poNumber=1000001", "b"),
        ("poNumber=0100013", ""),
        ("invoiceDateFrom=2027-01-10&invoiceDateTo=2027-01-10", "a"),  # both ends included
        ("invoiceDateFrom=2027-01-11", "b"),
        ("invoiceDateTo=2027-01-31", "a"),
        ("totalMin=100", "b"),
        ("totalMax=100", "a"),
        ("totalMin=90.64&totalMax=90.64", "a"),
        ("channel=MAIL", "b"),
        ("channel=UPLOAD", "ac"),
        ("status=COMPLETED", "a"),
        ("status=COMPLETED&status=EXCEPTION", "ba"),
        ("vendor=beta&channel=UPLOAD", ""),  # combined with AND
        ("vendor=alpha&totalMax=100&status=COMPLETED&channel=UPLOAD&poNumber=0100099", "a"),
    ],
)
async def test_each_filter_alone_and_combined(
    api: Api, engine: AsyncEngine, query: str, expected: str
) -> None:
    data = await _data(engine, api)
    ids = {"a": data.a, "b": data.b, "c": data.c}
    assert await _search(api, query) == _ids(*(ids[k] for k in expected))


async def test_an_invoice_without_data_matches_no_data_filter(api: Api, engine: AsyncEngine) -> None:  # EC-05
    data = await _data(engine, api)
    for query in ("vendor=a", "invoiceNumber=0", "invoiceDateFrom=2000-01-01", "totalMin=0", "totalMax=9999"):
        assert str(data.c) not in await _search(api, query)
    assert str(data.c) in await _search(api, "")  # listed when no data filter applies


async def test_the_summary_has_the_search_columns(api: Api, engine: AsyncEngine) -> None:
    data = await _data(engine, api)
    items = (await api.request("alice", "GET", "/v1/invoices?invoiceNumber=aos")).json()["items"]
    assert items[0]["id"] == str(data.a)
    assert (items[0]["invoiceDate"], items[0]["channel"], items[0]["uploadedAt"]) == (
        "2027-01-10",
        "UPLOAD",
        "2027-03-01T02:00:00Z",
    )
    mail = (await api.request("alice", "GET", "/v1/invoices?channel=MAIL")).json()["items"][0]
    assert mail["channel"] == "MAIL" and mail["invoiceDate"] == "2027-02-01"


# TS-03 / BR-04, EC-07 -------------------------------------------------------------------------------------


async def test_the_upload_date_is_a_day_of_the_company_time_zone(api: Api, engine: AsyncEngine) -> None:
    data = await _data(engine, api, zone="Asia/Singapore")
    # Singapore: c = 1 March 00:30, a = 1 March 10:00, b = 2 March 01:30
    assert await _search(api, "uploadedFrom=2027-03-01&uploadedTo=2027-03-01") == _ids(data.a, data.c)
    assert await _search(api, "uploadedFrom=2027-03-02") == _ids(data.b)
    assert await _search(api, "uploadedTo=2027-02-28") == []

    async with session_factory(engine)() as session, session.begin():
        await session.execute(update(Tenant).where(Tenant.id == api.world.tenant[0]).values(time_zone="UTC"))
    # UTC: c = 28 February, a and b = 1 March
    assert await _search(api, "uploadedFrom=2027-03-01&uploadedTo=2027-03-01") == _ids(data.b, data.a)
    assert await _search(api, "uploadedTo=2027-02-28") == _ids(data.c)


# TS-04 / BR-05, EC-09 -------------------------------------------------------------------------------------


async def test_pages_continue_with_the_same_filters(api: Api, engine: AsyncEngine) -> None:
    data = await _data(engine, api)
    first = (await api.request("alice", "GET", "/v1/invoices?pageSize=2")).json()
    assert [i["id"] for i in first["items"]] == _ids(data.b, data.a) and first["nextPageToken"]
    second = (
        await api.request("alice", "GET", f"/v1/invoices?pageSize=2&pageToken={first['nextPageToken']}")
    ).json()
    assert [i["id"] for i in second["items"]] == _ids(data.c) and second["nextPageToken"] is None

    filtered = (await api.request("alice", "GET", "/v1/invoices?pageSize=1&channel=UPLOAD")).json()
    assert [i["id"] for i in filtered["items"]] == _ids(data.a)
    rest = await api.request(
        "alice", "GET", f"/v1/invoices?pageSize=1&channel=UPLOAD&pageToken={filtered['nextPageToken']}"
    )
    assert [i["id"] for i in rest.json()["items"]] == _ids(data.c)


# BR-07, EC-02, EC-03, EC-04 -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("invoiceDateFrom=2027-02-02&invoiceDateTo=2027-02-01", "invoiceDateFrom"),
        ("uploadedFrom=2027-03-02&uploadedTo=2027-03-01", "uploadedFrom"),
        ("totalMin=10&totalMax=9", "totalMin"),
        ("totalMin=-1", "totalMin"),
        ("totalMax=-0.01", "totalMax"),
    ],
)
async def test_invalid_filters_are_refused_with_the_field(api: Api, query: str, field: str) -> None:
    response = await api.request("alice", "GET", f"/v1/invoices?{query}")
    assert response.status_code == 400
    assert response.json()["errors"][0]["field"] == field


@pytest.mark.parametrize(
    "query",
    [
        "poNumber=12",
        "poNumber=ABCDEFG",
        "channel=FAX",
        "status=GONE",
        "invoiceDateFrom=yesterday",
        "totalMin=abc",
        "vendor=",
    ],
)
async def test_malformed_values_are_refused(api: Api, query: str) -> None:
    assert (await api.request("alice", "GET", f"/v1/invoices?{query}")).status_code == 400


async def test_nothing_matching_is_an_empty_page(api: Api, engine: AsyncEngine) -> None:  # EC-02
    await _data(engine, api)
    page = (await api.request("alice", "GET", "/v1/invoices?vendor=nobody")).json()
    assert page == {"items": [], "nextPageToken": None}


# TS-05 / BR-01 --------------------------------------------------------------------------------------------


async def test_a_search_never_returns_another_companys_invoices(api: Api, engine: AsyncEngine) -> None:
    data = await _data(engine, api)
    other = await new_world(engine)
    api.users["outsider"] = other.alice
    for query in ("", "vendor=alpha", "invoiceNumber=aos", "poNumber=0100012", "channel=MAIL", "totalMin=0"):
        assert await _search(api, query, who="outsider") == []
    assert await _search(api, "vendor=alpha") == _ids(data.a)
    assert (await api.request("outsider", "GET", f"/v1/invoices/{data.a}")).status_code == 404  # SAPS-41
