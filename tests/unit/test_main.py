import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_create_app_enables_docs_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        app_env="local",
        docs_enabled=True,
        allowed_hosts=["localhost", "127.0.0.1", "testserver"],
        auth_jwt_secret="local-test-secret",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = create_app()

    assert application.docs_url == "/docs"
    assert application.redoc_url == "/redoc"
    assert application.openapi_url == "/openapi.json"


def test_create_app_disables_docs_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        app_env="production",
        debug=False,
        docs_enabled=False,
        allowed_hosts=["api.novascale.example"],
        cors_allowed_origins=[],
        hsts_enabled=True,
        auth_jwt_secret=("a-strong-production-secret-with-more-than-32-characters"),
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = create_app()

    assert application.docs_url is None
    assert application.redoc_url is None
    assert application.openapi_url is None


def test_app_accepts_trusted_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        app_env="local",
        docs_enabled=True,
        allowed_hosts=["testserver"],
        auth_jwt_secret="local-test-secret",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = create_app()

    with TestClient(application) as client:
        response = client.get("/health")

    assert response.status_code == 200


def test_app_rejects_untrusted_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        app_env="local",
        docs_enabled=True,
        allowed_hosts=["testserver"],
        auth_jwt_secret="local-test-secret",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = create_app()

    with TestClient(
        application,
        base_url="http://malicious.example",
    ) as client:
        response = client.get("/health")

    assert response.status_code == 400


def test_app_does_not_add_cors_when_origins_are_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        app_env="local",
        docs_enabled=True,
        allowed_hosts=["testserver"],
        cors_allowed_origins=[],
        auth_jwt_secret="local-test-secret",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = create_app()

    with TestClient(application) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "https://app.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert "access-control-allow-origin" not in response.headers


def test_app_allows_configured_cors_origin_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        app_env="local",
        docs_enabled=True,
        allowed_hosts=["testserver"],
        cors_allowed_origins=["https://app.novascale.example"],
        auth_jwt_secret="local-test-secret",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = create_app()

    with TestClient(application) as client:
        response = client.options(
            "/health",
            headers={
                "Origin": "https://app.novascale.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.novascale.example"
    assert "access-control-allow-credentials" not in response.headers


def test_app_adds_security_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        app_env="local",
        docs_enabled=True,
        allowed_hosts=["testserver"],
        cors_allowed_origins=[],
        auth_jwt_secret="local-test-secret",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = create_app()

    with TestClient(application) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_app_does_not_add_hsts_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        app_env="local",
        docs_enabled=True,
        allowed_hosts=["testserver"],
        cors_allowed_origins=[],
        hsts_enabled=False,
        auth_jwt_secret="local-test-secret",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = create_app()

    with TestClient(application) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert "strict-transport-security" not in response.headers


def test_app_adds_hsts_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        app_env="production",
        debug=False,
        docs_enabled=False,
        allowed_hosts=["testserver"],
        cors_allowed_origins=[],
        hsts_enabled=True,
        auth_jwt_secret=("a-strong-production-secret-with-more-than-32-characters"),
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = create_app()

    with TestClient(application) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["strict-transport-security"] == ("max-age=31536000; includeSubDomains")


def test_app_uses_configured_api_v1_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        app_env="local",
        docs_enabled=True,
        allowed_hosts=["testserver"],
        cors_allowed_origins=[],
        hsts_enabled=False,
        api_v1_prefix="/custom/v1",
        auth_jwt_secret="local-test-secret",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = create_app()

    paths = application.openapi()["paths"]

    assert "/custom/v1/auth/me" in paths
    assert "/api/v1/auth/me" not in paths


def test_app_generates_request_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        app_env="local",
        docs_enabled=True,
        allowed_hosts=["testserver"],
        cors_allowed_origins=[],
        hsts_enabled=False,
        auth_jwt_secret="local-test-secret",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = create_app()

    with TestClient(application) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert response.headers["x-request-id"]


def test_app_preserves_incoming_request_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        app_env="local",
        docs_enabled=True,
        allowed_hosts=["testserver"],
        cors_allowed_origins=[],
        hsts_enabled=False,
        auth_jwt_secret="local-test-secret",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    application = create_app()

    request_id = "request-123"

    with TestClient(application) as client:
        response = client.get(
            "/health",
            headers={
                "X-Request-ID": request_id,
            },
        )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == request_id
