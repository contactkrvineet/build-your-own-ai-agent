"""
Abstract base for all AskVineet tools.

Every tool is also a LangChain BaseTool so it can be plugged directly
into the ReAct agent without any adapter code.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel


class AskVineetBaseTool(BaseTool):
    """
    Base class for all AskVineet tools.

    Subclasses must implement:
        - name: str         — unique snake_case identifier
        - description: str  — what the tool does (shown to the LLM)
        - _run(...)         — synchronous execution logic
        - args_schema       — Pydantic model describing tool inputs

    Optional:
        - _arun(...)        — async execution (defaults to running _run in thread)
        - is_enabled()      — whether the tool should be loaded (reads config)
    """

    @classmethod
    def is_enabled(cls) -> bool:
        """Override to check config/env before loading."""
        return True

    def _run(self, *args: Any, **kwargs: Any) -> str:  # type: ignore[override]
        raise NotImplementedError

    async def _arun(self, *args: Any, **kwargs: Any) -> str:  # type: ignore[override]
        """Default async implementation: run sync version in thread pool."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self._run(*args, **kwargs))
