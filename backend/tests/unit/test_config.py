from saps.config import Settings


def test_defaults_follow_the_developer_guide() -> None:
    s = Settings(_env_file=None)
    assert s.dramatiq_heartbeat_timeout_ms == 30_000
    assert s.dramatiq_maintenance_chance == 100_000
    assert s.max_upload_size_mb == 10
    assert s.session_cookie_secure is True


def test_environment_overrides_defaults(monkeypatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "5")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    s = Settings(_env_file=None)
    assert s.max_upload_size_mb == 5
    assert s.session_cookie_secure is False


def test_secret_is_not_shown_in_repr() -> None:
    assert "local-test-secret" not in repr(Settings(_env_file=None))
