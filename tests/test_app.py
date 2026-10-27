import re
from pathlib import Path
from note_calendar.app import create_app
from note_calendar.storage import read_json, write_json
from note_calendar.device import device_url
from note_calendar.google_calendar import GoogleCalendar
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path)


def test_preview_export_and_no_made_up_live_events(app):
    client=app.test_client()
    response=client.get("/api/status")
    assert response.status_code==200
    assert response.json["total"]==0
    service=app.extensions["calendar_service"]
    assert read_json(service.data_dir/"settings.json")["update_hours"]==[0]
    assert client.get("/api/frame.png").data.startswith(b"\x89PNG")
    assert len(client.get("/api/frame.bin").data)==30000
    assert client.get("/api/status?mode=busy").json["total"]==17


def test_mutations_require_csrf_and_snapshot_refresh_is_honest(app):
    client=app.test_client()
    assert client.post("/api/refresh").status_code==403
    html=client.get("/").text
    token=re.search(r'name="csrf-token" content="([^"]+)"',html)[1]
    response=client.post("/api/refresh",headers={"X-CSRF-Token":token})
    assert response.status_code==400 and "snapshot" in response.json["error"]


def test_lan_admin_is_blocked_but_authenticated_device_can_pull(app,tmp_path):
    client=app.test_client()
    environ={"REMOTE_ADDR":"192.168.1.50"}
    assert client.get("/api/status",environ_overrides=environ).status_code==403
    assert client.get("/device/frame",environ_overrides=environ).status_code==401
    key=read_json(tmp_path/"app-secrets.json")["device_key"]
    headers={"Authorization":"Bearer "+key}
    first=client.get("/device/frame",headers=headers,environ_overrides=environ)
    assert first.status_code==200 and len(first.data)==30000
    headers["If-None-Match"]=first.headers["ETag"]
    unchanged=client.get("/device/frame",headers=headers,environ_overrides=environ)
    assert unchanged.status_code==304 and not unchanged.data
    assert int(unchanged.headers["X-Sleep-Seconds"])>=60


@pytest.mark.parametrize("url",["http://127.0.0.1","https://192.168.1.2","http://example.com","http://192.168.1.2/secret","http://192.168.1.2:3000"])
def test_reference_device_address_must_be_local_ipv4(url):
    with pytest.raises(ValueError):device_url(url)


def test_calendar_pagination_continues_after_empty_page():
    class Response:
        def __init__(self,payload):self.payload=payload
        def raise_for_status(self):pass
        def json(self):return self.payload
    class Session:
        def __init__(self):self.params=[]
        def get(self,url,params,timeout):
            self.params.append(dict(params))
            return Response({"items":[],"nextPageToken":"next"} if len(self.params)==1 else {"items":[{"id":"event"}]})
    session=Session()
    rows=GoogleCalendar.list_events(session,"calendar@example.com",datetime(2026,10,26,tzinfo=ZoneInfo("America/Los_Angeles")))
    assert rows==[{"id":"event"}]
    assert session.params[1]["pageToken"]=="next"
    assert "timeMax" not in session.params[0]


def test_button_refresh_is_explicit_and_timer_does_not_sync_outside_midnight(app,monkeypatch):
    service=app.extensions["calendar_service"]
    service.now=lambda:datetime(2026,10,26,22,tzinfo=ZoneInfo("America/Los_Angeles"))
    monkeypatch.setattr(type(service.google),"connected",property(lambda self:True))
    calls=[]
    service.sync=lambda:calls.append("fetched")
    service.device_frame(manual=False)
    assert calls==[]
    service.device_frame(manual=True)
    assert calls==["fetched"]


def test_failed_refresh_keeps_saved_calendar(app,monkeypatch):
    service=app.extensions["calendar_service"]
    service.configure({"calendar_id":"selected-calendar@example.com"})
    service.cache={"events":[{"id":"saved"}],"source":"connector-snapshot"}
    monkeypatch.setattr(type(service.google),"connected",property(lambda self:True))
    def fail(*args):raise ConnectionError("network unavailable")
    monkeypatch.setattr(service.google,"fetch",fail)
    with pytest.raises(ConnectionError):service.sync()
    assert service.cache["events"]==[{"id":"saved"}]
    assert service.error and not service.sync_lock.locked()


def test_fresh_install_requires_explicit_calendar_selection(app,monkeypatch):
    service=app.extensions["calendar_service"]
    assert service.settings["calendar_id"]==""
    monkeypatch.setattr(type(service.google),"connected",property(lambda self:True))
    calls=[]
    monkeypatch.setattr(service.google,"fetch",lambda *args:calls.append(args))
    with pytest.raises(ValueError,match="calendar ID"):
        service.sync()
    assert calls==[]


def test_saved_daytime_schedule_migrates_to_midnight_without_changing_calendar(tmp_path):
    write_json(tmp_path/"settings.json",{"update_hours":[6,10,14,18],
               "calendar_id":"selected-calendar@example.com","timezone":"America/Los_Angeles",
               "manual_refresh":False})
    app=create_app(tmp_path)
    settings=app.test_client().get("/api/status").json["settings"]
    assert settings["update_hours"]==[0]
    assert settings["calendar_id"]=="selected-calendar@example.com"
    assert settings["manual_refresh"] is False
    assert read_json(tmp_path/"settings.json")==settings


def test_device_receives_midnight_schedule_even_when_image_is_unchanged(app,tmp_path):
    tz=ZoneInfo("America/Los_Angeles")
    now=datetime(2026,10,27,12,tzinfo=tz)
    app.extensions["calendar_service"].now=lambda:now
    client=app.test_client()
    key=read_json(tmp_path/"app-secrets.json")["device_key"]
    headers={"Authorization":"Bearer "+key,"X-Wake-Reason":"timer"}
    first=client.get("/device/frame",headers=headers)
    assert first.status_code==200
    headers["If-None-Match"]=first.headers["ETag"]
    unchanged=client.get("/device/frame",headers=headers)
    assert unchanged.status_code==304
    for response in (first,unchanged):
        wakes=[datetime.fromtimestamp(int(t),tz) for t in response.headers["X-Wake-Schedule"].split(",")]
        assert len(wakes)==28
        assert wakes[0]==datetime(2026,10,28,0,tzinfo=tz)
        assert all(stamp.hour==stamp.minute==stamp.second==0 for stamp in wakes)
        assert int(response.headers["X-Sleep-Seconds"])==12*3600
    assert client.get("/api/status").json["next_update"]==wakes[0].isoformat()
