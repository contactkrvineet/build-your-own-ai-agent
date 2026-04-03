"""
Chat routes — REST + WebSocket endpoints for the AskVineet agent.

REST:    POST /chat
         GET  /chat/history/{session_id}
         DELETE /chat/session/{session_id}

WebSocket: WS /chat/ws/{session_id}
"""

from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.agent.core import get_agent
from app.utils.logger import logger

router = APIRouter(prefix="/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")


class SourceDoc(BaseModel):
    source: str
    filename: str
    page: str | int
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    route_used: str
    sources: list[SourceDoc] = []
    tool_calls: list[str] = []
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=ChatResponse, summary="Send a message to AskVineet")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a message and receive a response.

    The agent will automatically:
    - Answer from documents (RAG) if the query matches stored knowledge.
    - Call tools (weather, Gmail, calendar) if live data is needed.
    - Fall back to direct LLM response for general questions.
    """
    agent = get_agent()
    response = await agent.achat(request.message, session_id=request.session_id)

    return ChatResponse(
        answer=response.answer,
        session_id=response.session_id,
        route_used=response.route_used,
        sources=[SourceDoc(**s) for s in response.sources],
        tool_calls=response.tool_calls,
        error=response.error,
    )


@router.get(
    "/history/{session_id}",
    summary="Get conversation history for a session",
)
async def get_history(session_id: str) -> dict:
    agent = get_agent()
    history = agent.get_history(session_id)
    return {"session_id": session_id, "messages": history}


@router.delete(
    "/session/{session_id}",
    summary="Clear a session's conversation memory",
)
async def clear_session(session_id: str) -> dict:
    agent = get_agent()
    agent.clear_session(session_id)
    return {"status": "cleared", "session_id": session_id}


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str) -> None:
    """
    WebSocket chat endpoint.

    Client sends:   {"message": "user query here"}
    Server replies: {"answer": "...", "route_used": "...", "sources": [...], "done": true}

    Errors are sent as: {"error": "description", "done": true}
    """
    await websocket.accept()
    logger.info(f"WebSocket connected: session={session_id}")

    agent = get_agent()

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
                message = data.get("message", "").strip()
            except json.JSONDecodeError:
                message = raw.strip()

            if not message:
                await websocket.send_json({"error": "Empty message", "done": True})
                continue

            try:
                response = await agent.achat(message, session_id=session_id)
                await websocket.send_json(
                    {
                        "answer": response.answer,
                        "route_used": response.route_used,
                        "session_id": session_id,
                        "sources": response.sources,
                        "tool_calls": response.tool_calls,
                        "done": True,
                    }
                )
            except Exception as e:
                logger.error(f"WebSocket agent error: {e}")
                await websocket.send_json({"error": str(e), "done": True})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={session_id}")
