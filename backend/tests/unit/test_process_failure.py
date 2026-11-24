"""SAPS-38: EX1 after the last retry of `process_invoice` (TS-01 … TS-03, TS-06, TS-07)."""

import logging
import traceback
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import dramatiq
import pytest
from dramatiq import Worker
from dramatiq.brokers.stub import StubBroker
from dramatiq.middleware import TimeLimitExceeded
from pydantic import ValidationError

from saps.application.processing import FAILURE_PREFIX, FailedProcessingService, describe_failure
from saps.config import Settings
from saps.domain.invoices import InvoiceStatus, NotificationType
from saps.domain.users import Role
from saps.ports.extraction import StoredFile
from saps.ports.processing import InvoiceToProcess
from saps.worker import jobs
from tests.fakes import NOW


def _traceback_of(error: BaseException) -> str:
    try:
        raise error
    except BaseException:
        return traceback.format_exc()


# TS-02 / BR-02 ---------------------------------------------------------------------------------------


def test_the_reason_is_the_error_class_and_its_message() -> None:
    text = _traceback_of(ConnectionError("SAPS Message Broker unavailable"))
    assert describe_failure(text) == f"{FAILURE_PREFIX}: ConnectionError: SAPS Message Broker unavailable"


def test_the_module_path_of_the_class_is_dropped_and_an_empty_message_is_left_out() -> None:
    assert describe_failure(_traceback_of(TimeLimitExceeded())) == f"{FAILURE_PREFIX}: TimeLimitExceeded"


def test_the_message_is_cut_at_200_characters() -> None:
    reason = describe_failure(_traceback_of(RuntimeError("x" * 500)))
    assert reason == f"{FAILURE_PREFIX}: RuntimeError: {'x' * 200}"


def test_no_frame_of_the_traceback_is_part_of_the_reason() -> None:
    reason = describe_failure(_traceback_of(ValueError("bad")))
    assert "File" not in reason and "Traceback" not in reason and "\n" not in reason


def test_a_chained_error_names_the_last_one() -> None:
    try:
        try:
            raise KeyError("first")
        except KeyError as exc:
            raise RuntimeError("second") from exc
    except RuntimeError:
        text = traceback.format_exc()
    assert describe_failure(text) == f"{FAILURE_PREFIX}: RuntimeError: second"


@pytest.mark.parametrize("text", ["", "   \n  File x, line 1\n", "Traceback (most recent call last):\n"])
def test_an_unreadable_traceback_gives_an_unknown_error(text: str) -> None:
    assert describe_failure(text) == f"{FAILURE_PREFIX}: unknown error"


# TS-01 / BR-01, BR-03 ---------------------------------------------------------------------------------


def _invoice(status: InvoiceStatus = InvoiceStatus.UPLOADED) -> InvoiceToProcess:
    return InvoiceToProcess(
        uuid4(), uuid4(), status, StoredFile("a" * 64, "k", "application/pdf"), "scan.pdf", None
    )


class FakeRepo:
    def __init__(self, invoice: InvoiceToProcess | None) -> None:
        self.invoice = invoice
        self.unreadable: list[str] = []
        self.notified: list[tuple[list[UUID], NotificationType, str]] = []

    async def lock_invoice(self, invoice_id: UUID) -> InvoiceToProcess | None:
        return self.invoice

    async def raise_unreadable(
        self, invoice: InvoiceToProcess, reason: str, *, actor: str, now: datetime
    ) -> None:
        assert (actor, now) == ("system", NOW)
        self.unreadable.append(reason)

    async def active_user_ids(self, tenant_id: UUID, role: Role) -> list[UUID]:
        assert role is Role.ACCOUNTING_MEMBER
        return MEMBERS

    async def add_notifications(
        self, tenant_id: UUID, invoice_id: UUID, recipients: Any, kind: NotificationType, message: str
    ) -> None:
        self.notified.append((list(recipients), kind, message))


MEMBERS = [uuid4(), uuid4()]


async def test_an_invoice_in_uploaded_gets_ex1_and_the_members_are_told() -> None:
    repo = FakeRepo(_invoice())
    assert await FailedProcessingService(repo, lambda: NOW).fail(uuid4(), "Processing failed: X") is True  # type: ignore[arg-type]
    assert repo.unreadable == ["Processing failed: X"]
    assert repo.notified == [
        (MEMBERS, NotificationType.EXCEPTION_RAISED, "Invoice file scan.pdf has exceptions: EX1.")
    ]


@pytest.mark.parametrize(
    "invoice", [None, *[_invoice(s) for s in InvoiceStatus if s is not InvoiceStatus.UPLOADED]]
)
async def test_any_other_status_or_a_missing_invoice_changes_nothing(
    invoice: InvoiceToProcess | None,
) -> None:
    repo = FakeRepo(invoice)
    assert await FailedProcessingService(repo, lambda: NOW).fail(uuid4(), "x") is False  # type: ignore[arg-type]
    assert repo.unreadable == [] and repo.notified == []


# TS-03 / BR-01, BR-04: the real Retries middleware on a stub broker -------------------------------------


def _run(error: BaseException, fail_times: int) -> tuple[int, list[tuple[dict[str, Any], dict[str, Any]]]]:
    broker = StubBroker()
    attempts: list[int] = []
    exhausted: list[tuple[dict[str, Any], dict[str, Any]]] = []

    @dramatiq.actor(
        broker=broker,
        actor_name="job",
        max_retries=2,
        min_backoff=1,
        max_backoff=1,
        on_retry_exhausted="job_failed",
    )
    def job(invoice_id: str) -> None:
        attempts.append(1)
        if len(attempts) <= fail_times:
            raise error

    @dramatiq.actor(broker=broker, actor_name="job_failed", max_retries=0)
    def job_failed(message_data: dict[str, Any], retry_data: dict[str, Any]) -> None:
        exhausted.append((message_data, retry_data))

    worker = Worker(broker, worker_timeout=100)
    worker.start()
    try:
        job.send("invoice-1")
        broker.join(job.queue_name, fail_fast=False)
        worker.join()
    finally:
        worker.stop()
    return len(attempts), exhausted


def test_the_callback_runs_once_after_the_last_retry() -> None:
    attempts, exhausted = _run(ConnectionError("Redis down"), fail_times=99)
    assert attempts == 3  # the first attempt and two retries
    [(message, retry)] = exhausted
    assert retry == {"retries": 2, "max_retries": 2}
    assert message["args"] == ["invoice-1"]
    assert describe_failure(message["options"]["traceback"]) == (
        f"{FAILURE_PREFIX}: ConnectionError: Redis down"
    )


def test_a_retry_that_succeeds_never_calls_the_callback() -> None:
    attempts, exhausted = _run(ConnectionError("blip"), fail_times=1)
    assert attempts == 2 and exhausted == []


def test_the_time_limit_counts_as_a_failure() -> None:  # EC-02
    attempts, exhausted = _run(TimeLimitExceeded(), fail_times=99)
    assert attempts == 3 and len(exhausted) == 1
    assert describe_failure(exhausted[0][0]["options"]["traceback"]) == f"{FAILURE_PREFIX}: TimeLimitExceeded"


# The actors of the SAPS Worker ---------------------------------------------------------------------------


def test_process_invoice_takes_its_retry_options_from_the_settings() -> None:  # BR-04
    from saps.worker import actors

    options = actors.process_invoice.options
    assert options["max_retries"] == actors.settings.process_invoice_max_retries
    assert options["min_backoff"] == actors.settings.process_invoice_min_backoff_ms
    assert options["max_backoff"] == actors.settings.process_invoice_max_backoff_ms
    assert options["on_retry_exhausted"] == actors.process_invoice_failed.actor_name
    assert actors.process_invoice_failed.options["max_retries"] == 0  # the callback is not retried (EC-04)


async def test_the_callback_actor_records_the_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from saps.worker import actors

    calls: list[tuple[UUID, str]] = []
    tenants: list[UUID | None] = []

    async def record(invoice_id: UUID, reason: str, tenant_id: UUID | None) -> bool:
        calls.append((invoice_id, reason))
        tenants.append(tenant_id)
        return True

    monkeypatch.setattr(actors, "run_failure", record)
    invoice_id = uuid4()
    message = {"args": [str(invoice_id)], "options": {"traceback": _traceback_of(OSError("disk"))}}
    await actors.process_invoice_failed.fn.__wrapped__(message, {"retries": 5, "max_retries": 5})
    assert calls == [(invoice_id, f"{FAILURE_PREFIX}: OSError: disk")]
    await actors.process_invoice_failed.fn.__wrapped__({"args": [str(invoice_id)]}, {})  # no traceback at all
    assert calls[1] == (invoice_id, f"{FAILURE_PREFIX}: unknown error")
    tenant_id = uuid4()
    await actors.process_invoice_failed.fn.__wrapped__({"args": [str(invoice_id), str(tenant_id)]}, {})
    assert tenants == [None, None, tenant_id]  # SAPS-41: the company of the failed message


# TS-06 / EC-04: run_failure logs and never raises -------------------------------------------------------


class _Tx:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, *exc: object) -> bool:
        return False


class _Session:
    def begin(self) -> _Tx:
        return _Tx()


class _Sessions:
    async def __aenter__(self) -> _Session:
        return _Session()

    async def __aexit__(self, *exc: object) -> bool:
        return False


class _Service:
    outcome: bool | Exception = True

    def __init__(self, *args: object) -> None:
        pass

    async def fail(self, invoice_id: UUID, reason: str) -> bool:
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.fixture
def no_database(monkeypatch: pytest.MonkeyPatch) -> type[_Service]:
    monkeypatch.setattr(jobs, "get_engine", lambda url: None)
    monkeypatch.setattr(jobs, "session_factory", lambda engine, tenant_id=None: _Sessions)
    monkeypatch.setattr(jobs, "FailedProcessingService", _Service)
    return _Service


@pytest.mark.parametrize(
    ("outcome", "message"), [(True, "process_failure_recorded"), (False, "process_failure_skipped")]
)
async def test_run_failure_logs_what_happened(
    no_database: type[_Service], caplog: pytest.LogCaptureFixture, outcome: bool, message: str
) -> None:
    caplog.set_level(logging.INFO, logger="saps.worker.processing")
    no_database.outcome = outcome
    assert await jobs.run_failure(uuid4(), "reason", uuid4()) is outcome
    assert [r.getMessage() for r in caplog.records] == [message]


async def test_a_failing_run_failure_is_logged_and_does_not_raise(
    no_database: type[_Service], caplog: pytest.LogCaptureFixture
) -> None:  # EC-04
    no_database.outcome = ConnectionError("database down")
    assert await jobs.run_failure(uuid4(), "reason", uuid4()) is False
    [record] = caplog.records
    assert (record.levelno, record.getMessage()) == (logging.ERROR, "process_failure_not_recorded")


# TS-07 / BR-04, BR-05: settings ---------------------------------------------------------------------------


def test_the_new_settings_have_the_agreed_defaults() -> None:
    settings = Settings(_env_file=None)
    assert (
        settings.process_invoice_max_retries,
        settings.process_invoice_min_backoff_ms,
        settings.process_invoice_max_backoff_ms,
        settings.sweeper_max_resends,
    ) == (5, 15_000, 300_000, 3)


@pytest.mark.parametrize(
    "field",
    [
        "process_invoice_max_retries",
        "process_invoice_min_backoff_ms",
        "process_invoice_max_backoff_ms",
        "sweeper_max_resends",
    ],
)
def test_the_new_settings_must_be_positive(field: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: 0})
