"""
Gmail tool — reads and summarises recent emails via Gmail API.
Toggle in config.yaml → tools.gmail.enabled
Credentials: set GOOGLE_CREDENTIALS_FILE in .env
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional, Type

from pydantic import BaseModel, Field

from app.config.settings import get_settings
from app.tools.base import AskVineetBaseTool
from app.utils.logger import logger


class GmailInput(BaseModel):
    query: str = Field(
        default="is:unread",
        description=(
            "Gmail search query, e.g. 'is:unread', 'from:boss@example.com', "
            "'subject:meeting label:inbox'"
        ),
    )
    max_results: Optional[int] = Field(
        default=None,
        description="Maximum number of emails to return (default: from config)",
    )


class GmailTool(AskVineetBaseTool):
    name: str = "read_gmail"
    description: str = (
        "Read and summarise emails from Gmail. "
        "Use this when the user asks to check emails, read messages, or summarise inbox."
    )
    args_schema: Type[BaseModel] = GmailInput

    @classmethod
    def is_enabled(cls) -> bool:
        s = get_settings()
        return s.tool_gmail_enabled

    def _run(self, query: str = "is:unread", max_results: Optional[int] = None) -> str:
        s = get_settings()
        limit = max_results or s.tool_gmail_max_results

        if not s.tool_gmail_enabled:
            return "Gmail tool is disabled. Enable it in config.yaml → tools.gmail.enabled"

        service = _get_gmail_service(s)
        if service is None:
            return "Gmail service could not be initialised. Check your credentials."

        try:
            results = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=limit)
                .execute()
            )
            messages = results.get("messages", [])

            if not messages:
                return f"No emails found for query: '{query}'"

            summaries = []
            for msg_ref in messages:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_ref["id"], format="metadata")
                    .execute()
                )
                headers = {
                    h["name"].lower(): h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }
                subject = headers.get("subject", "(no subject)")
                sender = headers.get("from", "unknown")
                date = headers.get("date", "")
                snippet = msg.get("snippet", "")[:200]
                summaries.append(
                    f"• From: {sender}\n"
                    f"  Subject: {subject}\n"
                    f"  Date: {date}\n"
                    f"  Preview: {snippet}"
                )

            return f"Found {len(summaries)} email(s):\n\n" + "\n\n".join(summaries)

        except Exception as e:
            logger.error(f"Gmail tool error: {e}")
            return f"Failed to read Gmail: {str(e)}"


# ---------------------------------------------------------------------------
# OAuth helper
# ---------------------------------------------------------------------------

def _get_gmail_service(s=None):
    """Build and return an authenticated Gmail API service object."""
    if s is None:
        s = get_settings()

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        scopes = [
            "https://www.googleapis.com/auth/gmail.readonly",
        ]
        creds_file = Path(s.google_credentials_file or "./credentials.json")
        token_file = Path(s.google_token_file or "./data/google_token.json")
        token_file.parent.mkdir(parents=True, exist_ok=True)

        creds = None
        if token_file.exists():
            creds = Credentials.from_authorized_user_file(str(token_file), scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not creds_file.exists():
                    logger.error(f"Gmail credentials file not found: {creds_file}")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(creds_file), scopes
                )
                creds = flow.run_local_server(port=0)
            token_file.write_text(creds.to_json())

        return build("gmail", "v1", credentials=creds)

    except Exception as e:
        logger.error(f"Gmail auth failed: {e}")
        return None
