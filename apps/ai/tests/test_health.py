from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_reports_service_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"service": "ai", "status": "ok"}
