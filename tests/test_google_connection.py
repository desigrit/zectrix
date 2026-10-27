from datetime import datetime, timedelta
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from note_calendar.google_calendar import GoogleCalendar, INDIA_CALENDAR, SCOPES
from note_calendar.service import CalendarService
from note_calendar.storage import read_json


def test_existing_service_account_uses_only_readonly_events_scope(tmp_path, monkeypatch):
    key = tmp_path / "existing-private-key.json"
    key.write_text("{}")
    monkeypatch.setenv("NOTE_GOOGLE_SERVICE_ACCOUNT_FILE", str(key))
    loader = Mock(return_value=object())
    session = Mock()
    monkeypatch.setattr("note_calendar.google_calendar.service_account.Credentials.from_service_account_file", loader)
    monkeypatch.setattr("note_calendar.google_calendar.AuthorizedSession", session)
    google = GoogleCalendar(tmp_path)

    assert google.connected and google.configured
    assert google.auth_method == "service_account"
    google.session()
    loader.assert_called_once_with(str(key), scopes=SCOPES)
    assert SCOPES == ["https://www.googleapis.com/auth/calendar.events.readonly"]
    session.assert_called_once_with(loader.return_value)
    with pytest.raises(ValueError, match="managed"):
        google.save_client({})
    with pytest.raises(ValueError, match="managed"):
        google.begin("http://localhost/auth/google/callback")


def test_missing_managed_key_never_falls_back_to_another_account(tmp_path, monkeypatch):
    monkeypatch.setenv("NOTE_GOOGLE_SERVICE_ACCOUNT_FILE", str(tmp_path / "missing.json"))
    (tmp_path / "google-token.json").write_text("{}")
    (tmp_path / "google-client.json").write_text("{}")
    google = GoogleCalendar(tmp_path)
    assert not google.connected and not google.configured
    with pytest.raises(FileNotFoundError):
        google.session()

    monkeypatch.delenv("NOTE_GOOGLE_SERVICE_ACCOUNT_FILE")
    oauth = GoogleCalendar(tmp_path)
    assert oauth.auth_method == "oauth" and oauth.connected and oauth.configured


def test_live_fetch_reads_selected_calendar_and_preserves_all_day_dates(tmp_path, monkeypatch):
    google = GoogleCalendar(tmp_path)
    now = datetime(2026, 10, 27, 10, tzinfo=ZoneInfo("America/Los_Angeles"))
    selected = "selected-calendar@example.com"
    all_day = {"id": "birthday", "summary": "Birthday", "start": {"date": "2027-05-30"},
               "end": {"date": "2027-05-31"}, "description": "Not needed for the display"}
    api_session = Mock()
    api_session.__enter__ = Mock(return_value=api_session)
    api_session.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(google, "session", lambda: api_session)
    calls = []

    def fetch(session, calendar_id, start, **kwargs):
        calls.append((calendar_id, kwargs))
        return [all_day] if calendar_id == selected else []

    monkeypatch.setattr(google, "list_events", fetch)
    cache, holidays, error = google.fetch(selected, now)
    assert [call[0] for call in calls] == [selected, INDIA_CALENDAR]
    assert "time_max" not in calls[0][1]
    assert cache["source"] == "google" and cache["calendar_id"] == selected
    assert cache["events"][0]["start"] == {"date": "2027-05-30"}
    assert "description" not in cache["events"][0]
    assert holidays is not None and error is None


def test_live_scheduler_fetches_once_at_midnight_and_survives_restart(tmp_path, monkeypatch):
    key = tmp_path / "existing-private-key.json"
    key.write_text("{}")
    monkeypatch.setenv("NOTE_GOOGLE_SERVICE_ACCOUNT_FILE", str(key))
    service = CalendarService(tmp_path)
    service.configure({"calendar_id":"selected-calendar@example.com"})
    calls = []
    current = datetime(2026, 10, 27, 5, tzinfo=ZoneInfo("America/Los_Angeles"))
    service.now = lambda: current

    def fetch(calendar_id, now):
        calls.append((calendar_id, now.hour))
        return {"source": "google", "calendar_id": calendar_id, "events": [],
                "fetched_at": now.isoformat()}, None, None

    monkeypatch.setattr(service.google, "fetch", fetch)
    for hour in range(24):
        current = current.replace(hour=hour)
        service.scheduled_refresh()
        service.scheduled_refresh()
    assert calls == [(service.settings["calendar_id"], 0)]
    assert read_json(tmp_path / "calendar-cache.json")["source"] == "google"
    status = service.status()
    assert status["source"] == "live" and status["google_auth_method"] == "service_account"
    assert str(key) not in str(status)

    restored = CalendarService(tmp_path)
    restored.now = lambda: current.replace(hour=0, second=20)
    monkeypatch.setattr(restored.google, "fetch", fetch)
    restored.scheduled_refresh()
    assert len(calls) == 1
    restored.now = lambda: current.replace(hour=0) + timedelta(days=1)
    restored.scheduled_refresh()
    assert len(calls) == 2
