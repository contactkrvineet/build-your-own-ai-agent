"""Tests for the agent core (routing + response structure)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.agent.core import AgentResponse, AskVineetAgent


class TestAgentResponse:
    """AgentResponse dataclass contract."""

    def test_minimal_response(self):
        resp = AgentResponse(answer="Hello", route_used="direct", session_id="s1")
        assert resp.answer == "Hello"
        assert resp.route_used == "direct"
        assert resp.sources == []
        assert resp.tool_calls == []
        assert resp.error is None

    def test_rag_response_has_sources(self):
        resp = AgentResponse(
            answer="Based on the document...",
            route_used="rag",
            session_id="s2",
            sources=[{"source": "file.pdf", "filename": "file.pdf", "page": 1, "excerpt": "text"}],
        )
        assert len(resp.sources) == 1
        assert resp.sources[0]["filename"] == "file.pdf"

    def test_tool_response_has_tool_calls(self):
        resp = AgentResponse(
            answer="The weather is 22°C",
            route_used="tool",
            session_id="s3",
            tool_calls=["get_weather"],
        )
        assert "get_weather" in resp.tool_calls


class TestAskVineetAgent:
    """AskVineetAgent initialisation and routing."""

    @patch("app.agent.core._load_enabled_tools", return_value=[])
    @patch("app.agent.core.create_langchain_llm")
    @patch("app.agent.core.build_rag_pipeline", side_effect=Exception("no docs"))
    def test_initialise_degrades_gracefully_without_rag(
        self, mock_rag, mock_llm, mock_tools
    ):
        """Agent should still start even if RAG pipeline fails."""
        mock_llm.return_value = MagicMock()
        agent = AskVineetAgent()
        agent.initialise()
        assert agent._initialised is True
        assert agent._rag_chain is None  # RAG failed but agent is alive

    @patch("app.agent.core._load_enabled_tools", return_value=[])
    @patch("app.agent.core.create_langchain_llm")
    @patch("app.agent.core.build_rag_pipeline", side_effect=Exception("no docs"))
    def test_chat_returns_response_object(self, mock_rag, mock_llm, mock_tools):
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = MagicMock(content="Direct answer")
        mock_llm.return_value = mock_llm_instance

        agent = AskVineetAgent()
        agent.initialise()

        resp = agent.chat("What is LangChain?")
        assert isinstance(resp, AgentResponse)
        assert resp.answer
        assert resp.session_id

    @patch("app.agent.core._load_enabled_tools", return_value=[])
    @patch("app.agent.core.create_langchain_llm")
    @patch("app.agent.core.build_rag_pipeline", side_effect=Exception("no docs"))
    def test_session_continuity(self, mock_rag, mock_llm, mock_tools):
        """Same session_id should give the same session back."""
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value = MagicMock(content="Hi!")
        mock_llm.return_value = mock_llm_instance

        agent = AskVineetAgent()
        agent.initialise()

        r1 = agent.chat("Hello", session_id="fixed-session")
        r2 = agent.chat("How are you?", session_id="fixed-session")

        assert r1.session_id == "fixed-session"
        assert r2.session_id == "fixed-session"

    @patch("app.agent.core._load_enabled_tools", return_value=[])
    @patch("app.agent.core.create_langchain_llm")
    @patch("app.agent.core.build_rag_pipeline", side_effect=Exception("no docs"))
    def test_clear_session(self, mock_rag, mock_llm, mock_tools):
        mock_llm.return_value = MagicMock()
        agent = AskVineetAgent()
        agent.initialise()
        agent.chat("Hi", session_id="del-session")
        agent.clear_session("del-session")
        # History should be empty after clear
        history = agent.get_history("del-session")
        assert history == []
