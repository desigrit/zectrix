"""Render the README preview from fictional events, without reading runtime data."""
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from note_calendar.holidays import Holiday
from note_calendar.models import upcoming
from note_calendar.render import render


def readme_frame():
    tz=ZoneInfo("America/Los_Angeles")
    now=datetime(2026,10,31,0,tzinfo=tz)
    examples=[
        ("2026-10-31",10,0,"Pumpkin carving"),
        ("2026-10-31",17,0,"Neighborhood walk"),
        ("2026-10-31",20,0,"Movie night"),
        ("2026-11-01",None,0,"Family day"),
        ("2026-11-01",11,0,"Brunch with friends"),
        ("2026-11-02",9,0,"Weekly planning"),
        ("2026-11-03",18,0,"Library pickup"),
        ("2026-11-05",19,0,"Dinner with friends"),
        ("2026-11-07",9,0,"Farmers market"),
        ("2027-01-01",None,0,"New Year's Day"),
    ]
    events=[]
    for index,(day,hour,minute,title) in enumerate(examples):
        if hour is None:
            start={"date":day}
            end={"date":(date.fromisoformat(day)+timedelta(days=1)).isoformat()}
        else:
            stamp=datetime.fromisoformat(day).replace(hour=hour,minute=minute,tzinfo=tz)
            start={"dateTime":stamp.isoformat()}
            end={"dateTime":(stamp+timedelta(hours=1)).isoformat()}
        events.append({"id":f"readme-example-{index}","summary":title,"start":start,"end":end})
    holiday=Holiday("readme-halloween","Halloween",date(2026,10,31),"halloween","Example")
    return render(upcoming(events,now),now,holiday)


if __name__=="__main__":
    output=Path(__file__).resolve().parent.parent/"docs"/"images"/"calendar-halloween.png"
    output.parent.mkdir(parents=True,exist_ok=True)
    frame=readme_frame()
    output.write_bytes(frame.png(scale=2))
    print(f"Rendered {len(frame.rows)} fictional events to {output}")
