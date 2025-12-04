from datetime import datetime
from typing import Optional
import os


class CalendarClient:
    def __init__(self):
        self.enabled = bool(os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON"))
        self.default_calendar = os.getenv("GOOGLE_CALENDAR_DEFAULT_ID", "primary")

    def create_event(self, calendar_id: str, summary: str, description: str, start: datetime, end: datetime, attendees: list[str]) -> Optional[str]:
        if not self.enabled:
            return None
        return "mock-calendar-event-id"


