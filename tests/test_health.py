"""Tests for GET /health."""

from __future__ import annotations


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_body(client):
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert "version" in data


def test_health_version_format(client):
    version = client.get("/health").json()["version"]
    parts = version.split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)
