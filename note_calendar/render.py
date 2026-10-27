from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from io import BytesIO
from PIL import Image, ImageDraw
from .art import holiday_art
from .typography import font
from .holidays import Holiday
from .models import Event

WIDTH, HEIGHT, SIDEBAR = 400, 300, 104
AGENDA_LEFT, AGENDA_TOP, AGENDA_RIGHT, AGENDA_BOTTOM = SIDEBAR + 12, 14, 390, 288
HEADING_STEP, ROW_STEP, GROUP_GAP, TIME_COLUMN = 14, 14, 5, 52
SEPARATOR_SPACE = 8
BADGE_PAD_X, BADGE_PAD_Y = 4, 3
BLACK, WHITE, YELLOW, RED = range(4)
# Color indices are the hardware codes. RGB approximates printed e-paper ink.
PALETTE = [(25, 24, 22), (241, 239, 228), (225, 180, 45), (135, 31, 43)]


@dataclass
class Frame:
    image: Image.Image
    rows: list[dict]
    total_events: int
    holiday: Holiday | None

    def png(self, scale=1, native_colors=False) -> bytes:
        image = self.image.copy()
        if native_colors:
            colors = [(0,0,0),(255,255,255),(255,255,0),(255,0,0)]
            image.putpalette([c for rgb in colors for c in rgb] + [0] * (768 - 12))
        if scale != 1:
            image = image.resize((WIDTH * scale, HEIGHT * scale), Image.Resampling.NEAREST)
        output = BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def binary(self) -> bytes:
        return pack_2bpp(self.image)

    @property
    def digest(self):
        return sha256(self.binary()).hexdigest()


def pack_2bpp(image: Image.Image) -> bytes:
    if image.mode != "P" or image.size != (WIDTH, HEIGHT):
        raise ValueError("Expected a 400 x 300 indexed frame.")
    pixels = image.tobytes()
    if any(pixel > 3 for pixel in pixels):
        raise ValueError("The frame contains colors outside the Note palette.")
    return bytes((pixels[i] << 6) | (pixels[i+1] << 4) | (pixels[i+2] << 2) | pixels[i+3]
                 for i in range(0, len(pixels), 4))


def unpack_2bpp(raw: bytes) -> Image.Image:
    if len(raw) != 30000:
        raise ValueError("A Note 4c frame must contain exactly 30,000 bytes.")
    image = Image.frombytes("P", (WIDTH, HEIGHT), bytes((value >> shift) & 3 for value in raw for shift in (6,4,2,0)))
    image.putpalette([c for rgb in PALETTE for c in rgb] + [0] * (768 - 12))
    return image


def wrap_label(text: str, label_font, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        if line and label_font.measure(f"{line} {word}") > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def render(events: list[Event], now: datetime, holiday: Holiday | None, stale=False) -> Frame:
    image = Image.new("P", (WIDTH, HEIGHT), WHITE)
    image.putpalette([c for rgb in PALETTE for c in rgb] + [0] * (768 - 12))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, SIDEBAR - 1, HEIGHT - 1), fill=RED)
    body, heading, time_font = font(), font(14, "Bold"), font(12,"Regular")
    font(14,"Regular").draw(image, (12, 16), now.strftime("%A"), WHITE)
    font(64, "Bold").draw(image, (10, 34), str(now.day), WHITE)
    font(14,"Regular").draw(image, (12, 82), now.strftime("%b %Y"), WHITE)

    monday = now.date() - timedelta(days=now.weekday())
    counts = Counter(e.day(now) for e in events)
    week_font = font(11,"Bold")
    for index, letter in enumerate("MTWTFSS"):
        left, top, right, bottom = 12+index*12,112,24+index*12,128
        ink_left, ink_top, ink_right, ink_bottom = week_font.ink_box(letter)
        letter_x = left + (right-left-(ink_right-ink_left))//2-ink_left
        letter_y = top + (bottom-top-(ink_bottom-ink_top))//2-ink_top
        is_today = index == now.weekday()
        if is_today:
            draw.rounded_rectangle((left,top,right-1,bottom-1),radius=2,fill=WHITE)
        week_font.draw(image,(letter_x,letter_y),letter,BLACK if is_today else WHITE)
        for dot in range(min(3, counts[monday + timedelta(days=index)])):
            center_x = (left+right)//2
            draw.rectangle((center_x-1,134+dot*4,center_x,135+dot*4),fill=WHITE)

    if holiday:
        holiday_font = font(13,"Regular")
        image.paste(holiday_art(holiday.art), (4,182))
        date_label = f"{holiday.day.day} {holiday.day.strftime('%b')}"
        if holiday.observed:
            date_label += " OBS."
        holiday_font.draw(image,(12,253),date_label,WHITE)
        for index,line in enumerate(wrap_label(holiday.name,holiday_font,SIDEBAR-24)[:2]):
            holiday_font.draw(image,(12,268+index*13),holiday_font.fit(line,SIDEBAR-24),WHITE)

    x, y, right, bottom = AGENDA_LEFT, AGENDA_TOP, AGENDA_RIGHT, AGENDA_BOTTOM
    rows = []
    current_day = None
    previous_ink_bottom = 0
    for event in events:
        day = event.day(now)
        new_group = day != current_day
        heading_y = y + (GROUP_GAP if current_day is not None else 0)
        row_y = y
        preceding_bottom = previous_ink_bottom
        badge = None
        if new_group:
            label = f"{day.strftime('%a')} {day.day} {day.strftime('%b')}"
            heading_left, heading_top, heading_right, heading_bottom = heading.ink_box(label)
            is_today = day == now.date()
            decoration_top = heading_top-BADGE_PAD_Y if is_today else heading_top
            heading_y = max(heading_y, preceding_bottom+1-decoration_top)
            preceding_bottom = heading_y + heading_bottom
            if is_today:
                badge = (x+heading_left-BADGE_PAD_X,heading_y+heading_top-BADGE_PAD_Y,
                         x+heading_right+BADGE_PAD_X,heading_y+heading_bottom+BADGE_PAD_Y)
                preceding_bottom = badge[3]
            row_y = heading_y + HEADING_STEP

        time_label = event.time_label()
        if event.start.date() < now.date():
            time_label = "Ongoing" if not event.all_day else ""
        title_x = x+TIME_COLUMN+SEPARATOR_SPACE if time_label else x
        title = body.fit(event.title, right-title_x)
        time_offset = body.ascent-time_font.ascent
        title_top, title_bottom = body.ink_bounds(title)
        time_top, time_bottom = time_font.ink_bounds(time_label)
        ink_top = min(title_top,time_top+time_offset)
        ink_bottom = max(title_bottom,time_bottom+time_offset)
        # Tall accents receive only the extra pixels needed to clear prior ink.
        row_y = max(row_y,preceding_bottom+1-ink_top)
        if row_y + max(ROW_STEP,ink_bottom) > bottom:
            break

        if new_group:
            if badge is not None:
                draw.rounded_rectangle((badge[0],badge[1],badge[2]-1,badge[3]-1),radius=3,fill=RED)
                heading.draw(image,(x,heading_y),label,WHITE)
            else:
                heading.draw(image,(x,heading_y),label,RED)
            current_day = day
        time_font.draw(image,(x,row_y+time_offset),time_label,BLACK)
        if time_label:
            dot_top = row_y + body.ascent - 4
            draw.ellipse((x+TIME_COLUMN,dot_top,x+TIME_COLUMN+1,dot_top+1),fill=BLACK)
        body.draw(image,(title_x,row_y),title,BLACK)
        text = f"{time_label} \u00b7 {title}" if time_label else title
        rows.append({"id":event.id,"title":event.title,"text":text,"date":day.isoformat(),
                     "date_label":label,"time":event.time_label(),"all_day":event.all_day,
                     "y":row_y,"title_x":title_x})
        previous_ink_bottom = row_y + ink_bottom
        y = row_y + ROW_STEP

    if not rows:
        heading.draw(image,(x,24),"A little open space",RED)
        body.draw(image,(x,46),"No upcoming events.",BLACK)
    if stale:
        font(10).draw(image,(x,290),"Offline - saved calendar",BLACK)
    return Frame(image, rows, len(events), holiday)
