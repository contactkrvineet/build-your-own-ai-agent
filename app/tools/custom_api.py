"""
Custom REST API tool — calls any user-defined HTTP endpoint.
Toggle in config.yaml → tools.custom_api.enabled
Configure endpoint + auth via .env (CUSTOM_API_ENDPOINT, CUSTOM_API_KEY, etc.)
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Type

import httpx
from pydantic import BaseModel, Field

from app.config.settings import get_settings
from app.tools.base import AskVineetBaseTool
from app.utils.logger import logger


class CustomAPIInput(BaseModel):
    endpoint_override: Optional[str] = Field(
        default=None,
        description="Override the configured endpoint URL for this call",
    )
    params: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Query parameters to include in the request",
    )
    payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="JSON body for POST/PUT/PATCH requests",
    )


class CustomAPITool(AskVineetBaseTool):
    name: str = "call_custom_api"
    description: str = (
        "Call a configured external REST API endpoint and return its response. "
        "Use this when the user asks for data from a specific external service."
    )
    args_schema: Type[BaseModel] = CustomAPIInput

    @classmethod
    def is_enabled(cls) -> bool:
        s = get_settings()
        return s.tool_custom_api_enabled and bool(s.custom_api_endpoint)

    def _run(
        self,
        endpoint_override: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> str:
        s = get_settings()

        if not s.tool_custom_api_enabled:
            return "Custom API tool is disabled. Enable in config.yaml → tools.custom_api.enabled"

        url = endpoint_override or s.custom_api_endpoint
        if not url:
            return "No API endpoint configured. Set CUSTOM_API_ENDPOINT in .env"

        # Build headers — inject auth from env (never from user input)
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if s.custom_api_header_name and s.custom_api_header_value:
            headers[s.custom_api_header_name] = s.custom_api_header_value

        method = "GET"  # Default; extend as needed
        if payload:
            method = "POST"

        try:
            resp = httpx.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()

            # Try JSON, fall back to raw text
            try:
                data = resp.json()
                # Truncate huge responses
                text = str(data)
                if len(text) > 2000:
                    text = text[:2000] + "\n...[truncated]"
                return f"API response ({resp.status_code}):\n{text}"
            except Exception:
                text = resp.text[:2000]
                return f"API response ({resp.status_code}):\n{text}"

        except httpx.HTTPStatusError as e:
            logger.error(f"Custom API HTTP error: {e}")
            return f"API call failed with status {e.response.status_code}: {e.response.text[:500]}"
        except Exception as e:
            logger.error(f"Custom API tool error: {e}")
            return f"API call failed: {str(e)}"
