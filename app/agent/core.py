"""
AskVineet Agent Core — main entry point for all agent interactions.

Architecture:
  User message
    → Router (classify: rag / tool / direct)
    → RAG chain          (for document questions)
    → ReAct AgentExecutor (for tool-using questions)
    → Direct LLM chain   (for everything else)
    → Response + updated memory

The same AskVineetAgent instance is reused across requests within a process.
Per-user state is stored in session memory (app/agent/memory.py).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool
from langchain_core.vectorstores import VectorStore

from app.agent.memory import clear_session, get_session_history, get_session_memory
from app.agent.prompts import REACT_PROMPT_TEMPLATE, get_system_prompt
from app.agent.router import RouteDecision, classify_query
from app.config.settings import get_settings
from app.llm.factory import create_langchain_llm
from app.utils.logger import logger


# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------

@dataclass
class AgentResponse:
    """Structured response returned by the agent."""

    answer: str
    route_used: str                           # "rag" | "tool" | "direct"
    session_id: str
    sources: List[Dict[str, Any]] = field(default_factory=list)  # RAG source docs
    tool_calls: List[str] = field(default_factory=list)          # Tools invoked
    tokens_used: int = 0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class AskVineetAgent:
    """
    The main AskVineet agent.

    Usage:
        agent = AskVineetAgent()
        agent.initialise()          # build RAG pipeline, load tools
        response = agent.chat("What's the weather in London?", session_id="abc")
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._llm = None
        self._tools: List[BaseTool] = []
        self._vector_store: Optional[VectorStore] = None
        self._rag_chain = None
        self._react_executor: Optional[AgentExecutor] = None
        self._initialised = False

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def initialise(self) -> None:
        """Build all components. Call once at startup."""
        if self._initialised:
            return

        logger.info("Initialising AskVineet agent...")

        # LLM
        self._llm = create_langchain_llm()

        # Tools
        self._tools = _load_enabled_tools()
        logger.info(f"Loaded {len(self._tools)} tool(s): {[t.name for t in self._tools]}")

        # RAG pipeline — deferred to first query to reduce startup memory
        # (embedding model ~300MB, too heavy for Render free tier at boot)
        if self._settings.rag_enabled:
            logger.info("RAG enabled — pipeline will load on first RAG query")

        # ReAct agent (only if tools are available)
        if self._tools:
            self._build_react_executor()

        self._initialised = True
        logger.info("AskVineet agent ready.")

    def _build_rag_pipeline(self) -> None:
        try:
            from app.rag.retriever import build_rag_pipeline

            self._vector_store, self._rag_chain = build_rag_pipeline()
        except Exception as e:
            logger.error(f"RAG pipeline failed to initialise: {e}")

    def _build_react_executor(self) -> None:
        prompt = PromptTemplate.from_template(REACT_PROMPT_TEMPLATE).partial(
            system_prompt=get_system_prompt()
        )
        react_agent = create_react_agent(
            llm=self._llm,
            tools=self._tools,
            prompt=prompt,
        )
        self._react_executor = AgentExecutor(
            agent=react_agent,
            tools=self._tools,
            verbose=self._settings.debug,
            handle_parsing_errors=True,
            max_iterations=8,
            max_execution_time=60,
        )

    # ── Public API ────────────────────────────────────────────────────────

    def chat(self, message: str, session_id: Optional[str] = None) -> AgentResponse:
        """
        Synchronous chat entry point.

        Args:
            message:    User's input message.
            session_id: Identifier for conversation continuity (creates new if None).

        Returns:
            AgentResponse with answer, route info, and sources.
        """
        if not self._initialised:
            self.initialise()

        sid, memory = get_session_memory(session_id)

        # Classify query
        tool_names = [t.name for t in self._tools]
        route = classify_query(
            query=message,
            rag_enabled=self._settings.rag_enabled,
            available_tools=tool_names,
        )

        logger.info(f"[{sid}] Route: {route.value} | Query: '{message[:80]}'")

        try:
            if route == RouteDecision.RAG:
                return self._handle_rag(message, sid, memory)
            elif route == RouteDecision.TOOL and self._react_executor:
                return self._handle_tool(message, sid, memory)
            else:
                return self._handle_direct(message, sid, memory)
        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            return AgentResponse(
                answer=f"I encountered an error: {str(e)}",
                route_used=route.value,
                session_id=sid,
                error=str(e),
            )

    async def achat(
        self, message: str, session_id: Optional[str] = None
    ) -> AgentResponse:
        """Async version of chat()."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.chat(message, session_id))

    def get_history(self, session_id: str) -> List[Dict[str, str]]:
        return get_session_history(session_id)

    def clear_session(self, session_id: str) -> None:
        clear_session(session_id)

    def reload_documents(self) -> None:
        """Hot-reload: rebuild the RAG pipeline from scratch."""
        logger.info("Hot-reloading document store...")
        self._build_rag_pipeline()

    def add_document(self, file_path: str) -> None:
        """Hot-add a single document to the existing vector store."""
        if not self._vector_store:
            logger.warning("Vector store not initialised — rebuilding.")
            self._build_rag_pipeline()
            return

        from app.rag.retriever import add_new_document_to_store

        add_new_document_to_store(file_path, self._vector_store)

    # ── Route handlers ────────────────────────────────────────────────────

    def _handle_rag(self, message: str, sid: str, memory) -> AgentResponse:
        # Lazy-build RAG pipeline on first RAG query (saves startup memory)
        if not self._rag_chain and self._settings.rag_enabled:
            self._build_rag_pipeline()

        if not self._rag_chain:
            return self._handle_direct(message, sid, memory)

        chat_history = memory.chat_memory.messages
        result = self._rag_chain.invoke({"query": message})

        answer = result.get("result", "I couldn't find a relevant answer in the documents.")
        sources = [
            {
                "source": doc.metadata.get("source", "unknown"),
                "filename": doc.metadata.get("filename", ""),
                "page": doc.metadata.get("page", ""),
                "excerpt": doc.page_content[:300],
            }
            for doc in result.get("source_documents", [])
        ]

        # Update memory
        memory.save_context({"input": message}, {"output": answer})

        return AgentResponse(
            answer=answer,
            route_used="rag",
            session_id=sid,
            sources=sources,
        )

    def _handle_tool(self, message: str, sid: str, memory) -> AgentResponse:
        chat_history = memory.chat_memory.messages

        result = self._react_executor.invoke(
            {
                "input": message,
                "chat_history": chat_history,
            }
        )

        answer = result.get("output", "I couldn't complete the task.")
        intermediate = result.get("intermediate_steps", [])
        tool_calls = [step[0].tool for step in intermediate if step]

        memory.save_context({"input": message}, {"output": answer})

        return AgentResponse(
            answer=answer,
            route_used="tool",
            session_id=sid,
            tool_calls=tool_calls,
        )

    def _handle_direct(self, message: str, sid: str, memory) -> AgentResponse:
        chat_history = memory.chat_memory.messages
        messages = [SystemMessage(content=get_system_prompt())]
        messages.extend(chat_history)
        messages.append(HumanMessage(content=message))

        response = self._llm.invoke(messages)
        answer = response.content

        memory.save_context({"input": message}, {"output": answer})

        return AgentResponse(
            answer=answer,
            route_used="direct",
            session_id=sid,
        )


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_agent_instance: Optional[AskVineetAgent] = None


def get_agent() -> AskVineetAgent:
    """Return the process-level singleton agent (lazy initialised)."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = AskVineetAgent()
        _agent_instance.initialise()
    return _agent_instance


# ---------------------------------------------------------------------------
# Tool loader
# ---------------------------------------------------------------------------

def _load_enabled_tools() -> List[BaseTool]:
    """Dynamically load only the tools that are enabled in config."""
    tools: List[BaseTool] = []

    tool_classes = []

    try:
        from app.tools.weather import WeatherTool
        tool_classes.append(WeatherTool)
    except ImportError:
        pass

    try:
        from app.tools.gmail import GmailTool
        tool_classes.append(GmailTool)
    except ImportError:
        pass

    try:
        from app.tools.calendar_tool import CalendarTool
        tool_classes.append(CalendarTool)
    except ImportError:
        pass

    try:
        from app.tools.custom_api import CustomAPITool
        tool_classes.append(CustomAPITool)
    except ImportError:
        pass

    for cls in tool_classes:
        if cls.is_enabled():
            tools.append(cls())

    return tools
