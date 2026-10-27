import argparse
import hmac
import ipaddress
import json
import os
import secrets
import time
from datetime import timezone
from io import BytesIO
from pathlib import Path
from flask import Flask, jsonify, redirect, render_template, request, send_file, session, url_for
from .service import CalendarService
from .schedule import next_update, wake_schedule
from .storage import read_json, write_json


def create_app(data_dir=None, background=False):
    data_dir=Path(data_dir or os.environ.get("NOTE_DATA_DIR",Path.cwd()/".data"))
    service=CalendarService(data_dir)
    secret_path=data_dir/"app-secrets.json"
    secret=read_json(secret_path)
    if not secret:
        secret={"session_key":secrets.token_hex(32),"device_key":secrets.token_urlsafe(32)}
        write_json(secret_path,secret)
    app=Flask(__name__)
    app.config.update(SECRET_KEY=secret["session_key"],MAX_CONTENT_LENGTH=32768,
                      SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE="Lax",
                      SESSION_COOKIE_NAME="note_calendar_session")
    original_wsgi=app.wsgi_app

    def mounted_wsgi(environ, start_response):
        # Only the local ESL Hub may supply the fixed mount point. Never trust LAN
        # forwarding headers to turn a remote request into a localhost request.
        if (environ.get("REMOTE_ADDR") in ("127.0.0.1","::1")
                and environ.get("HTTP_X_NOTE_MOUNT")=="/note"):
            environ["SCRIPT_NAME"]="/note"
        return original_wsgi(environ,start_response)

    app.wsgi_app=mounted_wsgi
    app.extensions["calendar_service"]=service
    csrf=secrets.token_urlsafe(32)
    flows={}

    @app.before_request
    def protect():
        if request.path.startswith("/device/"):
            token=request.headers.get("Authorization","").removeprefix("Bearer ")
            if not hmac.compare_digest(token,secret["device_key"]):
                return jsonify(error="Device pairing is required."),401
            return None
        try:
            local=ipaddress.ip_address(request.remote_addr).is_loopback
        except ValueError:
            local=False
        if not local:
            return "Open the controller through its SSH tunnel on this computer.",403
        if request.host.split(":")[0] not in ("localhost","127.0.0.1","[::1]"):
            return "Use localhost or 127.0.0.1 for the controller.",403
        if request.method not in ("GET","HEAD","OPTIONS") and not hmac.compare_digest(request.headers.get("X-CSRF-Token",""),csrf):
            return jsonify(error="Reload this page and try again."),403

    @app.after_request
    def headers(response):
        response.headers["Cache-Control"]="no-store, private"
        response.headers["X-Content-Type-Options"]="nosniff"
        response.headers["Referrer-Policy"]="no-referrer"
        ancestors="'self'" if request.script_root=="/note" and request.args.get("embedded")=="1" else "'none'"
        response.headers["Content-Security-Policy"]=f"default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors {ancestors}; base-uri 'none'; form-action 'self'"
        return response

    @app.errorhandler(ValueError)
    def invalid(error):
        return jsonify(error=str(error)),400

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error="The file is too large. Choose the Google Desktop OAuth client JSON."),413

    @app.get("/")
    def index():
        return render_template("index.html",csrf=csrf,embedded=request.script_root=="/note" and request.args.get("embedded")=="1")

    @app.get("/api/status")
    def status():
        result=service.status(request.args.get("mode","calendar"))
        result["next_update"]=next_update(service.now()).isoformat()
        result["device_seen"]=service.device_seen
        return jsonify(result)

    @app.get("/api/frame.png")
    def frame_png():
        mode=request.args.get("mode","calendar")
        scale=int(request.args.get("scale",1))
        if scale not in (1,2,3):
            raise ValueError("Preview scale must be 1, 2 or 3.")
        frame=service.frame(mode)
        return send_file(BytesIO(frame.png(scale,native_colors=request.args.get("native")=="1")),mimetype="image/png",download_name="note-calendar.png",as_attachment=request.args.get("download")=="1")

    @app.get("/api/frame.bin")
    def frame_bin():
        frame=service.frame(request.args.get("mode","calendar"))
        return send_file(BytesIO(frame.binary()),mimetype="application/octet-stream",download_name="note-calendar-400x300.bin",as_attachment=True)

    @app.post("/api/refresh")
    def refresh():
        try:
            return jsonify(service.sync())
        except ValueError:
            raise
        except Exception:
            return jsonify(error=service.error),502

    @app.post("/api/settings")
    def settings():
        return jsonify(settings=service.configure(request.get_json() or {}),message="Settings saved.")

    @app.post("/api/device/check")
    def check():
        try:
            result=service.device.check(service.settings["device_url"])
            return jsonify(result,message="The Note's LAN image service is ready.")
        except ValueError:
            raise
        except Exception:
            return jsonify(error="Could not reach the Note. Check its IP address and wake it first."),502

    @app.post("/api/device/send")
    def send():
        try:
            return jsonify(service.send(force=bool((request.get_json(silent=True) or {}).get("force"))))
        except ValueError:
            raise
        except Exception:
            return jsonify(error=service.device_error),502

    @app.get("/api/pairing")
    def pairing():
        return jsonify(device_key=secret["device_key"],controller_url=os.environ.get("NOTE_DEVICE_URL","http://192.168.1.100:29174"))

    @app.post("/api/google/client")
    def client():
        upload=request.files.get("file")
        if upload is None:
            raise ValueError("Choose the Google Desktop OAuth client JSON.")
        try:
            payload=json.loads(upload.read())
        except (ValueError,UnicodeDecodeError):
            raise ValueError("This file is not valid JSON.")
        service.google.save_client(payload)
        return jsonify(message="Google client saved. You can now connect your calendar.")

    @app.get("/auth/google")
    def google_start():
        if request.script_root:
            # Google Desktop clients require a loopback redirect. Start the whole
            # flow there so the browser's state cookie has the correct origin.
            return redirect("http://127.0.0.1:29176/auth/google")
        if not service.google.configured:
            return redirect(url_for("index",notice="google-client-needed"))
        callback=request.url_root.rstrip("/")+"/auth/google/callback"
        url,state,flow=service.google.begin(callback)
        flows[state]=(time.monotonic(),flow)
        session["oauth_state"]=state
        return redirect(url)

    @app.get("/auth/google/callback")
    def google_callback():
        state=request.args.get("state","")
        item=flows.pop(state,None)
        if not item or not hmac.compare_digest(state,session.pop("oauth_state","")) or time.monotonic()-item[0]>600:
            return redirect(url_for("index",notice="google-expired"))
        if request.args.get("error") or not request.args.get("code"):
            return redirect(url_for("index",notice="google-cancelled"))
        try:
            service.google.finish(item[1],request.args["code"])
            service.sync()
        except Exception:
            return redirect(url_for("index",notice="google-failed"))
        return redirect(url_for("index",notice="google-connected"))

    @app.get("/device/frame")
    def device_frame():
        try:
            frame=service.device_frame(manual=request.headers.get("X-Wake-Reason")=="manual")
        except Exception:
            frame=service.frame()
        now=service.now()
        # Subtract UTC timestamps so the overnight interval also handles DST changes.
        seconds=max(60,int(next_update(now).timestamp()-now.timestamp()))
        digest=frame.digest
        if request.headers.get("If-None-Match","").strip('"')==digest:
            response=app.response_class(status=304)
        else:
            response=app.response_class(frame.binary(),mimetype="application/octet-stream")
        response.headers["ETag"]=f'"{digest}"'
        response.headers["X-Sleep-Seconds"]=str(seconds)
        response.headers["X-Server-Time"]=str(int(now.timestamp()))
        response.headers["X-Wake-Schedule"]=",".join(map(str,wake_schedule(now)))
        return response

    @app.post("/device/ack")
    def device_ack():
        digest=(request.get_json(silent=True) or {}).get("digest","")
        if len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Invalid frame digest.")
        service.record_device(digest)
        return jsonify(ok=True)

    if background:
        service.start()
    return app


def main():
    parser=argparse.ArgumentParser(description="Note calendar controller")
    parser.add_argument("--port",type=int,default=29174)
    parser.add_argument("--host",default="127.0.0.1")
    parser.add_argument("--data-dir",type=Path)
    args=parser.parse_args()
    app=create_app(args.data_dir,background=True)
    from waitress import serve
    serve(app,host=args.host,port=args.port,threads=4)


if __name__=="__main__":
    main()
