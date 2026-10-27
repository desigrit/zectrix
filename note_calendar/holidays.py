from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from .storage import read_json


@dataclass(frozen=True)
class Holiday:
    id: str
    name: str
    day: date
    art: str
    region: str
    observed: bool = False


# This intentionally selects major holidays instead of every observance in the feed.
INDIAN_HOLIDAYS = {
    "republic day": ("Republic Day", "flag"),
    "pongal": ("Pongal", "sun"),
    "makar sankranti": ("Sankranti", "sun"),
    "maha shivaratri/shivaratri": ("Maha Shivaratri", "festival"),
    "maha shivaratri": ("Maha Shivaratri", "festival"),
    "holi": ("Holi", "festival"),
    "rama navami": ("Ram Navami", "festival"),
    "ram navami": ("Ram Navami", "festival"),
    "vaisakhi": ("Vaisakhi", "sun"),
    "eid ul-fitr": ("Eid al-Fitr", "moon"),
    "ramzan id/eid-ul-fitar": ("Eid al-Fitr", "moon"),
    "bakrid/eid ul-adha": ("Eid al-Adha", "moon"),
    "eid ul-adha": ("Eid al-Adha", "moon"),
    "independence day": ("Independence Day", "flag"),
    "raksha bandhan (rakhi)": ("Raksha Bandhan", "festival"),
    "raksha bandhan": ("Raksha Bandhan", "festival"),
    "janmashtami": ("Janmashtami", "festival"),
    "ganesh chaturthi/vinayaka chaturthi": ("Ganesh Chaturthi", "festival"),
    "ganesh chaturthi": ("Ganesh Chaturthi", "festival"),
    "onam": ("Onam", "festival"),
    "mahatma gandhi jayanti": ("Gandhi Jayanti", "flag"),
    "dussehra": ("Dussehra", "festival"),
    "diwali/deepavali": ("Diwali", "diya"),
    "diwali": ("Diwali", "diya"),
    "guru nanak jayanti": ("Guru Nanak Jayanti", "diya"),
    "christmas": ("Christmas", "tree"),
    "christmas day": ("Christmas", "tree"),
}


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def us_federal(year: int) -> list[Holiday]:
    may_last = date(year, 5, 31)
    values = [
        ("new-year", "New Year's Day", date(year, 1, 1), "festival"),
        ("mlk", "MLK Day", nth_weekday(year, 1, 0, 3), "flag"),
        ("washington", "Washington's Birthday", nth_weekday(year, 2, 0, 3), "flag"),
        ("memorial", "Memorial Day", may_last - timedelta(days=may_last.weekday()), "flag"),
        ("juneteenth", "Juneteenth", date(year, 6, 19), "flag"),
        ("independence", "Independence Day", date(year, 7, 4), "flag"),
        ("labor", "Labor Day", nth_weekday(year, 9, 0, 1), "flag"),
        ("columbus", "Columbus Day", nth_weekday(year, 10, 0, 2), "flag"),
        ("veterans", "Veterans Day", date(year, 11, 11), "flag"),
        ("thanksgiving", "Thanksgiving", nth_weekday(year, 11, 3, 4), "harvest"),
        ("christmas", "Christmas", date(year, 12, 25), "tree"),
    ]
    result = []
    for key, name, day, art in values:
        result.append(Holiday(f"us-{key}-{year}", name, day, art, "US"))
        if day.weekday() in (5, 6):
            observed = day + timedelta(days=-1 if day.weekday() == 5 else 1)
            result.append(Holiday(f"us-{key}-{year}-observed", name, observed, art, "US", True))
    return result


def indian_holidays(raw: list[dict]) -> list[Holiday]:
    result = []
    for row in raw:
        title = row.get("summary", "").strip().casefold()
        match = INDIAN_HOLIDAYS.get(title)
        if match:
            start = row.get("start", "")
            if isinstance(start, dict):
                start = start.get("date", start.get("dateTime", ""))
            try:
                result.append(Holiday(str(row.get("id", title)), match[0], date.fromisoformat(start[:10]), match[1], "IN"))
            except ValueError:
                continue
    return result


def next_holiday(today: date, indian_events: list[dict]) -> Holiday | None:
    holidays = [h for year in range(today.year - 1, today.year + 3) for h in us_federal(year)]
    holidays.extend(indian_holidays(indian_events))
    eligible = sorted((h for h in holidays if h.day >= today), key=lambda h: (h.day, h.observed, h.region, h.name))
    return eligible[0] if eligible else None


def bundled_indian_events() -> dict:
    return read_json(Path(__file__).parent / "assets" / "india-holidays.json", {"events": []})
