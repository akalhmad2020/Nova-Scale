import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.integration
def test_readiness_checks_postgres() -> None:
    with TestClient(app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
