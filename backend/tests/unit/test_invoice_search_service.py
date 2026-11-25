"""Search use case with a fake reader (SAPS-46 TS-01)."""

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from saps.application.invoices import search_invoices
from saps.domain.invoice_search import InvalidSearchError, SearchCriteria
from saps.domain.mail_intake import IntakeChannel
from saps.domain.users import CurrentUser, Role
from saps.ports.invoices import InvoiceFilter, Page

USER = CurrentUser(uuid4(), uuid4(), "member1@sg.example.com", "M1", Role.ACCOUNTING_MEMBER)


class FakeReader:
    def __init__(self, zone: str = "Asia/Singapore") -> None:
        self.zone = zone
        self.zone_reads: list[UUID] = []
        self.listed: list[tuple[UUID, InvoiceFilter, int, str | None]] = []

    async def company_time_zone(self, tenant_id: UUID) -> str:
        self.zone_reads.append(tenant_id)
        return self.zone

    async def list_invoices(
        self, tenant_id: UUID, flt: InvoiceFilter, page_size: int, page_token: str | None
    ) -> Page[object]:
        self.listed.append((tenant_id, flt, page_size, page_token))
        return Page([object()], None)


async def test_the_filters_reach_the_reader_for_the_users_company() -> None:
    reader = FakeReader()
    base = InvoiceFilter(assignee="me", user_id=USER.user_id)
    criteria = SearchCriteria(
        vendor="  alpha  ",
        invoice_number="AOS 2026-1013",
        po_number="0100012",
        invoice_date_from=date(2027, 1, 1),
        invoice_date_to=date(2027, 1, 31),
        uploaded_from=date(2027, 3, 1),
        uploaded_to=date(2027, 3, 2),
        total_min=Decimal("10"),
        total_max=Decimal("500.50"),
        channel=IntakeChannel.MAIL,
    )
    page = await search_invoices(reader, USER, criteria, base, 20, "token")  # type: ignore[arg-type]
    assert len(page.items) == 1
    tenant, flt, size, token = reader.listed[0]
    assert (tenant, size, token) == (USER.tenant_id, 20, "token")
    assert (flt.assignee, flt.user_id) == ("me", USER.user_id)  # the queue filters are kept
    assert (flt.vendor, flt.invoice_number, flt.po_number) == ("alpha", "aos20261013", "0100012")
    assert (flt.invoice_date_from, flt.invoice_date_to) == (date(2027, 1, 1), date(2027, 1, 31))
    assert flt.uploaded_from == datetime(2027, 2, 28, 16, tzinfo=UTC)  # Singapore midnight
    assert flt.uploaded_to == datetime(2027, 3, 2, 16, tzinfo=UTC)  # end of the 2nd local day, excluded
    assert (flt.total_min, flt.total_max, flt.channel) == (
        Decimal("10"),
        Decimal("500.50"),
        IntakeChannel.MAIL,
    )
    assert reader.zone_reads == [USER.tenant_id]


async def test_without_an_upload_date_the_time_zone_is_not_read() -> None:
    reader = FakeReader()
    await search_invoices(reader, USER, SearchCriteria(vendor="  "), InvoiceFilter(), 20, None)  # type: ignore[arg-type]
    assert reader.zone_reads == [] and reader.listed[0][1].vendor is None  # blank text is no filter


async def test_an_invalid_filter_searches_nothing() -> None:  # BR-07
    reader = FakeReader()
    with pytest.raises(InvalidSearchError):
        await search_invoices(  # type: ignore[arg-type]
            reader, USER, SearchCriteria(total_min=Decimal("-1")), InvoiceFilter(), 20, None
        )
    assert reader.listed == []


async def test_the_search_is_logged_with_filter_names_only(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO):
        await search_invoices(  # type: ignore[arg-type]
            FakeReader(), USER, SearchCriteria(vendor="secret vendor"), InvoiceFilter(), 20, None
        )
    record = next(r for r in caplog.records if r.message == "invoices_searched")
    assert record.filters == ["vendor"] and record.items == 1  # type: ignore[attr-defined]
    assert "secret vendor" not in caplog.text
