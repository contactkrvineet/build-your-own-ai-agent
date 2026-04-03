"""
Conversation memory management.

Short-term: ConversationBufferWindowMemory (last N turns, per-session).
Long-term:  Vector store–backed memory for cross-session recall.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from uuid import uuid4

from langchain.memory import ConversationBufferWindowMemory

from app.config.settings import get_settings
from app.utils.logger import logger


# ---------------------------------------------------------------------------
# Session store (in-process; replace with Redis for multi-process deployments)
# ---------------------------------------------------------------------------

_sessions: Dict[str, ConversationBufferWindowMemory] = {}


def get_session_memory(session_id: Optional[str] = None) -> tuple[str, ConversationBufferWindowMemory]:
    """
    Return (session_id, memory) for a given session.
    Creates a new session if *session_id* is None or unknown.
    """
    s = get_settings()

    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]

    # New session
    sid = session_id or str(uuid4())
    memory = ConversationBufferWindowMemory(
        k=s.memory_window_size,
        memory_key="chat_history",
        return_messages=True,
        output_key="output",
    )
    _sessions[sid] = memory
    logger.debug(f"New session created: {sid}")
    return sid, memory


def clear_session(session_id: str) -> None:
    """Clear a session's short-term memory."""
    if session_id in _sessions:
        _sessions[session_id].clear()
        logger.info(f"Session cleared: {session_id}")


def list_sessions() -> List[str]:
    """Return all active session IDs."""
    return list(_sessions.keys())


def get_session_history(session_id: str) -> List[dict]:
    """
    Return conversation history for a session as a list of
    {"role": "user"|"assistant", "content": "..."} dicts.
    """
    if session_id not in _sessions:
        return []

    memory = _sessions[session_id]
    messages = memory.chat_memory.messages
    history = []
    for msg in messages:
        role = "user" if msg.type == "human" else "assistant"
        history.append({"role": role, "content": str(msg.content)})
    return history
