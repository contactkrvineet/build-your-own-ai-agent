"""
Abstract LLM interface.

All LLM providers implement BaseLLMProvider.
Callers program against this interface — swapping providers = zero code change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Iterator, List, Optional


@dataclass
class LLMMessage:
    """A single message in a conversation."""

    role: str   # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """Standardised response envelope returned by all providers."""

    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "stop"
    raw: Optional[object] = field(default=None, repr=False)


class BaseLLMProvider(ABC):
    """
    Abstract base for every LLM provider.

    Concrete implementations live in app/llm/litellm_wrapper.py.
    The LangChain–compatible chat model wraps the same provider
    so agent tools continue to work.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name, e.g. 'groq'."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model identifier passed to the API."""

    @abstractmethod
    def chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Synchronous chat completion."""

    @abstractmethod
    async def achat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Asynchronous chat completion."""

    @abstractmethod
    def stream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        """Synchronous streaming — yields token strings."""

    @abstractmethod
    async def astream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """Asynchronous streaming — yields token strings."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the provider is reachable and configured correctly."""
