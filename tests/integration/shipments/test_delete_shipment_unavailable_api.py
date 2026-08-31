from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.integration
def test_delete_shipment_endpoint_is_not_available() -> None:
    tenant_id = uuid4()
    shipment_id = uuid4()

    with TestClient(app) as client:
        response = client.delete(
            f"/api/v1/tenants/{tenant_id}/shipments/{shipment_id}",
        )

    assert response.status_code == 405
