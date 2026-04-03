"""Tests for the LLM provider and factory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.llm.base import LLMMessage, LLMResponse


class TestLLMMessage:
    def test_user_message(self):
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_system_message(self):
        msg = LLMMessage(role="system", content="You are AskVineet.")
        assert msg.role == "system"


class TestLLMResponse:
    def test_default_fields(self):
        resp = LLMResponse(content="Answer", model="gpt-4o", provider="openai")
        assert resp.prompt_tokens == 0
        assert resp.completion_tokens == 0
        assert resp.finish_reason == "stop"
        assert resp.raw is None

    def test_token_counts(self):
        resp = LLMResponse(
            content="Hi", model="m", provider="p",
            prompt_tokens=10, completion_tokens=5, total_tokens=15
        )
        assert resp.total_tokens == 15


class TestLiteLLMProvider:
    """Unit tests for LiteLLMProvider — LiteLLM calls are mocked."""

    def _make_mock_response(self, content="Hello from mock"):
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = content
        resp.choices[0].finish_reason = "stop"
        resp.model = "mock-model"
        resp.usage = MagicMock(prompt_tokens=5, completion_tokens=10, total_tokens=15)
        return resp

    @patch("litellm.completion")
    def test_chat_returns_llm_response(self, mock_completion):
        mock_completion.return_value = self._make_mock_response("Test answer")

        from app.llm.litellm_wrapper import LiteLLMProvider

        provider = LiteLLMProvider(
            model="groq/llama3-8b-8192",
            provider="groq",
            api_key="dummy",
        )
        result = provider.chat([LLMMessage(role="user", content="Hi")])

        assert isinstance(result, LLMResponse)
        assert result.content == "Test answer"
        assert result.total_tokens == 15
        mock_completion.assert_called_once()

    @patch("litellm.completion")
    def test_chat_passes_temperature_and_max_tokens(self, mock_completion):
        mock_completion.return_value = self._make_mock_response()

        from app.llm.litellm_wrapper import LiteLLMProvider

        provider = LiteLLMProvider(
            model="groq/llama3-8b-8192",
            provider="groq",
            temperature=0.2,
            max_tokens=512,
            api_key="dummy",
        )
        provider.chat([LLMMessage(role="user", content="Test")])

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["temperature"] == 0.2
        assert call_kwargs["max_tokens"] == 512

    @patch("litellm.completion", side_effect=Exception("API unreachable"))
    def test_health_check_returns_false_on_error(self, mock_completion):
        from app.llm.litellm_wrapper import LiteLLMProvider

        provider = LiteLLMProvider(
            model="groq/llama3-8b-8192", provider="groq", api_key="dummy"
        )
        assert provider.health_check() is False


class TestLLMFactory:
    """Tests for the LLM factory."""

    def test_get_litellm_model_string_groq(self):
        from app.config.settings import Settings

        s = Settings(llm_provider="groq", llm_model="llama3-8b-8192")
        assert s.get_litellm_model_string() == "groq/llama3-8b-8192"

    def test_get_litellm_model_string_openai(self):
        from app.config.settings import Settings

        s = Settings(llm_provider="openai", llm_model="gpt-4o")
        assert s.get_litellm_model_string() == "gpt-4o"

    def test_get_litellm_model_string_ollama(self):
        from app.config.settings import Settings

        s = Settings(llm_provider="ollama", llm_model="llama3")
        assert s.get_litellm_model_string() == "ollama/llama3"

    def test_invalid_provider_raises(self):
        from app.config.settings import Settings
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            Settings(llm_provider="invalid_provider")
