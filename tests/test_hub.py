from email.message import Message
import re
from urllib.error import URLError

from flask import Flask
from deploy import esl_note_proxy
from note_calendar.app import create_app


def test_mount_keeps_assets_api_links_and_google_loopback_correct(tmp_path):
    app=create_app(tmp_path)
    client=app.test_client()
    headers={"X-Note-Mount":"/note"}
    page=client.get("/",headers=headers)
    assert 'content="/note"' in page.text
    for path in ("static/app.css","static/app.js","api/frame.png","api/frame.bin","auth/google"):
        assert '/note/'+path in page.text
    assert 'href="/">Back to ESL Hub' in page.text
    embedded=client.get("/?embedded=1",headers=headers)
    assert 'class="hub-embedded"' in embedded.text
    assert "frame-ancestors 'self'" in embedded.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in page.headers["Content-Security-Policy"]
    assert "Back to ESL Hub" not in embedded.text
    assert embedded.text.count('id="source-label"')==1
    token=re.search(r'name="csrf-token" content="([^"]+)"',page.text)[1]
    assert client.post("/api/settings",headers=headers,json={"timezone":"America/Los_Angeles"}).status_code==403
    assert client.post("/api/settings",headers={**headers,"X-CSRF-Token":token},json={"timezone":"America/Los_Angeles"}).status_code==200
    assert client.get("/auth/google",headers=headers).location=="http://127.0.0.1:29176/auth/google"
    assert client.get("/api/status",headers=headers,environ_overrides={"REMOTE_ADDR":"192.168.1.50"}).status_code==403


def test_hub_proxy_forwards_body_and_security_headers_without_following_redirects(monkeypatch):
    calls=[]
    class Result:
        code=302
        headers=Message()
        headers["Location"]="http://127.0.0.1:29176/auth/google"
        headers["Cache-Control"]="no-store"
        headers["Set-Cookie"]="note_calendar_session=state; HttpOnly; SameSite=Lax"
        headers["Connection"]="keep-alive"
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self):return b"redirect"
    class Opener:
        def open(self,request,timeout):
            calls.append(request)
            return Result()
    monkeypatch.setattr(esl_note_proxy,"build_opener",lambda *args:Opener())
    app=Flask(__name__)
    esl_note_proxy.register_note_controller(app)
    client=app.test_client()
    response=client.post("/note/api/settings?mode=calendar",base_url="http://raspberrypi.local:5000",json={"timezone":"America/Los_Angeles"},headers={"X-CSRF-Token":"test-token","X-Note-Mount":"/untrusted","Origin":"http://raspberrypi.local:5000"},environ_overrides={"REMOTE_ADDR":"192.168.1.50"})
    assert response.status_code==302
    assert response.location=="http://127.0.0.1:29176/auth/google"
    assert response.headers["Set-Cookie"].startswith("note_calendar_session=")
    assert "Connection" not in response.headers
    assert calls[0].full_url=="http://127.0.0.1:29174/api/settings?mode=calendar"
    assert calls[0].get_header("X-note-mount")=="/note"
    assert calls[0].get_header("X-csrf-token")=="test-token"
    assert b"America/Los_Angeles" in calls[0].data
    for kwargs in ({"environ_overrides":{"REMOTE_ADDR":"203.0.113.1"}}, {"base_url":"http://evil.example"}):
        assert client.get("/note/api/status",**kwargs).status_code==403
    assert client.post("/note/api/settings",headers={"Origin":"http://evil.example"}).status_code==403
    assert client.post("/note/api/settings",data=b"a"*32769).status_code==413
    assert len(calls)==1


def test_hub_unavailable_response_is_recoverable(monkeypatch):
    class Opener:
        def open(self,*args,**kwargs):raise URLError("offline")
    monkeypatch.setattr(esl_note_proxy,"build_opener",lambda *args:Opener())
    app=Flask(__name__)
    esl_note_proxy.register_note_controller(app)
    client=app.test_client()
    assert client.get("/note/").location=="/?tab=note4"
    response=client.get("/note/?embedded=1")
    assert response.status_code==502
    assert "Reload" in response.text
    assert response.headers["Cache-Control"]=="no-store"


def test_hub_accepts_only_explicit_custom_hosts(monkeypatch):
    monkeypatch.setenv("NOTE_HUB_ALLOWED_HOSTS","display-hub.local,192.168.1.100")
    app=Flask(__name__)
    esl_note_proxy.register_note_controller(app)
    client=app.test_client()
    for host in ("display-hub.local","192.168.1.100"):
        assert client.get("/note/",base_url="http://"+host+":5000").location=="/?tab=note4"
    assert client.get("/note/",base_url="http://other-hub.local:5000").status_code==403
