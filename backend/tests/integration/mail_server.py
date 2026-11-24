"""A GreenMail test mail server (SMTP and IMAP) for the mail intake tests (SAPS-45, ADR-0012)."""

import imaplib
import smtplib
import time
from collections.abc import Iterator
from dataclasses import dataclass
from email.message import EmailMessage
from uuid import uuid4

import pytest

from saps.adapters.mail.imap_mailbox import ImapMailbox

IMAGE = "greenmail/standalone:2.1.15"
OPTIONS = "-Dgreenmail.setup.test.all -Dgreenmail.hostname=0.0.0.0 -Dgreenmail.auth.disabled"
PASSWORD = "demo-mail-pw"  # noqa: S105  (test server accepts any password)


@dataclass(frozen=True)
class MailServer:
    host: str
    smtp_port: int
    imap_port: int

    def mailbox(self) -> ImapMailbox:
        return ImapMailbox(self.host, self.imap_port, ssl=False, password=PASSWORD)

    def send(
        self,
        to: str | list[str],
        *,
        subject: str = "Invoice",
        attachments: dict[str, bytes] | None = None,
        message_id: str | None = None,
    ) -> str:
        """Send a mail; returns its Message-ID."""
        message = EmailMessage()
        message["From"] = "Vendor Ltd <billing@vendor.example.net>"
        message["To"] = ", ".join([to] if isinstance(to, str) else to)
        message["Subject"] = subject
        message_id = message_id or f"<{uuid4().hex}@vendor.example.net>"
        message["Message-ID"] = message_id
        message.set_content("Please find the invoice attached.")
        for name, data in (attachments or {}).items():
            kind = "pdf" if data.startswith(b"%PDF") else "octet-stream"
            maintype = "application"
            message.add_attachment(data, maintype=maintype, subtype=kind, filename=name)
        with smtplib.SMTP(self.host, self.smtp_port) as smtp:
            smtp.send_message(message)
        return message_id


@pytest.fixture(scope="session")
def mail_server() -> Iterator[MailServer]:
    containers = pytest.importorskip("testcontainers.core.container")
    try:
        container = (
            containers.DockerContainer(IMAGE)
            .with_exposed_ports(3025, 3143)
            .with_env("GREENMAIL_OPTS", OPTIONS)
        )
        container.start()
    except Exception as exc:  # Docker not running
        pytest.skip(f"Docker not available: {exc}")
    try:
        host = container.get_container_host_ip()
        server = MailServer(
            host, int(container.get_exposed_port(3025)), int(container.get_exposed_port(3143))
        )
        deadline = time.monotonic() + 60
        while True:  # Docker accepts connections before GreenMail listens: wait for the real greetings
            try:
                with smtplib.SMTP(server.host, server.smtp_port, timeout=3) as smtp:
                    smtp.noop()
                imaplib.IMAP4(server.host, server.imap_port, timeout=3).logout()
                break
            except OSError, smtplib.SMTPException, imaplib.IMAP4.error:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.5)
        yield server
    finally:
        container.stop()
