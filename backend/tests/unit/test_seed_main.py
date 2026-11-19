import logging

import pytest

from saps import seed
from saps.config import get_settings


def test_seed_is_skipped_without_password(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("SEED_USER_PASSWORD", "")
    get_settings.cache_clear()
    try:
        seed.main()  # configure_logging replaces root handlers, so re-attach the capture handler
    finally:
        get_settings.cache_clear()
    logging.getLogger().addHandler(caplog.handler)
    caplog.set_level(logging.WARNING)
    seed.log.warning("probe")
    assert any(r.getMessage() == "probe" for r in caplog.records)


def test_seed_runs_when_a_password_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    async def fake_run(database_url: str, password: str) -> None:
        calls.append((database_url, password))

    monkeypatch.setenv("SEED_USER_PASSWORD", "local-pw")
    monkeypatch.setattr(seed, "_run", fake_run)
    get_settings.cache_clear()
    try:
        seed.main()
    finally:
        get_settings.cache_clear()
    assert calls and calls[0][1] == "local-pw"
