import ipaddress
from datetime import datetime, timezone
from urllib.parse import urlsplit
import requests
from .storage import read_json, write_json


def device_url(value: str) -> str:
    value=value.strip().rstrip("/")
    if not value:
        return ""
    parsed=urlsplit(value if "://" in value else f"http://{value}")
    if parsed.scheme != "http" or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("Enter only the Note's local IPv4 address, such as 192.168.1.42.")
    try:
        address=ipaddress.IPv4Address(parsed.hostname)
        port=parsed.port
    except ValueError as exc:
        raise ValueError("Enter the local IPv4 address shown in the Note's LAN service settings.") from exc
    networks=[ipaddress.IPv4Network(n) for n in ("10.0.0.0/8","172.16.0.0/12","192.168.0.0/16")]
    if not any(address in network for network in networks) or port not in (None,80):
        raise ValueError("Use the Note's private LAN IPv4 address on port 80.")
    return f"http://{address}"


class NoteDevice:
    def __init__(self, state_path, session=None):
        self.path=state_path
        self.http=session or requests.Session()
        self.http.trust_env=False

    def check(self, url):
        url=device_url(url)
        if not url:
            raise ValueError("Add the Note's IP address first.")
        response=self.http.get(url+"/status", timeout=5, allow_redirects=False)
        response.raise_for_status()
        value=response.json()
        if value.get("status") != "ready" or value.get("mode") not in ("lan","ap"):
            raise ValueError("This address is not reporting the compatible Note image service.")
        return value

    def push(self, url, frame, force=False):
        url=device_url(url)
        self.check(url)
        saved=read_json(self.path,{})
        state=saved if saved.get("url")==url else {"url":url}
        if not force and state.get("digest")==frame.digest and state.get("display_requested"):
            return {"status":"unchanged","message":"The same frame was already sent. No refresh requested."}
        previous=state.get("photo_id")
        pending=state.get("pending",{})
        if pending.get("digest")==frame.digest:
            photo_id=pending["id"]
        else:
            response=self.http.post(url+"/upload?format=bwry2bpp",data=frame.binary(),
                                    headers={"Content-Type":"application/octet-stream"},timeout=30,allow_redirects=False)
            response.raise_for_status()
            result=response.json()
            photo_id=result.get("id")
            if not result.get("success") or not isinstance(photo_id,str) or not photo_id:
                raise ValueError("The Note did not confirm that the image was saved.")
            state["pending"]={"id":photo_id,"digest":frame.digest}
            write_json(self.path,state)
        response=self.http.post(url+"/photo/show",json={"id":photo_id},timeout=30,allow_redirects=False)
        response.raise_for_status()
        if not response.json().get("success"):
            raise ValueError("The image was uploaded, but display was not accepted. Wake the Note and retry.")
        state.update(photo_id=photo_id,digest=frame.digest,display_requested=True,
                     sent_at=datetime.now(timezone.utc).isoformat())
        state.pop("pending",None)
        write_json(self.path,state)
        # Only remove the previous frame recorded as created by this app on this device.
        cleanup_error=False
        if previous and previous != photo_id:
            try:
                deleted=self.http.delete(url+"/photo",params={"id":previous},timeout=10,allow_redirects=False)
                deleted.raise_for_status()
                cleanup_error=not deleted.json().get("success",False)
            except (requests.RequestException,ValueError):
                cleanup_error=True
        return {"status":"sent","message":"Image uploaded and display requested. Allow time for the e-paper refresh.",
                "cleanup_warning":cleanup_error,"sent_at":state["sent_at"]}
