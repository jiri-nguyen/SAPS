from saps.adapters.security.argon2_hasher import Argon2PasswordHasher


def test_hash_is_argon2id_and_verifies() -> None:
    hasher = Argon2PasswordHasher()
    hashed = hasher.hash("secret-pw")
    assert hashed.startswith("$argon2id$")
    assert hasher.verify(hashed, "secret-pw") is True
    assert hasher.verify(hashed, "other") is False


def test_invalid_hash_and_dummy_check_do_not_raise() -> None:
    hasher = Argon2PasswordHasher()
    assert hasher.verify("not-a-hash", "pw") is False
    hasher.dummy_verify("pw")
