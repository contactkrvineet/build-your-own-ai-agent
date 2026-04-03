"""Tests for FastAPI chat endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestChatEndpointREST:
    def test_post_chat_returns_200(self, api_client: TestClient):
        resp = api_client.post("/chat/", json={"message": "Hello"})
        assert resp.status_code == 200

    def test_response_has_required_fields(self, api_client: TestClient):
        data = api_client.post("/chat/", json={"message": "Hi"}).json()
        assert "answer" in data
        assert "session_id" in data
        assert "route_used" in data
        assert "sources" in data

    def test_empty_message_rejected(self, api_client: TestClient):
        resp = api_client.post("/chat/", json={"message": ""})
        assert resp.status_code == 422  # Pydantic validation error

    def test_session_id_propagated(self, api_client: TestClient):
        data = api_client.post(
            "/chat/",
            json={"message": "Hello", "session_id": "my-session-abc"},
        ).json()
        # The mocked agent returns 'test-session-123' from conftest
        assert data["session_id"] is not None

    def test_message_too_long_rejected(self, api_client: TestClient):
        resp = api_client.post("/chat/", json={"message": "x" * 4001})
        assert resp.status_code == 422


class TestHealthEndpoint:
    def test_health_returns_ok(self, api_client: TestClient):
        resp = api_client.get("/health/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "agent" in data
        assert "version" in data


class TestHistoryEndpoint:
    def test_get_history_returns_200(self, api_client: TestClient):
        resp = api_client.get("/chat/history/some-session-id")
        assert resp.status_code == 200

    def test_history_has_messages_key(self, api_client: TestClient):
        data = api_client.get("/chat/history/some-session").json()
        assert "messages" in data
        assert "session_id" in data


class TestSessionDelete:
    def test_delete_session_returns_ok(self, api_client: TestClient):
        resp = api_client.delete("/chat/session/some-session")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cleared"
