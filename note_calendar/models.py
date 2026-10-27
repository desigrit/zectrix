from dataclasses import dataclass
from datetime import date, datetime, time
from zoneinfo import ZoneInfo


def clean_text(value: str) -> str:
    # Normalize typographic punctuation before rendering with a bitmap font.
    return " ".join(str(value).replace(chr(0x2014), "-").replace(chr(0x2013), "-")
                    .replace("\u2018", "'").replace("\u2019", "'")
                    .replace("\u201c", '"').replace("\u201d", '"').split())


@dataclass(frozen=True)
class Event:
    id: str
    title: str
    start: datetime
    end: datetime
    all_day: bool = False

    def day(self, now: datetime) -> date:
        return max(self.start.date(), now.date())

    def time_label(self) -> str:
        if self.all_day:
            return ""
        hour = self.start.hour % 12 or 12
        minutes = f":{self.start.minute:02d}" if self.start.minute else ""
        return f"{hour}{minutes} {'AM' if self.start.hour < 12 else 'PM'}"


def parse_event(raw: dict, timezone: ZoneInfo) -> Event | None:
    if raw.get("status") == "cancelled" or raw.get("my_response_status") == "declined":
        return None
    if any(a.get("self") and a.get("responseStatus") == "declined" for a in raw.get("attendees", [])):
        return None
    start, end = raw.get("start"), raw.get("end")
    if not start or not end:
        return None
    all_day = isinstance(start, dict) and "date" in start
    if isinstance(start, dict):
        start = start.get("dateTime") or start.get("date")
    if isinstance(end, dict):
        end = end.get("dateTime") or end.get("date")
    all_day = all_day or len(start) == 10 or bool(raw.get("all_day"))

    def parse(value):
        if len(value) == 10:
            return datetime.combine(date.fromisoformat(value), time.min, timezone)
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone)
        return result.astimezone(timezone)

    try:
        event = Event(str(raw.get("id", "")), clean_text(raw.get("summary") or "Untitled event"),
                      parse(start), parse(end), all_day)
        return event if event.end > event.start else None
    except (ValueError, TypeError):
        return None


def upcoming(raw_events: list[dict], now: datetime) -> list[Event]:
    parsed = [parse_event(raw, now.tzinfo) for raw in raw_events]
    active = [event for event in parsed if event is not None and event.end > now]
    return sorted(active, key=lambda e: (e.day(now), not e.all_day, e.start, e.title, e.id))
