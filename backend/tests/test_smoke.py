"""Phase 0 smoke tests: the app boots and the health endpoint responds.

Also proves the verification mechanism (pytest) works before heavier phases.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_responds() -> None:
    client = TestClient(create_app())
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"] == "CLARA"
