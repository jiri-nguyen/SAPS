"""IMAP adapter: parsing of raw mails and the protocol steps with a fake client (SAPS-45 TS-01)."""

import imaplib
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Any

import pytest

from saps.adapters.mail.imap_mailbox import ImapMailbox, parse_mail
from saps.ports.mailbox import MailboxUnavailableError, MailRef

IMAP_ERROR = imaplib.IMAP4.error  # kept before the tests replace imaplib.IMAP4
REF = MailRef("<m1@example.net>", "7")
PDF = b"%PDF-1.7\n% invoice\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"png"


def _mail() -> EmailMessage:
    message = EmailMessage()
    message["From"] = "Vendor Ltd <billing@vendor.example.net>"
    message["To"] = "ap@vn.example.com"
    message["Subject"] = "Invoice 4711"
    message["Date"] = "Mon, 01 Mar 2027 09:30:00 +0700"
    message["Message-ID"] = "<m1@example.net>"
    message.set_content("Please find the invoice attached.")
    return message


def test_attachments_are_the_attached_files_in_order() -> None:  # EC-01
    message = _mail()
    message.add_attachment(PDF, maintype="application", subtype="pdf", filename="inv-1.pdf")
    message.add_attachment(PNG, maintype="image", subtype="png", filename="scan.png")
    mail = parse_mail(REF, message.as_bytes())
    assert (mail.sender, mail.subject) == ("Vendor Ltd <billing@vendor.example.net>", "Invoice 4711")
    assert mail.received_at == datetime(2027, 3, 1, 2, 30, tzinfo=UTC)
    assert [(a.position, a.name, a.declared_content_type, a.data) for a in mail.attachments] == [
        (1, "inv-1.pdf", "application/pdf", PDF),
        (2, "scan.png", "image/png", PNG),
    ]


def test_inline_images_and_the_body_are_not_attachments() -> None:  # EC-04
    message = _mail()
    message.add_alternative('<p>Regards <img src="cid:logo"></p>', subtype="html")
    message.get_payload()[1].add_related(
        PNG, maintype="image", subtype="png", cid="<logo>", disposition="inline", filename="logo.png"
    )  # type: ignore[union-attr]
    message.add_attachment(PDF, maintype="application", subtype="pdf", filename="inv.pdf")
    mail = parse_mail(REF, message.as_bytes())
    assert [a.name for a in mail.attachments] == ["inv.pdf"]


def test_a_file_without_disposition_counts_but_a_text_body_does_not() -> None:
    raw = (
        b"From: a@example.net\r\nSubject: s\r\nMIME-Version: 1.0\r\n"
        b'Content-Type: multipart/mixed; boundary="b"\r\n\r\n'
        b"--b\r\nContent-Type: text/plain\r\n\r\nbody\r\n"
        b'--b\r\nContent-Type: application/pdf; name="x.pdf"\r\nContent-Transfer-Encoding: base64\r\n\r\n'
        b"JVBERi0xLjcK\r\n--b\r\n"
        b"Content-Type: application/octet-stream\r\n\r\nno name, no disposition\r\n--b--\r\n"
    )
    mail = parse_mail(REF, raw)
    assert [(a.name, a.data[:5]) for a in mail.attachments] == [("x.pdf", b"%PDF-")]


def test_a_mail_without_attachments_or_date_still_parses() -> None:  # EC-02
    message = _mail()
    del message["Date"]
    mail = parse_mail(REF, message.as_bytes())
    assert mail.attachments == [] and mail.received_at.tzinfo is not None


def test_a_naive_date_is_taken_as_utc() -> None:
    message = _mail()
    message.replace_header("Date", "Mon, 01 Mar 2027 09:30:00 -0000")
    assert parse_mail(REF, message.as_bytes()).received_at.tzinfo is not None


class FakeImap:
    """Just enough of imaplib.IMAP4 for list, read and move."""

    def __init__(self, *, move: bool = True, login_error: bool = False) -> None:
        self.capabilities = ("IMAP4REV1", "MOVE") if move else ("IMAP4REV1",)
        self.login_error = login_error
        self.calls: list[tuple[Any, ...]] = []
        self.raw = {"3": _mail().as_bytes(), "9": b"Subject: no id\r\n\r\nbody"}
        self.move_status = "OK"

    def login(self, user: str, password: str) -> tuple[str, list[bytes]]:
        if self.login_error:
            raise IMAP_ERROR("AUTHENTICATIONFAILED")
        self.calls.append(("login", user))
        return "OK", []

    def select(self, folder: str) -> tuple[str, list[bytes]]:
        return "OK", [b"2"]

    def logout(self) -> None:
        self.calls.append(("logout",))

    def create(self, folder: str) -> tuple[str, list[bytes]]:
        self.calls.append(("create", folder))
        return "NO", [b"exists"]

    def expunge(self) -> tuple[str, list[bytes]]:
        self.calls.append(("expunge",))
        return "OK", []

    def uid(self, command: str, *args: str) -> tuple[str, list[Any]]:
        self.calls.append((command, *args))
        if command == "SEARCH":
            return "OK", [b"3 9 12"]
        if command == "FETCH" and "HEADER.FIELDS" in args[1]:
            uid = args[0]
            header = _mail().as_bytes().split(b"\r\n\r\n")[0] if uid == "3" else b"Subject: x"
            keep = b"\r\n".join(
                line for line in header.splitlines() if line.lower().startswith(b"message-id")
            )
            return "OK", [(b"1 (UID 1 BODY[HEADER.FIELDS (MESSAGE-ID)] {1}", keep + b"\r\n\r\n"), b")"]
        if command == "FETCH":
            return "OK", [(b"1 (BODY[] {1}", self.raw[args[0]]), b")"]
        if command == "MOVE":
            return self.move_status, []
        return "OK", []


@pytest.fixture
def imap(monkeypatch: pytest.MonkeyPatch) -> FakeImap:
    fake = FakeImap()
    monkeypatch.setattr(imaplib, "IMAP4", lambda host, port, timeout: fake)
    return fake


def _mailbox() -> ImapMailbox:
    return ImapMailbox("mail", 3143, ssl=False, password="demo")  # noqa: S106  (demo server only)


async def test_list_new_returns_the_oldest_mails_with_their_keys(imap: FakeImap) -> None:
    refs = await _mailbox().list_new("ap@vn.example.com", 2)
    assert [r.handle for r in refs] == ["3", "9"]
    assert refs[0].mail_key == "<m1@example.net>"
    assert refs[1].mail_key.startswith("sha256:") and len(refs[1].mail_key) == 71  # EC-12
    assert ("login", "ap@vn.example.com") in imap.calls and ("logout",) in imap.calls


async def test_read_parses_the_mail(imap: FakeImap) -> None:
    mail = await _mailbox().read("ap@vn.example.com", MailRef("<m1@example.net>", "3"))
    assert mail.subject == "Invoice 4711"


async def test_move_uses_move_when_available_and_copy_otherwise(
    imap: FakeImap, monkeypatch: pytest.MonkeyPatch
) -> None:
    await _mailbox().move("ap@vn.example.com", REF.__class__("k", "3"), "Processed")
    assert ("create", "Processed") in imap.calls and ("MOVE", "3", "Processed") in imap.calls
    assert not any(c[0] == "COPY" for c in imap.calls)

    imap.calls.clear()
    imap.move_status = "NO"  # the server refuses MOVE: fall back
    await _mailbox().move("ap@vn.example.com", MailRef("k", "3"), "Skipped")
    assert [c[0] for c in imap.calls if c[0] in ("MOVE", "COPY", "STORE", "expunge")] == [
        "MOVE",
        "COPY",
        "STORE",
        "expunge",
    ]

    fake = FakeImap(move=False)
    monkeypatch.setattr(imaplib, "IMAP4", lambda host, port, timeout: fake)
    await _mailbox().move("ap@vn.example.com", MailRef("k", "3"), "Processed")
    assert not any(c[0] == "MOVE" for c in fake.calls) and any(c[0] == "COPY" for c in fake.calls)


async def test_a_refused_sign_in_or_an_unreachable_server_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # EC-08
    monkeypatch.setattr(imaplib, "IMAP4", lambda host, port, timeout: FakeImap(login_error=True))
    with pytest.raises(MailboxUnavailableError):
        await _mailbox().list_new("ap@vn.example.com", 5)

    def refuse(host: str, port: int, timeout: int) -> None:
        raise ConnectionRefusedError

    monkeypatch.setattr(imaplib, "IMAP4", refuse)
    with pytest.raises(MailboxUnavailableError):
        await _mailbox().read("ap@vn.example.com", REF)
    with pytest.raises(MailboxUnavailableError):
        await _mailbox().move("ap@vn.example.com", REF, "Processed")


async def test_ssl_uses_the_ssl_client(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeImap()
    used: list[str] = []
    monkeypatch.setattr(imaplib, "IMAP4_SSL", lambda host, port, timeout: used.append("ssl") or fake)
    await ImapMailbox("mail", 993, ssl=True, password="x").list_new("a@b.c", 1)  # noqa: S106
    assert used == ["ssl"]


class BrokenImap(FakeImap):
    """A server that answers NO, or whose connection breaks, at the step the test names."""

    def __init__(
        self, *, select: str = "OK", search: str = "OK", copy: str = "OK", drop: str | None = None
    ) -> None:
        super().__init__(move=False)
        self.select_status, self.search_status, self.copy_status, self.drop = select, search, copy, drop

    def select(self, folder: str) -> tuple[str, list[bytes]]:
        return self.select_status, [b"0"]

    def logout(self) -> None:
        raise OSError("connection already closed")  # closing must never hide the real result

    def uid(self, command: str, *args: str) -> tuple[str, list[Any]]:
        if command == self.drop:
            raise OSError("connection reset")
        if command == "SEARCH" and self.search_status != "OK":
            return self.search_status, []
        if command == "COPY":
            return self.copy_status, []
        return super().uid(command, *args)


async def test_a_mailbox_that_cannot_be_opened_or_searched_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # EC-08
    monkeypatch.setattr(imaplib, "IMAP4", lambda host, port, timeout: BrokenImap(select="NO"))
    with pytest.raises(MailboxUnavailableError, match="cannot open"):
        await _mailbox().list_new("ap@vn.example.com", 5)
    monkeypatch.setattr(imaplib, "IMAP4", lambda host, port, timeout: BrokenImap(search="NO"))
    with pytest.raises(MailboxUnavailableError, match="search failed"):
        await _mailbox().list_new("ap@vn.example.com", 5)


@pytest.mark.parametrize("step", ["SEARCH", "FETCH", "COPY"])
async def test_a_connection_that_breaks_midway_is_unavailable(
    step: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(imaplib, "IMAP4", lambda host, port, timeout: BrokenImap(drop=step))
    box = _mailbox()
    with pytest.raises(MailboxUnavailableError):
        if step == "SEARCH":
            await box.list_new("ap@vn.example.com", 5)
        elif step == "FETCH":
            await box.read("ap@vn.example.com", REF)
        else:
            await box.move("ap@vn.example.com", MailRef("k", "3"), "Processed")


async def test_a_refused_copy_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(imaplib, "IMAP4", lambda host, port, timeout: BrokenImap(copy="NO"))
    with pytest.raises(MailboxUnavailableError, match="cannot copy"):
        await _mailbox().move("ap@vn.example.com", MailRef("k", "3"), "Processed")


async def test_a_fetch_without_a_body_reads_as_an_empty_mail(monkeypatch: pytest.MonkeyPatch) -> None:
    class NoBody(FakeImap):
        def uid(self, command: str, *args: str) -> tuple[str, list[Any]]:
            return ("OK", [None, b")"]) if command == "FETCH" else super().uid(command, *args)

    monkeypatch.setattr(imaplib, "IMAP4", lambda host, port, timeout: NoBody())
    mail = await _mailbox().read("ap@vn.example.com", REF)
    assert mail.attachments == []
