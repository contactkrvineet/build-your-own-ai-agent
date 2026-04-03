"""
LiteLLM-backed provider — supports ALL configured LLM providers
(OpenAI, Anthropic, Gemini, Groq, Ollama, HuggingFace) via a single
implementation.  Switching providers = change config.yaml only.

Also exposes a LangChain BaseChatModel subclass so the ReAct agent
and all LangChain chains work seamlessly with any provider.
"""

from __future__ import annotations

import os
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Type

from langchain_core.callbacks.manager import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse
from app.utils.logger import logger


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_litellm_messages(messages: List[LLMMessage]) -> List[Dict[str, str]]:
    return [{"role": m.role, "content": m.content} for m in messages]


def _lc_to_litellm_messages(messages: List[BaseMessage]) -> List[Dict[str, str]]:
    role_map = {
        HumanMessage: "user",
        AIMessage: "assistant",
        SystemMessage: "system",
    }
    result = []
    for msg in messages:
        role = role_map.get(type(msg), "user")
        result.append({"role": role, "content": str(msg.content)})
    return result


# ---------------------------------------------------------------------------
# Core provider (BaseLLMProvider implementation)
# ---------------------------------------------------------------------------

class LiteLLMProvider(BaseLLMProvider):
    """
    Unified provider using LiteLLM under the hood.
    Instantiate via app.llm.factory.create_llm_provider().
    """

    def __init__(
        self,
        model: str,
        provider: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        request_timeout: int = 60,
        max_retries: int = 3,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> None:
        self._model = model
        self._provider = provider
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = request_timeout
        self._max_retries = max_retries
        self._api_key = api_key
        self._api_base = api_base

        # Set env vars that LiteLLM reads automatically
        if api_key:
            self._set_api_key_env(provider, api_key)

    # ── BaseLLMProvider interface ─────────────────────────────────────────

    @property
    def provider_name(self) -> str:
        return self._provider

    @property
    def model_name(self) -> str:
        return self._model

    def chat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        import litellm

        litellm.drop_params = True

        kwargs = self._build_kwargs(temperature, max_tokens)
        response = litellm.completion(
            model=self._model,
            messages=_to_litellm_messages(messages),
            **kwargs,
        )
        return self._parse_response(response)

    async def achat(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        import litellm

        litellm.drop_params = True

        kwargs = self._build_kwargs(temperature, max_tokens)
        response = await litellm.acompletion(
            model=self._model,
            messages=_to_litellm_messages(messages),
            **kwargs,
        )
        return self._parse_response(response)

    def stream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Iterator[str]:
        import litellm

        litellm.drop_params = True

        kwargs = self._build_kwargs(temperature, max_tokens)
        response = litellm.completion(
            model=self._model,
            messages=_to_litellm_messages(messages),
            stream=True,
            **kwargs,
        )
        for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta

    async def astream(
        self,
        messages: List[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        import litellm

        litellm.drop_params = True

        kwargs = self._build_kwargs(temperature, max_tokens)
        response = await litellm.acompletion(
            model=self._model,
            messages=_to_litellm_messages(messages),
            stream=True,
            **kwargs,
        )
        async for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta

    def health_check(self) -> bool:
        try:
            self.chat([LLMMessage(role="user", content="ping")])
            return True
        except Exception as e:
            logger.warning(f"LLM health check failed ({self._provider}): {e}")
            return False

    # ── Private helpers ───────────────────────────────────────────────────

    def _build_kwargs(
        self, temperature: Optional[float], max_tokens: Optional[int]
    ) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "temperature": temperature if temperature is not None else self._temperature,
            "max_tokens": max_tokens if max_tokens is not None else self._max_tokens,
            "timeout": self._timeout,
            "num_retries": self._max_retries,
        }
        if self._api_base:
            kwargs["api_base"] = self._api_base
        return kwargs

    def _parse_response(self, response: Any) -> LLMResponse:
        choice = response.choices[0]
        usage = getattr(response, "usage", None)
        return LLMResponse(
            content=choice.message.content or "",
            model=getattr(response, "model", self._model),
            provider=self._provider,
            prompt_tokens=getattr(usage, "prompt_tokens", 0) if usage else 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) if usage else 0,
            total_tokens=getattr(usage, "total_tokens", 0) if usage else 0,
            finish_reason=choice.finish_reason or "stop",
            raw=response,
        )

    @staticmethod
    def _set_api_key_env(provider: str, api_key: str) -> None:
        env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "groq": "GROQ_API_KEY",
            "huggingface": "HUGGINGFACE_API_TOKEN",
        }
        env_var = env_map.get(provider)
        if env_var and api_key:
            os.environ.setdefault(env_var, api_key)


# ---------------------------------------------------------------------------
# LangChain-compatible ChatModel wrapper
# ---------------------------------------------------------------------------

class AskVineetChatModel(BaseChatModel):
    """
    LangChain BaseChatModel that delegates to LiteLLMProvider.
    Plug this into any LangChain chain, agent, or LCEL expression.
    """

    model: str
    provider: str
    temperature: float = 0.7
    max_tokens: int = 2048
    request_timeout: int = 60
    max_retries: int = 3
    api_key: Optional[str] = None
    api_base: Optional[str] = None

    # Internal — not a Pydantic field (use model_post_init or property)
    _llm_provider: Optional[LiteLLMProvider] = None

    def model_post_init(self, __context: Any) -> None:
        object.__setattr__(
            self,
            "_llm_provider",
            LiteLLMProvider(
                model=self.model,
                provider=self.provider,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                request_timeout=self.request_timeout,
                max_retries=self.max_retries,
                api_key=self.api_key,
                api_base=self.api_base,
            ),
        )

    @property
    def _llm_type(self) -> str:
        return f"askvineet-{self.provider}"

    # ── Sync ─────────────────────────────────────────────────────────────

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        lc_messages = [
            LLMMessage(role=r, content=c)
            for r, c in [
                (self._msg_role(m), str(m.content)) for m in messages
            ]
        ]
        resp = self._llm_provider.chat(lc_messages)  # type: ignore[union-attr]
        ai_msg = AIMessage(content=resp.content)
        return ChatResult(
            generations=[ChatGeneration(message=ai_msg)],
            llm_output={"model": resp.model, "usage": resp.total_tokens},
        )

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        import litellm

        litellm.drop_params = True

        litellm_msgs = _lc_to_litellm_messages(messages)
        response = litellm.completion(
            model=self.model,
            messages=litellm_msgs,
            stream=True,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                ai_chunk = AIMessage(content=delta)
                gen_chunk = ChatGenerationChunk(message=ai_chunk)
                if run_manager:
                    run_manager.on_llm_new_token(delta, chunk=gen_chunk)
                yield gen_chunk

    # ── Async ─────────────────────────────────────────────────────────────

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        lc_messages = [
            LLMMessage(role=self._msg_role(m), content=str(m.content))
            for m in messages
        ]
        resp = await self._llm_provider.achat(lc_messages)  # type: ignore[union-attr]
        ai_msg = AIMessage(content=resp.content)
        return ChatResult(generations=[ChatGeneration(message=ai_msg)])

    @staticmethod
    def _msg_role(msg: BaseMessage) -> str:
        if isinstance(msg, SystemMessage):
            return "system"
        if isinstance(msg, AIMessage):
            return "assistant"
        return "user"
