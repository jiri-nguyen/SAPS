"""IMAP adapter of the Mailbox Port (SAPS-45, ADR-0012): the local test mail server (GreenMail) of the demo.

Standard library only (`imaplib`, `email`). `imaplib` blocks, so every call runs in a thread with its own
connection. The user name is the mailbox address; the demo server accepts one shared password for all
mailboxes. Outlook comes later as a Microsoft Graph adapter behind the same port.
"""

import asyncio
import hashlib
import imaplib
from datetime import UTC, datetime
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import parsedate_to_datetime

from saps.ports.mailbox import Attachment, Mail, MailboxUnavailableError, MailRef

INBOX = "INBOX"
TIMEOUT_SECONDS = 15
_IMAP_ERRORS = (imaplib.IMAP4.error, OSError)
MAX_KEY = 500


class ImapMailbox:
    def __init__(self, host: str, port: int, *, ssl: bool, password: str) -> None:
        self._host = host
        self._port = port
        self._ssl = ssl
        self._password = password

    # --- MailboxPort ----------------------------------------------------------------------------------------

    async def list_new(self, mailbox: str, limit: int) -> list[MailRef]:
        return await asyncio.to_thread(self._list_new, mailbox, limit)

    async def read(self, mailbox: str, ref: MailRef) -> Mail:
        return await asyncio.to_thread(self._read, mailbox, ref)

    async def move(self, mailbox: str, ref: MailRef, folder: str) -> None:
        await asyncio.to_thread(self._move, mailbox, ref, folder)

    # --- Blocking implementation ---------------------------------------------------------------------------

    def _connect(self, mailbox: str) -> imaplib.IMAP4:
        try:
            client: imaplib.IMAP4 = (
                imaplib.IMAP4_SSL(self._host, self._port, timeout=TIMEOUT_SECONDS)
                if self._ssl
                else imaplib.IMAP4(self._host, self._port, timeout=TIMEOUT_SECONDS)
            )
            client.login(mailbox, self._password)
            status, _ = client.select(INBOX)
            if status != "OK":
                raise MailboxUnavailableError(f"cannot open {INBOX} of {mailbox}")
        except _IMAP_ERRORS as exc:
            raise MailboxUnavailableError(f"{type(exc).__name__} for {mailbox}") from exc
        return client

    @staticmethod
    def _close(client: imaplib.IMAP4) -> None:
        try:
            client.logout()
        except _IMAP_ERRORS:  # the connection is gone anyway
            pass

    def _list_new(self, mailbox: str, limit: int) -> list[MailRef]:
        client = self._connect(mailbox)
        try:
            status, data = client.uid("SEARCH", "ALL")
            if status != "OK":
                raise MailboxUnavailableError(f"search failed for {mailbox}")
            uids = [u.decode() for u in (data[0] or b"").split()[:limit]]  # ascending UIDs: oldest first
            return [MailRef(self._mail_key(client, uid), uid) for uid in uids]
        except _IMAP_ERRORS as exc:
            raise MailboxUnavailableError(f"{type(exc).__name__} for {mailbox}") from exc
        finally:
            self._close(client)

    def _mail_key(self, client: imaplib.IMAP4, uid: str) -> str:
        """The Message-ID header; a mail without one is identified by the hash of its content (EC-12)."""
        _, data = client.uid("FETCH", uid, "(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID)])")
        header = message_from_bytes(_literal(data), policy=policy.default)
        message_id = str(header.get("Message-ID") or "").strip()
        if message_id:
            return message_id[:MAX_KEY]
        return "sha256:" + hashlib.sha256(self._raw(client, uid)).hexdigest()

    @staticmethod
    def _raw(client: imaplib.IMAP4, uid: str) -> bytes:
        _, data = client.uid("FETCH", uid, "(BODY.PEEK[])")
        return _literal(data)

    def _read(self, mailbox: str, ref: MailRef) -> Mail:
        client = self._connect(mailbox)
        try:
            raw = self._raw(client, ref.handle)
        except _IMAP_ERRORS as exc:
            raise MailboxUnavailableError(f"{type(exc).__name__} for {mailbox}") from exc
        finally:
            self._close(client)
        return parse_mail(ref, raw)

    def _move(self, mailbox: str, ref: MailRef, folder: str) -> None:
        client = self._connect(mailbox)
        uid = ref.handle
        try:
            client.create(folder)  # answers NO when it exists: fine
            if b"MOVE" in _capabilities(client):
                status, _ = client.uid("MOVE", uid, folder)
                if status == "OK":
                    return
            status, _ = client.uid("COPY", uid, folder)
            if status != "OK":
                raise MailboxUnavailableError(f"cannot copy a mail of {mailbox} to {folder}")
            client.uid("STORE", uid, "+FLAGS", r"(\Deleted)")
            client.expunge()
        except _IMAP_ERRORS as exc:
            raise MailboxUnavailableError(f"{type(exc).__name__} for {mailbox}") from exc
        finally:
            self._close(client)


def _capabilities(client: imaplib.IMAP4) -> set[bytes]:
    return {c.upper() if isinstance(c, bytes) else str(c).encode().upper() for c in client.capabilities}


def _literal(data: list[object]) -> bytes:
    """The body of a FETCH answer: imaplib returns `(envelope, bytes)` tuples and a closing `b")"`."""
    for item in data:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
            return item[1]
    return b""


def parse_mail(ref: MailRef, raw: bytes) -> Mail:
    """Sender, subject, date and the attachments of a raw mail; inline parts are not attachments (EC-04)."""
    message = message_from_bytes(raw, policy=policy.default)
    assert isinstance(message, EmailMessage)  # policy.default always builds EmailMessage
    attachments: list[Attachment] = []
    for part in message.walk():
        if part.is_multipart() or not _is_attachment(part):
            continue
        payload = part.get_payload(decode=True)
        attachments.append(
            Attachment(
                position=len(attachments) + 1,
                name=part.get_filename(),
                declared_content_type=part.get_content_type(),
                data=payload if isinstance(payload, bytes) else b"",
            )
        )
    return Mail(
        ref=ref,
        sender=str(message.get("From") or ""),
        subject=str(message.get("Subject") or ""),
        received_at=_date_of(message),
        attachments=attachments,
    )


def _is_attachment(part: EmailMessage) -> bool:
    disposition = part.get_content_disposition()
    if disposition == "attachment":
        return True
    # No disposition at all but a file name and no text: some clients send attachments like this.
    return disposition is None and bool(part.get_filename()) and part.get_content_maintype() != "text"


def _date_of(message: EmailMessage) -> datetime:
    try:
        moment = parsedate_to_datetime(str(message.get("Date")))
    except TypeError, ValueError:
        return datetime.now(UTC)
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)
