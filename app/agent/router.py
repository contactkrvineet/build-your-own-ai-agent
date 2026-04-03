"""
Agent router — classifies each user query and directs it to the
appropriate handler:

  "rag"    → question likely answerable from documents
  "tool"   → needs a live API call (weather, gmail, calendar, etc.)
  "direct" → general conversation / knowledge question

Uses a lightweight LLM call with a structured prompt to classify,
with keyword-based heuristics as a fast pre-filter.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import List

from langchain_core.messages import HumanMessage, SystemMessage

from app.utils.logger import logger


class RouteDecision(str, Enum):
    RAG = "rag"
    TOOL = "tool"
    DIRECT = "direct"


# Keyword heuristics (applied before the LLM classifier to save tokens)
_TOOL_KEYWORDS = re.compile(
    r"\b(weather|temperature|rain|forecast|email|gmail|inbox|calendar|"
    r"meeting|event|schedule|appointment|api|fetch|get data)\b",
    re.IGNORECASE,
)

_RAG_KEYWORDS = re.compile(
    r"\b(document|file|pdf|according to|based on|in the|you have|vineet|"
    r"resume|cv|portfolio|experience|skills|project)\b",
    re.IGNORECASE,
)

_CLASSIFIER_PROMPT = """You are a routing classifier for an AI agent.
Classify the user's message into EXACTLY one of these categories:

  rag    — the user is asking about documents, files, the agent owner (Vineet Kumar),
           his portfolio, resume, experience, or any stored knowledge.
  tool   — the user wants live data: weather, emails, calendar, external API.
  direct — general knowledge, greetings, factual questions, coding help, etc.

Reply with ONLY the category word: rag | tool | direct
No explanation. No punctuation."""


def classify_query(
    query: str,
    rag_enabled: bool = True,
    available_tools: List[str] | None = None,
    use_llm: bool = True,
) -> RouteDecision:
    """
    Classify a query and return a RouteDecision.

    Args:
        query:           The user's message.
        rag_enabled:     Whether RAG pipeline is active.
        available_tools: Names of loaded tools (to validate tool routing).
        use_llm:         Use LLM classification (set False in tests/low-latency mode).
    """
    q_lower = query.lower().strip()

    # Fast path: greetings / trivial
    if len(q_lower) < 15 and any(
        q_lower.startswith(w) for w in ("hi", "hello", "hey", "thanks", "ok", "bye")
    ):
        return RouteDecision.DIRECT

    # Keyword heuristics
    if _TOOL_KEYWORDS.search(query):
        logger.debug(f"Router: keyword match → tool (query: '{query[:60]}')")
        return RouteDecision.TOOL

    if rag_enabled and _RAG_KEYWORDS.search(query):
        logger.debug(f"Router: keyword match → rag (query: '{query[:60]}')")
        return RouteDecision.RAG

    # LLM-based classification
    if use_llm:
        decision = _llm_classify(query)
        if decision == RouteDecision.RAG and not rag_enabled:
            decision = RouteDecision.DIRECT
        logger.debug(f"Router: LLM decision → {decision} (query: '{query[:60]}')")
        return decision

    return RouteDecision.DIRECT


def _llm_classify(query: str) -> RouteDecision:
    """Call the LLM classifier. Returns DIRECT on any failure."""
    try:
        from app.llm.factory import create_langchain_llm

        llm = create_langchain_llm()
        messages = [
            SystemMessage(content=_CLASSIFIER_PROMPT),
            HumanMessage(content=query),
        ]
        response = llm.invoke(messages)
        raw = response.content.strip().lower()

        if "rag" in raw:
            return RouteDecision.RAG
        if "tool" in raw:
            return RouteDecision.TOOL
        return RouteDecision.DIRECT

    except Exception as e:
        logger.warning(f"Router LLM classification failed, defaulting to DIRECT: {e}")
        return RouteDecision.DIRECT
