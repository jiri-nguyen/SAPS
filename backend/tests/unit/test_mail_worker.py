"""Worker wiring of the mail intake: adapter choice, settings and the shared timer (SAPS-45)."""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from saps.adapters.mail.imap_mailbox import ImapMailbox
from saps.config import Settings
from saps.ports.inbound_mail import MailboxOwner
from saps.ports.mailbox import MailboxUnavailableError
from saps.worker import mail_intake as worker
from saps.worker.mail_intake import build_mailbox
from saps.worker.sweeper import SweeperMiddleware
from saps.worker.timer import TimerMiddleware
from tests.fakes import MemoryQueue


def test_mail_settings_default_to_no_intake() -> None:
    s = Settings(_env_file=None)
    assert (s.mail_adapter, s.mail_poll_seconds, s.mail_batch_size) == ("none", 60, 50)
    assert (s.imap_host, s.imap_port, s.imap_ssl) == ("localhost", 3143, False)
    assert "demo-secret" not in repr(Settings(_env_file=None, imap_password="demo-secret"))  # type: ignore[arg-type]  # noqa: S106


def test_the_imap_adapter_is_chosen_by_configuration() -> None:
    settings = Settings(_env_file=None, mail_adapter="imap", imap_host="mail", imap_password="pw")  # type: ignore[arg-type]  # noqa: S106
    assert isinstance(build_mailbox(settings), ImapMailbox)


@pytest.mark.parametrize("name", ["none", "graph", "pop3"])
def test_other_adapters_are_not_available_yet(name: str) -> None:  # `graph` comes with SAPS-53
    with pytest.raises(ValueError, match="Unknown MAIL_ADAPTER"):
        build_mailbox(Settings(_env_file=None, mail_adapter=name))


def test_the_mail_timer_ticks_in_its_own_named_thread_and_stops() -> None:
    ticks: list[str] = []

    async def tick() -> None:
        import threading

        ticks.append(threading.current_thread().name)

    timer = TimerMiddleware("mail-intake", 0.05, tick)
    timer.after_worker_boot(MagicMock(), MagicMock())
    deadline = time.monotonic() + 3
    while len(ticks) < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    timer.before_worker_shutdown(MagicMock(), MagicMock())
    assert len(ticks) >= 2 and set(ticks) == {"mail-intake"}


def test_the_sweeper_timer_keeps_its_name() -> None:
    assert SweeperMiddleware(1, MagicMock())._name == "sweeper"


class _Repo:
    """Stands in for SqlInboundMailRepository; the tests choose how it misbehaves."""

    def __init__(self, *, list_error: bool = False, lock: bool = True) -> None:
        self.list_error, self.lock = list_error, lock
        self.locked: list[str] = []

    async def list_mailboxes(self) -> list[MailboxOwner]:
        if self.list_error:
            raise ConnectionError("database down")
        return [MailboxOwner(uuid4(), "Demo Vietnam", "ap@vn.example.com")]

    @asynccontextmanager
    async def try_lock_mailbox(self, address: str) -> AsyncIterator[bool]:
        self.locked.append(address)
        yield self.lock


def _wire(
    monkeypatch: pytest.MonkeyPatch, repo: _Repo, polled: list[str], *, poll_error: Exception | None = None
) -> None:
    monkeypatch.setattr(worker, "get_engine", lambda url: object())
    monkeypatch.setattr(worker, "SqlInboundMailRepository", lambda engine: repo)

    async def poll(settings: Settings, owner: MailboxOwner, *args: object) -> None:
        if poll_error is not None:
            raise poll_error
        polled.append(owner.mailbox_address)

    monkeypatch.setattr(worker, "_poll", poll)


async def test_a_tick_polls_every_unlocked_mailbox(monkeypatch: pytest.MonkeyPatch) -> None:
    repo, polled = _Repo(), []
    _wire(monkeypatch, repo, polled)
    await worker.run_mail_intake(Settings(_env_file=None), MemoryQueue(), MagicMock())
    assert polled == ["ap@vn.example.com"]


async def test_a_mailbox_read_by_another_process_is_skipped(monkeypatch: pytest.MonkeyPatch) -> None:  # EC-11
    repo, polled = _Repo(lock=False), []
    _wire(monkeypatch, repo, polled)
    await worker.run_mail_intake(Settings(_env_file=None), MemoryQueue(), MagicMock())
    assert repo.locked == ["ap@vn.example.com"] and polled == []


async def test_a_tick_never_raises(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    polled: list[str] = []
    _wire(monkeypatch, _Repo(list_error=True), polled)
    with caplog.at_level(logging.WARNING):
        await worker.run_mail_intake(Settings(_env_file=None), MemoryQueue(), MagicMock())
    assert "mail_poll_failed" in caplog.text and polled == []

    caplog.clear()
    _wire(monkeypatch, _Repo(), polled, poll_error=RuntimeError("unexpected"))
    with caplog.at_level(logging.WARNING):
        await worker.run_mail_intake(Settings(_env_file=None), MemoryQueue(), MagicMock())
    assert "mail_poll_failed" in caplog.text

    caplog.clear()
    _wire(monkeypatch, _Repo(), polled, poll_error=MailboxUnavailableError("refused"))
    with caplog.at_level(logging.WARNING):
        await worker.run_mail_intake(Settings(_env_file=None), MemoryQueue(), MagicMock())
    assert "mail_poll_failed" in caplog.text
