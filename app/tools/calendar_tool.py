"""
Google Calendar tool — lists upcoming events.
Toggle in config.yaml → tools.calendar.enabled
Credentials: set GOOGLE_CREDENTIALS_FILE in .env
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Type

from pydantic import BaseModel, Field

from app.config.settings import get_settings
from app.tools.base import AskVineetBaseTool
from app.utils.logger import logger


class CalendarInput(BaseModel):
    max_results: Optional[int] = Field(
        default=None,
        description="Maximum number of upcoming events to return",
    )
    calendar_id: str = Field(
        default="primary",
        description="Google Calendar ID (default: primary calendar)",
    )


class CalendarTool(AskVineetBaseTool):
    name: str = "get_calendar_events"
    description: str = (
        "Get upcoming events from Google Calendar. "
        "Use this when the user asks about their schedule, meetings, or upcoming events."
    )
    args_schema: Type[BaseModel] = CalendarInput

    @classmethod
    def is_enabled(cls) -> bool:
        s = get_settings()
        return s.tool_calendar_enabled

    def _run(
        self, max_results: Optional[int] = None, calendar_id: str = "primary"
    ) -> str:
        s = get_settings()

        if not s.tool_calendar_enabled:
            return "Calendar tool is disabled. Enable it in config.yaml → tools.calendar.enabled"

        service = _get_calendar_service(s)
        if service is None:
            return "Calendar service could not be initialised. Check your credentials."

        limit = max_results or s.tool_calendar_max_results

        try:
            now = datetime.now(timezone.utc).isoformat()
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=now,
                    maxResults=limit,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            events = events_result.get("items", [])

            if not events:
                return "No upcoming events found in your calendar."

            lines = [f"Upcoming {len(events)} event(s):"]
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date", ""))
                summary = event.get("summary", "(no title)")
                location = event.get("location", "")
                desc = event.get("description", "")[:100] if event.get("description") else ""

                line = f"• {summary} — {start}"
                if location:
                    line += f"\n  Location: {location}"
                if desc:
                    line += f"\n  Note: {desc}"
                lines.append(line)

            return "\n\n".join(lines)

        except Exception as e:
            logger.error(f"Calendar tool error: {e}")
            return f"Failed to fetch calendar events: {str(e)}"


# ---------------------------------------------------------------------------
# OAuth helper (shared pattern with Gmail)
# ---------------------------------------------------------------------------

def _get_calendar_service(s=None):
    """Build and return an authenticated Google Calendar API service."""
    if s is None:
        s = get_settings()

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/calendar.readonly"]
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
                    logger.error(f"Google credentials file not found: {creds_file}")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(creds_file), scopes
                )
                creds = flow.run_local_server(port=0)
            token_file.write_text(creds.to_json())

        return build("calendar", "v3", credentials=creds)

    except Exception as e:
        logger.error(f"Calendar auth failed: {e}")
        return None
