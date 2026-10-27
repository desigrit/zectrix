import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .demo import demo_events
from .device import NoteDevice, device_url
from .google_calendar import GoogleCalendar
from .holidays import bundled_indian_events, next_holiday
from .models import upcoming
from .render import render
from .storage import read_json, write_json
from .schedule import UPDATE_HOURS, due_update, next_update

DEFAULTS={"timezone":"America/Los_Angeles", "calendar_id":"",
          "device_url":"", "auto_send":False,"update_hours":list(UPDATE_HOURS),"power_mode":"battery","manual_refresh":True}


class CalendarService:
    def __init__(self, data_dir: Path):
        self.data_dir=data_dir
        data_dir.mkdir(parents=True,exist_ok=True)
        settings_path=data_dir/"settings.json"
        self.settings={**DEFAULTS,**read_json(settings_path,{})}
        # The scheduler and reported settings share one fixed cadence. Migrate
        # saved settings so an earlier schedule cannot remain visible after deploy.
        if not settings_path.exists() or self.settings["update_hours"] != list(UPDATE_HOURS):
            self.settings["update_hours"] = list(UPDATE_HOURS)
            write_json(settings_path,self.settings)
        self.google=GoogleCalendar(data_dir)
        self.device=NoteDevice(data_dir/"device-state.json")
        self.cache=read_json(data_dir/"calendar-cache.json",{"events":[],"source":"empty"})
        self.holidays=read_json(data_dir/"holiday-cache.json",bundled_indian_events())
        self.lock=threading.RLock()
        self.sync_lock=threading.Lock()
        self.device_lock=threading.Lock()
        self.error=None
        self.holiday_error=None
        self.device_error=None
        self.last_attempt=None
        self.last_send=None
        self.stopped=threading.Event()
        self.last_slot=read_json(data_dir/"schedule-state.json",{}).get("last_slot")
        self.device_seen=read_json(data_dir/"device-seen.json",{})

    def now(self):
        return datetime.now(ZoneInfo(self.settings["timezone"]))

    def configure(self, values):
        updated={**self.settings}
        if "timezone" in values:
            try:
                ZoneInfo(values["timezone"])
            except (ValueError,KeyError,TypeError):
                raise ValueError("Use a valid timezone, such as America/Los_Angeles.")
            updated["timezone"]=values["timezone"]
        if "calendar_id" in values:
            calendar=str(values["calendar_id"]).strip()
            if not calendar or len(calendar)>300:
                raise ValueError("Enter the calendar ID from Google Calendar settings.")
            updated["calendar_id"]=calendar
        if "device_url" in values:
            updated["device_url"]=device_url(values["device_url"])
        if "auto_send" in values:
            if not isinstance(values["auto_send"],bool):
                raise ValueError("Automatic sending must be on or off.")
            updated["auto_send"]=values["auto_send"]
        if "manual_refresh" in values:
            if not isinstance(values["manual_refresh"],bool):
                raise ValueError("Manual refresh must be on or off.")
            updated["manual_refresh"]=values["manual_refresh"]
        if updated["auto_send"] and not updated["device_url"]:
            raise ValueError("Add the Note's IP address before enabling automatic sending.")
        with self.lock:
            if updated["calendar_id"] != self.settings["calendar_id"]:
                self.cache={"events":[],"source":"empty"}
                write_json(self.data_dir/"calendar-cache.json",self.cache)
            self.settings=updated
            write_json(self.data_dir/"settings.json",updated)
        return updated

    def sync(self):
        if not self.google.connected:
            raise ValueError("Connect Google Calendar in Settings to enable live refresh. The saved snapshot is still available.")
        if not self.settings["calendar_id"]:
            raise ValueError("Choose your Google calendar ID in Settings before refreshing.")
        if not self.sync_lock.acquire(blocking=False):
            return {"message":"A calendar refresh is already running."}
        try:
            self.last_attempt=self.now()
            calendar_id=self.settings["calendar_id"]
            cache,holidays,holiday_error=self.google.fetch(calendar_id,self.now())
            with self.lock:
                if calendar_id != self.settings["calendar_id"]:
                    return {"message":"Calendar changed during refresh. Refresh the selected calendar again."}
                write_json(self.data_dir/"calendar-cache.json",cache)
                self.cache=cache
                if holidays is not None:
                    write_json(self.data_dir/"holiday-cache.json",holidays)
                    self.holidays=holidays
                self.error=None
                self.holiday_error=holiday_error
            return {"message":"Calendar refreshed."}
        except Exception:
            self.error="Calendar refresh failed. Check your connection or reconnect Google. The last saved calendar is preserved."
            raise
        finally:
            self.sync_lock.release()

    def frame(self, mode="calendar", now=None):
        if mode not in ("calendar","busy","sparse","empty"):
            raise ValueError("Choose Calendar, Busy example, Quiet example or Empty example.")
        now=now or self.now()
        with self.lock:
            if mode == "calendar":
                raw=self.cache.get("events",[])
                clock=now
            else:
                clock=now.replace(hour=7,minute=0,second=0,microsecond=0)
                raw=demo_events(clock,mode)
            events=upcoming(raw,clock)
            holiday=next_holiday(now.date(),self.holidays.get("events",[]))
            frame=render(events,clock,holiday,stale=bool(self.error) and mode=="calendar")
            return frame

    def status(self, mode="calendar"):
        frame=self.frame(mode)
        cache_time=self.cache.get("fetched_at")
        status="live" if self.cache.get("source")=="google" and self.google.connected else "snapshot"
        if self.error:
            status="offline"
        if self.cache.get("source")=="empty":
            status="unconnected"
        with self.lock:
            return {"mode":mode,"source":status,"fetched_at":cache_time,"error":self.error,
                    "holiday_error":self.holiday_error,"holiday_coverage":self.holidays.get("coverage_end"),
                    "settings":self.settings,"google_connected":self.google.connected,"google_configured":self.google.configured,
                    "google_auth_method":self.google.auth_method,
                    "device_error":self.device_error,"last_send":self.last_send,"rows":frame.rows,
                    "shown":len(frame.rows),"total":frame.total_events,"digest":frame.digest,
                    "holiday":None if frame.holiday is None else {"name":frame.holiday.name,"date":frame.holiday.day.isoformat(),"observed":frame.holiday.observed}}

    def scheduled_refresh(self):
        slot=due_update(self.now(),self.last_slot)
        if not slot:
            return
        # Claim this slot before network work, so concurrent device and timer requests agree.
        with self.lock:
            if slot==self.last_slot:
                return
            self.last_slot=slot
            write_json(self.data_dir/"schedule-state.json",{"last_slot":slot})
        if self.google.connected:
            self.sync()

    def device_frame(self,manual=False):
        if manual and self.settings["manual_refresh"] and self.google.connected:
            self.sync()
        else:
            self.scheduled_refresh()
        # The timer may already be fetching this slot. Let the device receive the
        # completed fetch rather than the previous slot's cached events.
        if self.sync_lock.acquire(timeout=45):
            self.sync_lock.release()
        return self.frame()

    def record_device(self,digest):
        self.device_seen={"seen_at":self.now().isoformat(),"displayed_digest":digest,
                          "next_update":next_update(self.now()).isoformat()}
        write_json(self.data_dir/"device-seen.json",self.device_seen)

    def send(self, force=False):
        if not self.device_lock.acquire(blocking=False):
            return {"status":"busy","message":"An image transfer is already running."}
        try:
            # Demo modes never flow to the physical device.
            result=self.device.push(self.settings["device_url"],self.frame(),force)
            self.last_send=result
            self.device_error=None
            return result
        except Exception:
            self.device_error="The Note could not be updated. Wake it, check its IP address and enable LAN service."
            raise
        finally:
            self.device_lock.release()

    def start(self):
        def loop():
            while not self.stopped.is_set():
                try:
                    now=self.now()
                    slot=due_update(now,self.last_slot)
                    self.scheduled_refresh()
                    if slot and self.settings["auto_send"] and not self.error:
                        self.send()
                except Exception:
                    logging.getLogger(__name__).warning("Background refresh did not complete; saved data retained.")
                self.stopped.wait(20)
        thread=threading.Thread(target=loop,name="note-calendar-refresh",daemon=True)
        thread.start()
        return thread
