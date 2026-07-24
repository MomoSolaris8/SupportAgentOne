from fastapi.testclient import TestClient

from supportagent.api import app

client = TestClient(app)


def test_models_endpoint_returns_model_catalog_and_request_id():
    response = client.get("/models")

    assert response.status_code == 200
    assert "models" in response.json()
    assert response.headers["X-Request-ID"]


def test_ask_requires_authentication():
    response = client.post(
        "/ask",
        json={"question": "Wie funktioniert das?"},
    )

    assert response.status_code == 401
    assert response.headers["X-Request-ID"]
