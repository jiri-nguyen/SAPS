import json
import logging

from saps.logging_config import JsonFormatter


def test_json_formatter_includes_extra_fields() -> None:
    record = logging.LogRecord("saps.test", logging.INFO, __file__, 1, "invoice_uploaded", (), None)
    record.invoice_id = "abc"
    line = json.loads(JsonFormatter().format(record))
    assert line["message"] == "invoice_uploaded"
    assert line["invoice_id"] == "abc"
    assert line["level"] == "INFO"


def test_configure_logging_installs_one_json_handler() -> None:
    from saps.logging_config import configure_logging

    configure_logging("DEBUG")
    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert isinstance(root.handlers[0].formatter, JsonFormatter)
    assert root.level == logging.DEBUG


def test_exception_is_included() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord("saps.test", logging.ERROR, __file__, 1, "failed", (), sys.exc_info())
    assert "ValueError: boom" in json.loads(JsonFormatter().format(record))["exception"]
