"""Send a test mail to a company mailbox of the local test mail server (SAPS-45).

    python backend/tools/send_test_mail.py --to ap@vn.example.com backend/fixtures/ds-01/invoices/*.pdf

Every file is attached. Without files the mail has no attachment (the intake skips it). Standard library
only. The SAPS Worker reads the mailboxes every `MAIL_POLL_SECONDS` (default 60 s).
"""

import argparse
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4

SUBTYPES = {
    ".pdf": ("application", "pdf"),
    ".png": ("image", "png"),
    ".jpg": ("image", "jpeg"),
    ".jpeg": ("image", "jpeg"),
}


def build_mail(to: str, sender: str, subject: str, files: list[Path]) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message["Message-ID"] = f"<{uuid4().hex}@send-test-mail.local>"
    message.set_content("Please find our invoice attached.")
    for file in files:
        maintype, subtype = SUBTYPES.get(file.suffix.lower(), ("application", "octet-stream"))
        message.add_attachment(file.read_bytes(), maintype=maintype, subtype=subtype, filename=file.name)
    return message


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--to", required=True, help="company mailbox, e.g. ap@vn.example.com")
    parser.add_argument("--smtp", default="localhost:3025", help="host:port of the test mail server")
    parser.add_argument("--from", dest="sender", default="Vendor Ltd <billing@vendor.example.net>")
    parser.add_argument("--subject", default="Invoice")
    parser.add_argument("files", nargs="*", type=Path, help="invoice files to attach (PDF, PNG, JPG)")
    args = parser.parse_args(argv)
    missing = [f for f in args.files if not f.is_file()]
    if missing:
        print(f"not a file: {', '.join(map(str, missing))}", file=sys.stderr)
        return 2
    host, _, port = args.smtp.partition(":")
    message = build_mail(args.to, args.sender, args.subject, args.files)
    with smtplib.SMTP(host, int(port or 3025)) as smtp:
        smtp.send_message(message)
    print(f"sent {message['Message-ID']} to {args.to} with {len(args.files)} attachment(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
