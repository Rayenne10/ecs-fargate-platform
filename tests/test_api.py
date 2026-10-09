import json

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_and_release(monkeypatch):
    monkeypatch.setenv("APP_REVISION", "a" * 40)
    monkeypatch.setenv("APP_ENV", "aws-demo")
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}
    assert client.get("/api/info").json()["revision"] == "a" * 40


def test_capacity():
    result = client.post("/api/capacity", json={"task_count": 2}).json()
    assert result["total_vcpu"] == 0.5
    assert result["total_memory_gib"] == 1


def test_oversized_body_is_rejected():
    response = client.post("/api/capacity", content=b"x" * 16385)
    assert response.status_code == 413
    assert "x-request-id" in response.headers


@pytest.mark.parametrize(
    "body",
    [
        {"task_count": 0},
        {"task_count": 101},
        {"task_count": 2, "cpu_units": 1},
        {"task_count": 1, "unexpected": True},
    ],
)
def test_invalid_capacity(body):
    assert client.post("/api/capacity", json=body).status_code == 422


def test_request_id_and_security_headers():
    response = client.get("/", headers={"X-Request-ID": "interview-demo"})
    assert response.headers["x-request-id"] == "interview-demo"
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert client.get("/", headers={"X-Request-ID": "bad id"}).headers["x-request-id"] != "bad id"


def test_metrics_do_not_label_arbitrary_paths():
    client.get("/sensitive-unique-path?secret=do-not-log")
    text = client.get("/metrics").text
    assert 'route="unmatched"' in text
    assert "sensitive-unique-path" not in text
    assert "do-not-log" not in text


def test_static_assets_are_bounded():
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/assets/style.css").status_code == 200
    assert client.get("/assets/unknown.txt").status_code == 404


def test_json_logs_exclude_query_and_body():
    # Verify the log structure from a captured handler, not application internals.
    import logging

    from app.main import logger

    records = []

    class Capture(logging.Handler):
        def emit(self, record):
            records.append(json.loads(record.getMessage()))

    handler = Capture()
    logger.addHandler(handler)
    try:
        client.post(
            "/api/capacity?token=secret",
            json={"task_count": 2},
            headers={"x-request-id": "trace-123"},
        )
    finally:
        logger.removeHandler(handler)
    assert records[-1]["request_id"] == "trace-123"
    assert records[-1]["route"] == "/api/capacity"
    assert "secret" not in json.dumps(records)
