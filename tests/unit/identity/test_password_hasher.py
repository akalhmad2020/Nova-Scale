from app.modules.identity.infrastructure.security.password_hasher import (
    Argon2PasswordHasher,
)


def test_hash_and_verify_password() -> None:
    hasher = Argon2PasswordHasher()

    password = "correct horse battery staple"
    password_hash = hasher.hash(password)

    assert password_hash != password
    assert hasher.verify(password, password_hash) is True


def test_verify_rejects_wrong_password() -> None:
    hasher = Argon2PasswordHasher()

    password_hash = hasher.hash("correct password")

    assert hasher.verify("wrong password", password_hash) is False


def test_hashes_are_unique_for_same_password() -> None:
    hasher = Argon2PasswordHasher()

    password = "same password"

    first_hash = hasher.hash(password)
    second_hash = hasher.hash(password)

    assert first_hash != second_hash
