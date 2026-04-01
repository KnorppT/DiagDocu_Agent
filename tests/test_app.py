"""Tests for the FastAPI GitHub Copilot Extension server."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

from agent.app import app, _get_last_user_message, _sse_chunk

DFC_NAME = "DFC_rbe_CddUTnet_UTnet1Plaus"


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestGetLastUserMessage:
    def test_returns_text_from_string_content(self):
        messages = [{"role": "user", "content": "Hello"}]
        assert _get_last_user_message(messages) == "Hello"

    def test_returns_last_user_message(self):
        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Reply"},
            {"role": "user", "content": "Second"},
        ]
        assert _get_last_user_message(messages) == "Second"

    def test_handles_structured_content(self):
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Structured content"}],
            }
        ]
        assert _get_last_user_message(messages) == "Structured content"

    def test_returns_empty_string_for_no_user_messages(self):
        messages = [{"role": "assistant", "content": "Hello"}]
        assert _get_last_user_message(messages) == ""

    def test_returns_empty_string_for_empty_list(self):
        assert _get_last_user_message([]) == ""


class TestSseChunk:
    def test_starts_with_data_prefix(self):
        chunk = _sse_chunk("Hello")
        assert chunk.startswith("data: ")

    def test_ends_with_double_newline(self):
        chunk = _sse_chunk("Hello")
        assert chunk.endswith("\n\n")

    def test_contains_content(self):
        chunk = _sse_chunk("Hello world")
        assert "Hello world" in chunk

    def test_finish_reason_included_when_provided(self):
        chunk = _sse_chunk("", finish_reason="stop")
        assert "stop" in chunk


# ---------------------------------------------------------------------------
# Server endpoint tests (synchronous TestClient)
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_returns_200(self):
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200

    def test_returns_ok_status(self):
        client = TestClient(app)
        response = client.get("/")
        data = response.json()
        assert data["status"] == "ok"
        assert data["agent"] == "DiagDocu"


class TestCopilotChatEndpoint:
    def _post(self, messages: list, headers: dict | None = None):
        client = TestClient(app)
        return client.post(
            "/",
            json={"messages": messages},
            headers=headers or {},
        )

    def test_returns_200(self):
        response = self._post(
            [{"role": "user", "content": f"Erstelle DiagDocu für {DFC_NAME}"}]
        )
        assert response.status_code == 200

    def test_response_is_event_stream(self):
        response = self._post(
            [{"role": "user", "content": f"Erstelle DiagDocu für {DFC_NAME}"}]
        )
        assert "text/event-stream" in response.headers["content-type"]

    def test_response_contains_dfc_name(self):
        response = self._post(
            [{"role": "user", "content": f"Erstelle DiagDocu für {DFC_NAME}"}]
        )
        assert DFC_NAME in response.text

    def test_no_dfc_name_returns_help_message(self):
        response = self._post([{"role": "user", "content": "Hallo"}])
        assert response.status_code == 200
        # Should contain guidance about providing a DFC name
        body = response.text
        assert "DFC" in body

    def test_empty_messages_returns_help(self):
        response = self._post([])
        assert response.status_code == 200

    def test_structured_content_message(self):
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Erstelle DiagDocu für {DFC_NAME}"}
                ],
            }
        ]
        response = self._post(messages)
        assert response.status_code == 200
        assert DFC_NAME in response.text
