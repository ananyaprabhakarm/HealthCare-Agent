from datetime import datetime
from typing import Optional
import os
import json

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False


class CalendarClient:
    def __init__(self):
        creds_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_JSON", "")
        self.enabled = bool(creds_path and GOOGLE_CALENDAR_AVAILABLE)
        self.default_calendar = os.getenv("GOOGLE_CALENDAR_DEFAULT_ID", "primary")
        self.service = None
        if self.enabled:
            try:
                if os.path.exists(creds_path):
                    creds = service_account.Credentials.from_service_account_file(
                        creds_path,
                        scopes=['https://www.googleapis.com/auth/calendar']
                    )
                else:
                    creds_data = json.loads(creds_path)
                    creds = service_account.Credentials.from_service_account_info(
                        creds_data,
                        scopes=['https://www.googleapis.com/auth/calendar']
                    )
                self.service = build('calendar', 'v3', credentials=creds)
            except Exception as e:
                print(f"Failed to initialize Google Calendar: {e}")
                self.enabled = False

    def create_event(self, calendar_id: str, summary: str, description: str, start: datetime, end: datetime, attendees: list[str]) -> Optional[str]:
        if not self.enabled or not self.service:
            return None
        try:
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': end.isoformat(),
                    'timeZone': 'UTC',
                },
                'attendees': [{'email': email} for email in attendees],
            }
            event = self.service.events().insert(calendarId=calendar_id or self.default_calendar, body=event).execute()
            return event.get('id')
        except HttpError as e:
            print(f"Google Calendar API error: {e}")
            return None
        except Exception as e:
            print(f"Error creating calendar event: {e}")
            return None


