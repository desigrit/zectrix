from datetime import datetime, timedelta

UPDATE_HOURS=(0,)


def next_update(now: datetime) -> datetime:
    for day_offset in (0,1):
        day=now+timedelta(days=day_offset)
        for hour in UPDATE_HOURS:
            candidate=day.replace(hour=hour,minute=0,second=0,microsecond=0)
            if candidate > now:
                return candidate
    raise AssertionError("A next-day update must exist.")


def due_update(now: datetime, last_slot: str | None) -> str | None:
    # One-minute scheduling window. Do not catch up outside the daily window.
    if now.hour not in UPDATE_HOURS or now.minute != 0:
        return None
    slot=now.replace(minute=0,second=0,microsecond=0).isoformat()
    return slot if slot != last_slot else None


def wake_schedule(now: datetime, count=28) -> list[int]:
    slots=[]
    cursor=now
    for _ in range(count):
        cursor=next_update(cursor)
        slots.append(int(cursor.timestamp()))
    return slots
