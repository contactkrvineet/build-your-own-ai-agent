"""Health check routes."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.config.settings import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", summary="Health check")
async def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "agent": s.agent_name,
        "version": s.agent_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/llm", summary="LLM provider health check")
async def llm_health() -> dict:
    try:
        from app.llm.factory import create_llm_provider
        from app.llm.base import LLMMessage

        provider = create_llm_provider()
        ok = provider.health_check()
        return {
            "status": "ok" if ok else "degraded",
            "provider": provider.provider_name,
            "model": provider.model_name,
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}
