"""Integration: SAPS-38 EX1 after the last retry, on a real PostgreSQL (TS-04)."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from saps.adapters.persistence.db import session_factory
from saps.adapters.persistence.matching_repository import SqlMatchingRepository
from saps.adapters.persistence.models import InvoiceEvent
from saps.adapters.persistence.processing_repository import SqlProcessingRepository
from saps.application.matching import MatchingService
from saps.application.processing import FailedProcessingService, ProcessInvoiceService, describe_failure
from saps.domain.invoices import NotificationType
from saps.ports.extraction import StoredFile
from tests.integration.api_world import Api
from tests.integration.pipeline import ERP, process

pytestmark = pytest.mark.integration

DS01 = "ds-01/invoices/ds-01-trade-po.pdf"


def _clock() -> datetime:
    return datetime.now(UTC)


class FailingExtraction:
    """An extraction service that is down: every call raises (the dummy adapter cannot do that)."""

    async def extract(self, file: StoredFile) -> None:
        raise ConnectionError("Extraction service unavailable")


async def _fail_the_job(api: Api, invoice_id: uuid.UUID) -> None:
    with pytest.raises(ConnectionError):
        async with session_factory(api.engine)() as session, session.begin():
            matching = MatchingService(SqlMatchingRepository(session), ERP, _clock)
            service = ProcessInvoiceService(
                SqlProcessingRepository(session), FailingExtraction(), matching, _clock
            )
            await service.process(invoice_id)


async def _fail(api: Api, invoice_id: uuid.UUID, reason: str) -> bool:
    async with session_factory(api.engine)() as session, session.begin():
        return await FailedProcessingService(SqlProcessingRepository(session), _clock).fail(
            invoice_id, reason
        )


async def test_the_last_failed_retry_raises_ex1_and_tells_the_members(api: Api) -> None:
    invoice_id = await api.sample(DS01, processed=False)
    await _fail_the_job(api, invoice_id)
    assert (await api.get(invoice_id))["status"] == "UPLOADED"  # the failed job rolled back

    reason = describe_failure(
        "Traceback (most recent call last):\nConnectionError: Extraction service unavailable\n"
    )
    assert await _fail(api, invoice_id, reason) is True

    invoice = await api.get(invoice_id)
    assert invoice["status"] == "EXCEPTION"
    [exception] = invoice["exceptions"]
    assert (exception["code"], exception["status"]) == ("EX1", "OPEN")
    assert exception["message"] == f"Invoice unreadable: {reason}"
    async with session_factory(api.engine)() as session:
        events = (
            (
                await session.execute(
                    select(InvoiceEvent).where(
                        InvoiceEvent.invoice_id == invoice_id, InvoiceEvent.action == "EXTRACT"
                    )
                )
            )
            .scalars()
            .all()
        )
    assert [(e.status_to.value, e.details, e.actor) for e in events] == [
        ("EXCEPTION", {"found": False, "reason": reason}, "system")
    ]
    notified = await api.notifications(invoice_id)
    assert notified == {
        "Member": [NotificationType.EXCEPTION_RAISED],
        "Bob": [NotificationType.EXCEPTION_RAISED],
    }  # the Accounting Members; not the managers


async def test_running_the_failure_step_again_changes_nothing(api: Api) -> None:  # BR-03
    invoice_id = await api.sample(DS01, processed=False)
    assert await _fail(api, invoice_id, "first") is True
    assert await _fail(api, invoice_id, "second") is False
    invoice = await api.get(invoice_id)
    assert [e["code"] for e in invoice["exceptions"]] == ["EX1"]
    assert invoice["exceptions"][0]["message"] == "Invoice unreadable: first"
    assert sum(len(types) for types in (await api.notifications(invoice_id)).values()) == 2


async def test_an_invoice_that_moved_on_is_left_alone(api: Api) -> None:  # BR-03, EC-03
    invoice_id = await api.sample(DS01, processed=False)
    await process(api.engine, invoice_id)  # a late retry finished the job: Pending review
    assert await _fail(api, invoice_id, "too late") is False
    assert (await api.get(invoice_id))["status"] == "POSTING"


async def test_an_unknown_invoice_is_ignored(api: Api) -> None:
    assert await _fail(api, uuid.uuid4(), "nobody") is False
