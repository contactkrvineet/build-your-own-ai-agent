"""
LLM Factory — creates the correct provider from config.yaml / .env settings.

Usage:
    from app.llm.factory import create_llm_provider, create_langchain_llm

    # Low-level provider (direct use)
    provider = create_llm_provider()

    # LangChain-compatible chat model (use in chains / agents)
    llm = create_langchain_llm()
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from app.config.settings import Settings, get_settings
from app.llm.base import BaseLLMProvider
from app.llm.litellm_wrapper import AskVineetChatModel, LiteLLMProvider
from app.utils.logger import logger


def create_llm_provider(settings: Optional[Settings] = None) -> BaseLLMProvider:
    """
    Instantiate the LiteLLMProvider from configuration.
    API keys are read from environment variables via Settings.
    """
    s = settings or get_settings()

    model_string = s.get_litellm_model_string()
    api_key = s.get_api_key_for_provider()
    api_base = s.ollama_base_url if s.llm_provider == "ollama" else None

    logger.info(
        f"Creating LLM provider: provider={s.llm_provider}  "
        f"model={model_string}  temp={s.llm_temperature}"
    )

    return LiteLLMProvider(
        model=model_string,
        provider=s.llm_provider,
        temperature=s.llm_temperature,
        max_tokens=s.llm_max_tokens,
        request_timeout=s.llm_request_timeout,
        max_retries=s.llm_max_retries,
        api_key=api_key,
        api_base=api_base,
    )


def create_langchain_llm(settings: Optional[Settings] = None) -> AskVineetChatModel:
    """
    Instantiate the LangChain-compatible ChatModel from configuration.
    Use this in LangChain chains, agents, and LCEL expressions.
    """
    s = settings or get_settings()

    model_string = s.get_litellm_model_string()
    api_key = s.get_api_key_for_provider()
    api_base = s.ollama_base_url if s.llm_provider == "ollama" else None

    logger.info(f"Creating LangChain ChatModel: {model_string}")

    return AskVineetChatModel(
        model=model_string,
        provider=s.llm_provider,
        temperature=s.llm_temperature,
        max_tokens=s.llm_max_tokens,
        request_timeout=s.llm_request_timeout,
        max_retries=s.llm_max_retries,
        api_key=api_key,
        api_base=api_base,
    )


@lru_cache(maxsize=1)
def get_cached_langchain_llm() -> AskVineetChatModel:
    """Cached singleton — use in long-running services."""
    return create_langchain_llm()
