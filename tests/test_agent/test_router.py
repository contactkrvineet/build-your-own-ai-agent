"""Tests for the agent router."""

from __future__ import annotations

import pytest

from app.agent.router import RouteDecision, classify_query


class TestRouterKeywordHeuristics:
    """Fast-path keyword-based routing — no LLM calls."""

    def test_weather_routes_to_tool(self):
        result = classify_query("What's the weather in London?", use_llm=False)
        assert result == RouteDecision.TOOL

    def test_temperature_routes_to_tool(self):
        result = classify_query("What's the temperature in New York today?", use_llm=False)
        assert result == RouteDecision.TOOL

    def test_email_routes_to_tool(self):
        result = classify_query("Check my email inbox", use_llm=False)
        assert result == RouteDecision.TOOL

    def test_calendar_event_routes_to_tool(self):
        result = classify_query("What meetings do I have today?", use_llm=False)
        assert result == RouteDecision.TOOL

    def test_document_query_routes_to_rag(self):
        result = classify_query(
            "According to the document, what are Vineet's skills?",
            rag_enabled=True,
            use_llm=False,
        )
        assert result == RouteDecision.RAG

    def test_resume_routes_to_rag(self):
        result = classify_query(
            "Tell me about Vineet's experience from his resume",
            rag_enabled=True,
            use_llm=False,
        )
        assert result == RouteDecision.RAG

    def test_rag_disabled_falls_to_direct(self):
        result = classify_query(
            "What are Vineet's skills according to the document?",
            rag_enabled=False,
            use_llm=False,
        )
        assert result == RouteDecision.DIRECT

    def test_greeting_routes_direct(self):
        for greeting in ("hi", "hello", "hey", "thanks"):
            result = classify_query(greeting, use_llm=False)
            assert result == RouteDecision.DIRECT

    def test_general_question_routes_direct(self):
        result = classify_query(
            "Explain the difference between sync and async Python",
            use_llm=False,
        )
        assert result == RouteDecision.DIRECT


class TestRouterDecisionEnum:
    def test_enum_values(self):
        assert RouteDecision.RAG == "rag"
        assert RouteDecision.TOOL == "tool"
        assert RouteDecision.DIRECT == "direct"
