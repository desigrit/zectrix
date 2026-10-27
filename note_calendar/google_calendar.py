import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
from google.auth.transport.requests import AuthorizedSession, Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import Flow
from .storage import read_json, write_json

SCOPES = ["https://www.googleapis.com/auth/calendar.events.readonly"]
INDIA_CALENDAR = "en.indian#holiday@group.v.calendar.google.com"


class GoogleCalendar:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.client_path = data_dir / "google-client.json"
        self.token_path = data_dir / "google-token.json"
        # Deployment-only configuration. The browser cannot choose a credential
        # path or upload a service account key.
        account_file = os.environ.get("NOTE_GOOGLE_SERVICE_ACCOUNT_FILE")
        self.service_account_path = Path(account_file) if account_file else None

    @property
    def auth_method(self):
        return "service_account" if self.service_account_path is not None else "oauth"

    @property
    def connected(self):
        if self.service_account_path is not None:
            return self.service_account_path.is_file()
        return self.token_path.exists()

    @property
    def configured(self):
        if self.service_account_path is not None:
            return self.service_account_path.is_file()
        return self.client_path.exists()

    def save_client(self, payload: dict):
        if self.service_account_path is not None:
            raise ValueError("Google Calendar is managed by this Pi's existing calendar connection.")
        client = payload.get("installed")
        if not isinstance(client, dict) or not client.get("client_id") or not client.get("client_secret"):
            raise ValueError("Choose a Google OAuth client JSON for a Desktop app.")
        # Never accept arbitrary authorization/token hosts from an uploaded file.
        if client.get("auth_uri") != "https://accounts.google.com/o/oauth2/auth" or client.get("token_uri") != "https://oauth2.googleapis.com/token":
            raise ValueError("This file does not contain the standard Google OAuth endpoints.")
        write_json(self.client_path, {"installed": client})

    def begin(self, redirect_uri: str):
        if self.service_account_path is not None:
            raise ValueError("Google Calendar is managed by this Pi's existing calendar connection.")
        flow = Flow.from_client_secrets_file(str(self.client_path), scopes=SCOPES, autogenerate_code_verifier=True)
        flow.redirect_uri = redirect_uri
        url, state = flow.authorization_url(access_type="offline", prompt="consent")
        return url, state, flow

    def finish(self, flow, code: str):
        flow.fetch_token(code=code)
        if not flow.credentials.refresh_token:
            raise ValueError("Google did not return permission for background refresh. Connect again and allow access.")
        write_json(self.token_path, json.loads(flow.credentials.to_json()))

    def session(self):
        if self.service_account_path is not None:
            credentials = service_account.Credentials.from_service_account_file(
                str(self.service_account_path), scopes=SCOPES)
            return AuthorizedSession(credentials)
        credentials = Credentials.from_authorized_user_file(str(self.token_path), scopes=SCOPES)
        if not credentials.valid:
            if not credentials.refresh_token:
                raise ValueError("Reconnect Google Calendar to renew access.")
            credentials.refresh(Request())
            write_json(self.token_path, json.loads(credentials.to_json()))
        return AuthorizedSession(credentials)

    @staticmethod
    def list_events(session, calendar_id: str, now: datetime, maximum=100, time_max=None):
        url = f"https://www.googleapis.com/calendar/v3/calendars/{quote(calendar_id, safe='')}/events"
        params = {"singleEvents":"true", "orderBy":"startTime", "showDeleted":"false",
                  "timeMin":now.isoformat(), "timeZone":str(now.tzinfo), "maxResults":min(maximum, 250)}
        if time_max is not None:
            params["timeMax"] = time_max.isoformat()
        events=[]
        seen=set()
        while True:
            response=session.get(url, params=params, timeout=20)
            response.raise_for_status()
            page=response.json()
            events.extend(page.get("items", []))
            token=page.get("nextPageToken")
            if not token or len(events)>=maximum:
                break
            if token in seen:
                raise ValueError("Google Calendar returned a repeated page. Try refreshing again.")
            seen.add(token)
            params["pageToken"]=token
        return events[:maximum]

    def fetch(self, calendar_id: str, now: datetime):
        with self.session() as session:
            events=self.list_events(session, calendar_id, now)
            # Holiday freshness is independent of the personal calendar's successful sync.
            holidays=None
            holiday_error=None
            try:
                limit=now + timedelta(days=550)
                holidays=self.list_events(session, INDIA_CALENDAR, now.replace(hour=0,minute=0,second=0,microsecond=0), maximum=250, time_max=limit)
            except Exception:
                holiday_error="Indian holiday refresh failed. The saved holiday dates are still available."
        stamp=datetime.now(timezone.utc).isoformat()
        allowed=("id","summary","start","end","status","attendees")
        minimal=[{key:e[key] for key in allowed if key in e} for e in events]
        for event in minimal:
            event["attendees"]=[a for a in event.get("attendees",[]) if a.get("self")]
        cache={"source":"google", "calendar_id":calendar_id,"fetched_at":stamp,"events":minimal}
        holiday_cache=None if holidays is None else {
            "events":[{key:e[key] for key in ("id","summary","start") if key in e} for e in holidays],
            "fetched_at":stamp,"coverage_end":limit.date().isoformat(),"source":"Google Calendar: Holidays in India"}
        return cache, holiday_cache, holiday_error
