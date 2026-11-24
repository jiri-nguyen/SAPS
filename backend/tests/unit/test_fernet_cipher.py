"""Encryption of the stored tokens and the sign-in cookie (SAPS-44)."""

from cryptography.fernet import Fernet

from saps.adapters.security.fernet_cipher import FernetTokenCipher


def test_round_trip_tampering_other_key_and_age() -> None:
    cipher = FernetTokenCipher(Fernet.generate_key().decode())
    secret = cipher.encrypt("refresh-token")
    assert "refresh-token" not in secret
    assert cipher.decrypt(secret) == "refresh-token"
    assert cipher.decrypt(secret, max_age_seconds=600) == "refresh-token"
    assert cipher.decrypt(secret[:-2] + "AA") is None
    assert cipher.decrypt("not a token ü") is None
    assert FernetTokenCipher(Fernet.generate_key().decode()).decrypt(secret) is None


def test_too_old_values_are_refused() -> None:
    key = Fernet.generate_key()
    old = Fernet(key).encrypt_at_time(b"state", current_time=1_000)
    assert FernetTokenCipher(key.decode()).decrypt(old.decode(), max_age_seconds=600) is None
