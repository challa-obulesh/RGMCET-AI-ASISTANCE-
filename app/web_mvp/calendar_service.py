import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)
INDIA_TZ = ZoneInfo("Asia/Kolkata")

class GoogleCalendarService:
    def __init__(self):
        self.enabled = os.getenv("GOOGLE_CALENDAR_ENABLED", "false").lower() == "true"
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN", "")
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        self.service = None

        if self.enabled:
            self._initialize_service()

    def _initialize_service(self):
        try:
            if not self.client_id or not self.client_secret:
                logger.warning("Google Calendar enabled but credentials missing.")
                self.enabled = False
                return

            creds = Credentials(
                token=None,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("Google Calendar service initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize Google Calendar service: {e}")
            self.enabled = False

    async def create_event(self, appointment: dict) -> Optional[str]:
        """Creates a calendar event and returns the event ID."""
        if not self.enabled or not self.service:
            logger.info("Calendar integration disabled or unavailable (create_event)")
            return f"demo_event_id_{appointment['appointment_id']}"

        try:
            date_str = appointment["date"]
            start_str = appointment["start_time"]
            end_str = appointment["end_time"]
            
            start_dt = datetime.strptime(f"{date_str} {start_str}", "%Y-%m-%d %H:%M").replace(tzinfo=INDIA_TZ)
            end_dt = datetime.strptime(f"{date_str} {end_str}", "%Y-%m-%d %H:%M").replace(tzinfo=INDIA_TZ)

            event = {
                'summary': f"Appointment: {appointment.get('student_name', 'Student')} & {appointment.get('professor_name', 'Professor')}",
                'description': appointment.get("reason", ""),
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
            }

            if not self.refresh_token:
                logger.warning("No refresh token to create event, returning demo ID.")
                return f"demo_event_id_{appointment['appointment_id']}"
                
            created_event = self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
            logger.info(f"Created Google Calendar event: {created_event.get('id')}")
            return created_event.get('id')
        except HttpError as error:
            logger.error(f"Google Calendar API error (create_event): {error}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error (create_event): {e}")
            return None

    async def update_event(self, event_id: str, appointment: dict) -> bool:
        if not self.enabled or not self.service or event_id.startswith("demo_event_id_"):
            return True

        try:
            date_str = appointment["date"]
            start_str = appointment["start_time"]
            end_str = appointment["end_time"]
            
            start_dt = datetime.strptime(f"{date_str} {start_str}", "%Y-%m-%d %H:%M").replace(tzinfo=INDIA_TZ)
            end_dt = datetime.strptime(f"{date_str} {end_str}", "%Y-%m-%d %H:%M").replace(tzinfo=INDIA_TZ)

            event = {
                'summary': f"Appointment: {appointment.get('student_name', 'Student')} & {appointment.get('professor_name', 'Professor')}",
                'description': appointment.get("reason", ""),
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': 'Asia/Kolkata',
                },
            }
            if not self.refresh_token:
                return True
                
            self.service.events().update(calendarId=self.calendar_id, eventId=event_id, body=event).execute()
            return True
        except HttpError as error:
            logger.error(f"Google Calendar API error (update_event): {error}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error (update_event): {e}")
            return False

    async def delete_event(self, event_id: str) -> bool:
        if not self.enabled or not self.service or event_id.startswith("demo_event_id_"):
            return True

        try:
            if not self.refresh_token:
                return True
            self.service.events().delete(calendarId=self.calendar_id, eventId=event_id).execute()
            logger.info(f"Deleted Google Calendar event: {event_id}")
            return True
        except HttpError as error:
            logger.error(f"Google Calendar API error (delete_event): {error}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error (delete_event): {e}")
            return False

calendar_service = GoogleCalendarService()
