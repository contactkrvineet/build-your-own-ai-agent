"""
Pydantic-based settings management.

Priority order (highest → lowest):
  1. Environment variables (.env file)
  2. config.yaml values
  3. Default values defined here

Secrets are ALWAYS read from environment variables — never from config.yaml.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).parent.parent.parent  # project root


def _load_yaml(path: Path) -> Dict[str, Any]:
    """Load config.yaml and return as dict (empty dict if file missing)."""
    if path.exists():
        with path.open("r") as f:
            return yaml.safe_load(f) or {}
    return {}


def _get(d: Dict, *keys: str, default: Any = None) -> Any:
    """Safe nested dict getter."""
    for key in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(key, default)
    return d


_yaml = _load_yaml(_ROOT / "config.yaml")


# ---------------------------------------------------------------------------
# Settings dataclass
# ---------------------------------------------------------------------------

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Agent ──────────────────────────────────────────────────────────────
    agent_name: str = Field(
        default_factory=lambda: _get(_yaml, "agent", "name", default="AskVineet")
    )
    agent_description: str = Field(
        default_factory=lambda: _get(_yaml, "agent", "description", default="")
    )
    agent_version: str = Field(
        default_factory=lambda: _get(_yaml, "agent", "version", default="1.0.0")
    )
    debug: bool = Field(
        default_factory=lambda: _get(_yaml, "agent", "debug", default=False)
    )

    # ── LLM ───────────────────────────────────────────────────────────────
    llm_provider: str = Field(
        default_factory=lambda: _get(_yaml, "llm", "provider", default="groq")
    )
    llm_model: str = Field(
        default_factory=lambda: _get(_yaml, "llm", "model", default="llama3-8b-8192")
    )
    llm_temperature: float = Field(
        default_factory=lambda: _get(_yaml, "llm", "temperature", default=0.7)
    )
    llm_max_tokens: int = Field(
        default_factory=lambda: _get(_yaml, "llm", "max_tokens", default=2048)
    )
    llm_streaming: bool = Field(
        default_factory=lambda: _get(_yaml, "llm", "streaming", default=True)
    )
    llm_request_timeout: int = Field(
        default_factory=lambda: _get(_yaml, "llm", "request_timeout", default=60)
    )
    llm_max_retries: int = Field(
        default_factory=lambda: _get(_yaml, "llm", "max_retries", default=3)
    )
    ollama_base_url: str = Field(
        default_factory=lambda: _get(
            _yaml, "llm", "ollama_base_url", default="http://localhost:11434"
        )
    )

    # ── LLM API Keys (from env only) ───────────────────────────────────────
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    groq_api_key: Optional[str] = Field(default=None)
    google_api_key: Optional[str] = Field(default=None)
    huggingface_api_token: Optional[str] = Field(default=None)

    # ── RAG ───────────────────────────────────────────────────────────────
    rag_enabled: bool = Field(
        default_factory=lambda: _get(_yaml, "rag", "enabled", default=True)
    )
    rag_documents_path: str = Field(
        default_factory=lambda: _get(_yaml, "rag", "documents_path", default="./documents")
    )
    rag_vector_store: str = Field(
        default_factory=lambda: _get(_yaml, "rag", "vector_store", default="chroma")
    )
    rag_vector_store_path: str = Field(
        default_factory=lambda: _get(
            _yaml, "rag", "vector_store_path", default="./data/vectorstore"
        )
    )
    rag_embedding_model: str = Field(
        default_factory=lambda: _get(
            _yaml, "rag", "embedding_model", default="all-MiniLM-L6-v2"
        )
    )
    rag_chunk_size: int = Field(
        default_factory=lambda: _get(_yaml, "rag", "chunk_size", default=1000)
    )
    rag_chunk_overlap: int = Field(
        default_factory=lambda: _get(_yaml, "rag", "chunk_overlap", default=200)
    )
    rag_top_k: int = Field(
        default_factory=lambda: _get(_yaml, "rag", "top_k", default=5)
    )
    rag_ocr_enabled: bool = Field(
        default_factory=lambda: _get(_yaml, "rag", "ocr_enabled", default=False)
    )
    rag_ocr_language: str = Field(
        default_factory=lambda: _get(_yaml, "rag", "ocr_language", default="eng")
    )
    rag_hot_reload: bool = Field(
        default_factory=lambda: _get(_yaml, "rag", "hot_reload", default=True)
    )
    rag_collection_name: str = Field(
        default_factory=lambda: _get(
            _yaml, "rag", "collection_name", default="askvineet_docs"
        )
    )

    # ── Tools ─────────────────────────────────────────────────────────────
    tool_weather_enabled: bool = Field(
        default_factory=lambda: _get(_yaml, "tools", "weather", "enabled", default=True)
    )
    tool_weather_units: str = Field(
        default_factory=lambda: _get(_yaml, "tools", "weather", "units", default="metric")
    )
    openweathermap_api_key: Optional[str] = Field(default=None)

    tool_gmail_enabled: bool = Field(
        default_factory=lambda: _get(_yaml, "tools", "gmail", "enabled", default=False)
    )
    tool_gmail_max_results: int = Field(
        default_factory=lambda: _get(_yaml, "tools", "gmail", "max_results", default=10)
    )

    tool_calendar_enabled: bool = Field(
        default_factory=lambda: _get(
            _yaml, "tools", "calendar", "enabled", default=False
        )
    )
    tool_calendar_max_results: int = Field(
        default_factory=lambda: _get(
            _yaml, "tools", "calendar", "max_results", default=10
        )
    )

    google_credentials_file: Optional[str] = Field(default="./credentials.json")
    google_token_file: Optional[str] = Field(default="./data/google_token.json")

    tool_custom_api_enabled: bool = Field(
        default_factory=lambda: _get(
            _yaml, "tools", "custom_api", "enabled", default=False
        )
    )
    custom_api_endpoint: Optional[str] = Field(default=None)
    custom_api_key: Optional[str] = Field(default=None)
    custom_api_header_name: Optional[str] = Field(default=None)
    custom_api_header_value: Optional[str] = Field(default=None)

    # ── Workflows ─────────────────────────────────────────────────────────
    scheduler_enabled: bool = Field(
        default_factory=lambda: _get(
            _yaml, "workflows", "scheduler", "enabled", default=True
        )
    )
    scheduler_timezone: str = Field(
        default_factory=lambda: _get(
            _yaml, "workflows", "scheduler", "timezone", default="UTC"
        )
    )
    file_watcher_enabled: bool = Field(
        default_factory=lambda: _get(
            _yaml, "workflows", "file_watcher", "enabled", default=True
        )
    )

    # ── API ───────────────────────────────────────────────────────────────
    api_host: str = Field(
        default_factory=lambda: _get(_yaml, "api", "host", default="0.0.0.0")
    )
    api_port: int = Field(
        default_factory=lambda: _get(_yaml, "api", "port", default=8000)
    )
    secret_key: str = Field(default="change-me-to-a-random-32-char-string")

    # ── Logging ───────────────────────────────────────────────────────────
    log_level: str = Field(
        default_factory=lambda: _get(_yaml, "logging", "level", default="INFO")
    )
    log_file: str = Field(
        default_factory=lambda: _get(
            _yaml, "logging", "file", default="./data/logs/askvineet.log"
        )
    )

    # ── Memory ────────────────────────────────────────────────────────────
    memory_window_size: int = Field(
        default_factory=lambda: _get(
            _yaml, "memory", "short_term", "window_size", default=10
        )
    )
    memory_long_term_enabled: bool = Field(
        default_factory=lambda: _get(
            _yaml, "memory", "long_term", "enabled", default=True
        )
    )

    # ── UI ────────────────────────────────────────────────────────────────
    ui_title: str = Field(
        default_factory=lambda: _get(_yaml, "ui", "title", default="AskVineet")
    )
    ui_show_sources: bool = Field(
        default_factory=lambda: _get(_yaml, "ui", "show_sources", default=True)
    )
    ui_show_agent_thought: bool = Field(
        default_factory=lambda: _get(_yaml, "ui", "show_agent_thought", default=False)
    )

    @field_validator("llm_provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        allowed = {"openai", "anthropic", "gemini", "groq", "ollama", "huggingface"}
        if v not in allowed:
            raise ValueError(f"llm_provider must be one of {allowed}, got '{v}'")
        return v

    @field_validator("rag_vector_store")
    @classmethod
    def validate_vector_store(cls, v: str) -> str:
        allowed = {"chroma", "faiss"}
        if v not in allowed:
            raise ValueError(f"rag_vector_store must be one of {allowed}, got '{v}'")
        return v

    def get_litellm_model_string(self) -> str:
        """
        Return the LiteLLM model string for the configured provider.
        LiteLLM format: '<provider>/<model>' for most providers.
        """
        provider_map = {
            "openai": self.llm_model,           # e.g. gpt-4o (no prefix needed)
            "anthropic": self.llm_model,        # e.g. claude-3-5-sonnet-20241022
            "gemini": f"gemini/{self.llm_model}",
            "groq": f"groq/{self.llm_model}",
            "ollama": f"ollama/{self.llm_model}",
            "huggingface": f"huggingface/{self.llm_model}",
        }
        return provider_map.get(self.llm_provider, self.llm_model)

    def get_api_key_for_provider(self) -> Optional[str]:
        """Return the correct API key for the active LLM provider."""
        key_map = {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "gemini": self.google_api_key,
            "groq": self.groq_api_key,
            "ollama": None,
            "huggingface": self.huggingface_api_token,
        }
        return key_map.get(self.llm_provider)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings singleton."""
    return Settings()
