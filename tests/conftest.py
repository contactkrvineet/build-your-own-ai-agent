"""
Shared pytest fixtures.

All tests can use these via dependency injection (no import needed).
Run:  pytest tests/ -v --cov=app --cov-report=term-missing
"""

from __future__ import annotations

import os
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Environment — use dummy keys so tests never hit real APIs
# ---------------------------------------------------------------------------

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy-key-for-unit-tests")
os.environ.setdefault("GROQ_API_KEY", "gsk_test_dummy_key")
os.environ.setdefault("OPENWEATHERMAP_API_KEY", "owm_test_dummy")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_settings():
    """Settings instance with test overrides."""
    from app.config.settings import Settings

    return Settings(
        llm_provider="groq",
        llm_model="llama3-8b-8192",
        llm_temperature=0.0,  # Deterministic for testing
        rag_enabled=False,     # No real vector store in unit tests
        tool_weather_enabled=False,
        tool_gmail_enabled=False,
        tool_calendar_enabled=False,
        tool_custom_api_enabled=False,
        scheduler_enabled=False,
        file_watcher_enabled=False,
        debug=True,
    )


@pytest.fixture
def mock_llm_response():
    """Factory fixture: return a mock LLM chat response."""

    def _factory(content: str = "Test response from mock LLM"):
        from app.llm.base import LLMResponse

        return LLMResponse(
            content=content,
            model="mock-model",
            provider="mock",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )

    return _factory


@pytest.fixture
def mock_llm_provider(mock_llm_response):
    """Fully mocked LiteLLMProvider."""
    from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

    provider = MagicMock(spec=BaseLLMProvider)
    provider.provider_name = "mock"
    provider.model_name = "mock-model"
    provider.chat.return_value = mock_llm_response()
    provider.achat = AsyncMock(return_value=mock_llm_response())
    provider.health_check.return_value = True
    return provider


@pytest.fixture
def mock_langchain_llm():
    """Mocked LangChain chat model that returns a fixed response."""
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult

    llm = MagicMock()
    llm.invoke.return_value = AIMessage(content="Mocked LLM answer")
    llm._generate.return_value = ChatResult(
        generations=[ChatGeneration(message=AIMessage(content="Mocked LLM answer"))]
    )
    return llm


@pytest.fixture
def mock_vector_store():
    """Mocked VectorStore."""
    from langchain_core.documents import Document

    store = MagicMock()
    store.similarity_search.return_value = [
        Document(
            page_content="Vineet Kumar is an SDET Manager with 10+ years experience.",
            metadata={"source": "resume.pdf", "filename": "resume.pdf", "page": 1},
        )
    ]
    store.add_documents.return_value = None
    return store


@pytest.fixture
def sample_documents():
    """Sample LangChain Documents for RAG tests."""
    from langchain_core.documents import Document

    return [
        Document(
            page_content="Vineet Kumar is an experienced SDET Manager specialising in AI and automation.",
            metadata={"source": "bio.txt", "filename": "bio.txt"},
        ),
        Document(
            page_content="Skills: Python, LangChain, Selenium, Pytest, AWS, CI/CD.",
            metadata={"source": "skills.txt", "filename": "skills.txt"},
        ),
        Document(
            page_content="Projects: AskVineet AI Agent, Test automation framework, API testing suite.",
            metadata={"source": "projects.txt", "filename": "projects.txt"},
        ),
    ]


@pytest.fixture
def api_client():
    """FastAPI test client with mocked agent."""
    with patch("app.agent.core.get_agent") as mock_get_agent:
        from app.agent.core import AgentResponse

        agent = MagicMock()
        agent.achat = AsyncMock(
            return_value=AgentResponse(
                answer="Hello! I'm AskVineet.",
                route_used="direct",
                session_id="test-session-123",
            )
        )
        agent.get_history.return_value = []
        agent.clear_session.return_value = None
        mock_get_agent.return_value = agent

        from app.main import app

        with TestClient(app) as client:
            yield client


@pytest.fixture
def tmp_documents_dir(tmp_path):
    """Temporary documents directory with sample files."""
    docs_dir = tmp_path / "documents"
    docs_dir.mkdir()
    (docs_dir / "sample.txt").write_text(
        "Vineet Kumar — SDET Manager and AI Engineer."
    )
    (docs_dir / "skills.md").write_text(
        "# Skills\n- Python\n- LangChain\n- Pytest\n- FastAPI"
    )
    return docs_dir
