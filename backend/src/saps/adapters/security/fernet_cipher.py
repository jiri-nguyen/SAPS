"""Fernet (AES-128-CBC + HMAC-SHA256) for the stored tokens and the sign-in cookie (SAPS-44 §3.1)."""

from cryptography.fernet import Fernet, InvalidToken


class FernetTokenCipher:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode("ascii"))

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode("ascii")

    def decrypt(self, value: str, *, max_age_seconds: int | None = None) -> str | None:
        try:
            return self._fernet.decrypt(value.encode("ascii"), ttl=max_age_seconds).decode()
        except InvalidToken, UnicodeError, ValueError:
            return None
