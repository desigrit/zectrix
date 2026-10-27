from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from PIL import Image, ImageChops, ImageDraw
from note_calendar.models import upcoming, parse_event
from note_calendar.holidays import next_holiday, us_federal, bundled_indian_events
from note_calendar.render import render, pack_2bpp, unpack_2bpp, wrap_label, AGENDA_RIGHT
from note_calendar.typography import font
from note_calendar.demo import demo_events
from note_calendar.schedule import next_update, due_update, wake_schedule

TZ=ZoneInfo("America/Los_Angeles")
NOW=datetime(2026,10,26,7,0,tzinfo=TZ)


def event(start, end, **extra):
    return {"id":"event","summary":"Sample event","start":start,"end":end,**extra}


def test_excludes_ended_cancelled_declined_keeps_ongoing():
    rows=[event("2026-10-26T06:00:00-07:00","2026-10-26T07:00:00-07:00"),
          event("2026-10-26T06:30:00-07:00","2026-10-26T07:30:00-07:00",id="ongoing"),
          event("2026-10-26T08:00:00-07:00","2026-10-26T09:00:00-07:00",status="cancelled"),
          event("2026-10-26T08:00:00-07:00","2026-10-26T09:00:00-07:00",attendees=[{"self":True,"responseStatus":"declined"}])]
    assert [e.id for e in upcoming(rows,NOW)]==["ongoing"]


def test_all_day_exclusive_end_and_multiday():
    row=event({"date":"2026-10-25"},{"date":"2026-10-27"})
    parsed=upcoming([row],NOW)[0]
    assert parsed.all_day and parsed.day(NOW)==NOW.date()
    assert upcoming([row],datetime(2026,10,27,tzinfo=TZ))==[]


def test_timezone_uses_structured_time_and_dst():
    row=event({"dateTime":"2026-11-02T16:00:00Z"},{"dateTime":"2026-11-02T17:00:00Z"},summary="Meeting at 11 AM")
    parsed=parse_event(row,TZ)
    assert parsed.time_label()=="8 AM"
    assert parsed.title=="Meeting at 11 AM"


def test_busy_capacity_and_no_orphan_headers_or_overflow():
    frame=render(upcoming(demo_events(NOW),NOW),NOW,None)
    assert len(frame.rows)==13
    assert all(row["y"]+12<=288 for row in frame.rows)
    assert len({row["id"] for row in frame.rows})==13
    # Nothing may paint into the right margin, regardless of glyph advances.
    assert set(frame.image.crop((AGENDA_RIGHT,0,400,300)).tobytes())=={1}


def test_single_day_packs_more_than_many_day_groups():
    rows=[event((NOW+timedelta(minutes=i*15)).isoformat(),(NOW+timedelta(minutes=i*15+10)).isoformat(),id=str(i)) for i in range(25)]
    frame=render(upcoming(rows,NOW),NOW,None)
    assert len(frame.rows)==18


def test_sparse_extends_beyond_a_week_and_truncates_long_titles():
    rows=demo_events(NOW,"sparse")
    rows[-1]["summary"]="A very long calendar title "*10
    frame=render(upcoming(rows,NOW),NOW,None)
    assert len(frame.rows)==3 and frame.rows[-1]["date"]=="2026-12-03"
    assert frame.rows[-1]["text"].endswith("...")


def test_compact_agenda_keeps_filling_across_years():
    rows=[]
    for index in range(10):
        start=NOW+timedelta(days=index*60)
        rows.append(event(start.isoformat(),(start+timedelta(hours=1)).isoformat(),id=str(index)))
    frame=render(upcoming(rows,NOW),NOW,None)
    assert len(frame.rows)==8
    assert frame.rows[-1]["date"]==rows[7]["start"][:10]
    assert frame.rows[-1]["date"][:4]=="2027"
    assert frame.rows[-1]["y"]+font().height<=288


def test_proportional_font_clipping_and_route_symbol_keep_solid_inks():
    body=font()
    assert body.measure("iii")<body.measure("WWW")
    for text in ("A long interview title "*8,"SEA \u2192 IST", "W\u00e9dding celebration"):
        clipped=body.fit(text,90)
        assert body.measure(clipped)<=90
    image=Image.new("P",(400,300),1)
    body.draw(image,(12,12),"SEA \u2192 IST",0)
    assert set(image.tobytes())=={0,1}
    assert bytes(body.face.getmask("\u2192"))!=bytes(body.face.getmask("\uffff"))


def test_holiday_words_use_both_lines_before_truncating():
    holiday_font=font(13,"Regular")
    for name in ("New Year's Day","Raksha Bandhan","Maha Shivaratri","Gandhi Jayanti","Columbus Day"):
        lines=wrap_label(name,holiday_font,80)
        assert len(lines)<=2
        assert " ".join(lines)==name
        assert all(holiday_font.measure(line)<=80 for line in lines)


def test_tall_accents_do_not_merge_with_previous_row_descenders():
    rows=[event((NOW+timedelta(hours=i)).isoformat(),(NOW+timedelta(hours=i+1)).isoformat(),
                id=str(i),summary=title) for i,title in enumerate(("gyp","\u00c5ngstr\u00f6m"))]
    frame=render(upcoming(rows,NOW),NOW,None)
    masks=[]
    for row in frame.rows:
        mask=Image.new("1",(400,300))
        font().draw(mask,(row["title_x"],row["y"]),row["title"],1)
        masks.append(mask)
    assert len(masks)==2
    assert ImageChops.logical_and(*masks).getbbox() is None
    assert masks[0].getbbox()[3] < masks[1].getbbox()[1]


def test_first_row_tall_accent_clears_entire_date_badge():
    rows=[event("2026-10-26T08:00:00-07:00","2026-10-26T09:00:00-07:00",summary="\u00c5ngstr\u00f6m")]
    frame=render(upcoming(rows,NOW),NOW,None)
    agenda=frame.image.crop((104,0,400,300))
    left,top,right,bottom=agenda.point([255 if i==3 else 0 for i in range(256)],mode="1").getbbox()
    badge=Image.new("1",frame.image.size)
    ImageDraw.Draw(badge).rectangle((left+104,top,right+103,bottom-1),fill=1)
    title=Image.new("1",frame.image.size)
    font().draw(title,(frame.rows[0]["title_x"],frame.rows[0]["y"]),"\u00c5ngstr\u00f6m",1)
    assert ImageChops.logical_and(title,badge).getbbox() is None


def test_all_day_has_full_width_and_timed_midnight_keeps_time_and_separator():
    rows=[event({"date":"2026-10-27"},{"date":"2026-10-28"},id="all-day",summary="Birthday"),
          event("2026-10-27T00:00:00-07:00","2026-10-27T01:00:00-07:00",id="midnight",summary="Late flight")]
    frame=render(upcoming(rows,NOW),NOW,None)
    all_day,timed=frame.rows
    assert all_day["text"]=="Birthday" and all_day["time"]==""
    assert all_day["title_x"]==116
    assert timed["text"]=="12 AM \u00b7 Late flight"
    assert timed["title_x"]>all_day["title_x"]


def test_future_date_labels_always_include_month_without_year_or_badge():
    rows=[event("2026-10-28T08:00:00-07:00","2026-10-28T09:00:00-07:00"),
          event("2027-05-30T08:00:00-07:00","2027-05-30T09:00:00-07:00",id="next-year")]
    frame=render(upcoming(rows,NOW),NOW,None)
    assert [row["date_label"] for row in frame.rows]==["Wed 28 Oct","Sun 30 May"]
    # Future headers contain red lettering only, never a filled date badge.
    agenda=frame.image.crop((104,0,400,300))
    assert agenda.getpixel((9,14))==1
    assert not any(agenda.getpixel((x,14))==3 for x in range(9,12))


def test_today_badge_has_equal_padding_and_rounded_corners():
    frame=render(upcoming([event("2026-10-26T08:00:00-07:00","2026-10-26T09:00:00-07:00")],NOW),NOW,None)
    agenda=frame.image.crop((104,0,400,300))
    red=agenda.point([255 if i==3 else 0 for i in range(256)],mode="1")
    left,top,right,bottom=red.getbbox()
    # Exclude rounded corners to isolate white text from the paper background.
    inner=agenda.crop((left+3,top+3,right-3,bottom-3))
    ink=inner.point([255 if i==1 else 0 for i in range(256)],mode="1").getbbox()
    il,it,ir,ib=(ink[0]+left+3,ink[1]+top+3,ink[2]+left+3,ink[3]+top+3)
    assert il-left==right-ir==4
    assert it-top==bottom-ib==3
    assert agenda.getpixel((left,top))==1
    assert agenda.getpixel(((left+right)//2,top))==3


def test_weekday_marker_centers_every_visible_glyph():
    for index in range(7):
        frame=render([],NOW+timedelta(days=index),None)
        cell=frame.image.crop((12+index*12,112,24+index*12,128))
        left,top,right,bottom=cell.point([255 if i==0 else 0 for i in range(256)],mode="1").getbbox()
        assert abs(left-(12-right))<=1
        assert abs(top-(16-bottom))<=1


def test_frame_binary_roundtrip_and_color_order():
    image=Image.new("P",(400,300),1)
    for i,color in enumerate([0,1,2,3]):image.putpixel((i,0),color)
    raw=pack_2bpp(image)
    assert len(raw)==30000 and raw[0]==0b00011011
    assert unpack_2bpp(raw).tobytes()==image.tobytes()


def test_holiday_selection_keeps_today_and_filters_minor_observances():
    rows=bundled_indian_events()["events"]
    assert next_holiday(date(2026,10,26),rows).name=="Diwali"
    assert next_holiday(date(2026,11,8),rows).name=="Diwali"
    assert next_holiday(date(2026,11,9),rows).name=="Veterans Day"


def test_federal_observed_date_crosses_year():
    holidays=us_federal(2028)
    assert any(h.day==date(2027,12,31) and h.observed and h.name=="New Year's Day" for h in holidays)
    assert len([h for h in holidays if not h.observed])==11


def test_once_daily_at_midnight_and_no_daytime_refresh():
    assert next_update(NOW)==datetime(2026,10,27,0,tzinfo=TZ)
    midnight=NOW.replace(hour=0,minute=0)
    assert next_update(midnight)==datetime(2026,10,27,0,tzinfo=TZ)
    assert next_update(NOW.replace(hour=23,minute=59,second=59))==datetime(2026,10,27,0,tzinfo=TZ)
    slot=due_update(midnight,None)
    assert slot is not None
    assert due_update(midnight.replace(second=40),slot) is None
    assert due_update(midnight.replace(minute=1),None) is None
    assert all(due_update(NOW.replace(hour=hour),None) is None for hour in range(1,24))


def test_midnight_schedule_handles_both_dst_changes_and_year_rollover():
    for now,hours in ((datetime(2026,11,1,0,tzinfo=TZ),25),
                      (datetime(2026,3,8,0,tzinfo=TZ),23)):
        assert next_update(now).hour==0
        assert next_update(now).timestamp()-now.timestamp()==hours*3600
    assert next_update(datetime(2026,12,31,18,tzinfo=TZ))==datetime(2027,1,1,0,tzinfo=TZ)


def test_cached_wakes_cover_28_consecutive_midnights():
    now=datetime(2026,10,31,18,tzinfo=TZ)
    slots=wake_schedule(now)
    assert len(slots)==28 and slots==sorted(set(slots))
    local=[datetime.fromtimestamp(slot,TZ) for slot in slots]
    assert all((stamp.hour,stamp.minute,stamp.second)==(0,0,0) for stamp in local)
    assert [stamp.date() for stamp in local]==[date(2026,11,1)+timedelta(days=i) for i in range(28)]
