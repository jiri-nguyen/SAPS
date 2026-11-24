"""Port of the company mailboxes (SAPS-45, ADR-0012). Adapters: IMAP (demo), Microsoft Graph (later)."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

PROCESSED_FOLDER = "Processed"
SKIPPED_FOLDER = "Skipped"


class MailboxUnavailableError(Exception):
    """The mail server cannot be reached, or refuses the sign-in (EC-08)."""


@dataclass(frozen=True)
class MailRef:
    """A mail found in the inbox. `handle` is the adapter's own address of the mail (e.g. an IMAP UID)."""

    mail_key: str  # stable across polls: the Message-ID, or a hash of the raw mail (EC-12)
    handle: str


@dataclass(frozen=True)
class Attachment:
    position: int  # order among the attachments of the mail, from 1
    name: str | None
    declared_content_type: str
    data: bytes


@dataclass(frozen=True)
class Mail:
    ref: MailRef
    sender: str
    subject: str
    received_at: datetime
    attachments: Sequence[Attachment]


class MailboxPort(Protocol):
    async def list_new(self, mailbox: str, limit: int) -> list[MailRef]:
        """Mails in the inbox, oldest first, at most `limit`."""
        ...

    async def read(self, mailbox: str, ref: MailRef) -> Mail:
        """Sender, subject, date and the attachments (not inline parts, EC-04)."""
        ...

    async def move(self, mailbox: str, ref: MailRef, folder: str) -> None:
        """Move the mail to `Processed` or `Skipped`; creates the folder when missing."""
        ...
