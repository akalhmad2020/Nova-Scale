from app.modules.identity.infrastructure.security.refresh_token_service import (
    SecureRefreshTokenService,
)


def test_generate_refresh_token_returns_non_empty_token() -> None:
    service = SecureRefreshTokenService()

    token = service.generate()

    assert token
    assert isinstance(token, str)


def test_generate_refresh_token_returns_unique_tokens() -> None:
    service = SecureRefreshTokenService()

    first_token = service.generate()
    second_token = service.generate()

    assert first_token != second_token


def test_hash_refresh_token_is_deterministic() -> None:
    service = SecureRefreshTokenService()

    token = "example-refresh-token"

    first_hash = service.hash(token)
    second_hash = service.hash(token)

    assert first_hash == second_hash


def test_hash_refresh_token_does_not_store_raw_token() -> None:
    service = SecureRefreshTokenService()

    token = "example-refresh-token"

    token_hash = service.hash(token)

    assert token_hash != token


def test_different_refresh_tokens_have_different_hashes() -> None:
    service = SecureRefreshTokenService()

    first_hash = service.hash("first-token")
    second_hash = service.hash("second-token")

    assert first_hash != second_hash
