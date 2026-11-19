"""Argon2id implementation of the PasswordHasher port (ADR-0008)."""

from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import InvalidHashError, VerificationError


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._argon2 = _Argon2()  # Argon2id with the library's recommended parameters
        self._dummy_hash = self._argon2.hash("timing-equalizer-not-a-real-password")

    def hash(self, password: str) -> str:
        return self._argon2.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._argon2.verify(password_hash, password)
        except VerificationError, InvalidHashError:
            return False

    def dummy_verify(self, password: str) -> None:
        self.verify(self._dummy_hash, password)
