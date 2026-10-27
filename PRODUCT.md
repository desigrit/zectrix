# Note calendar

<!-- impeccable:product-schema 1 -->

## Platform

web

The browser is a local control surface. The product output is a 400 x 300 pixel image for a Zectrix Note 4c.

## Stack

Python, Pillow, Flask, and a small HTML/CSS/JavaScript control surface. A Raspberry Pi hosts the controller. Arduino/ESP32-S3 firmware handles scheduled wake, image fetch and deep sleep.

## Users and purpose

A personal, glanceable desk calendar. Show upcoming events from a selected Google calendar, plus one upcoming US federal or major Indian holiday. Microsoft To Do belongs on a separate future page, with editing on phone or computer.

## Operating context

Note 4c: 400 x 300 pixels, black/white/red/yellow, slow full-screen refresh. Do not assume fast cursor movement or partial refresh. This build produces compatible image files and supports the reference firmware's local image-upload API. Hardware connection and installed firmware must be verified before claiming a physical display update.

## Confirmed constraints

- Preserve the reference's compact agenda, red sidebar and holiday illustration. Use clean proportional sans-serif lettering instead of a robotic bitmap style.
- Typography preference: Calibri-like lettering with the reference's stronger event text. Carlito Bold is used for event titles and date headings, with regular times and sidebar labels. Source Sans was rejected.
- Show day and date in place of week numbers.
- No calendar title, account email or "Next holiday" label on the Note.
- Fill the available height with upcoming events, including following years, without a fixed week or year horizon. Keep rows compact instead of expanding their spacing to fill a quiet calendar.
- Group weekday, large date and month/year closely in the sidebar. Balance the date, weekday strip and holiday as separate groups.
- Single-line event titles and 12-hour times separated from titles by an interpunct. All-day events omit time and start at the agenda's left edge.
- Every agenda label uses weekday, day and month, such as Wed 28 Oct, without a year. Full dates remain available to sorting and filtering.
- Highlight only the actual current date, with a rounded red badge padded evenly around the visible letters. Center the white weekday marker around each glyph.
- Keep event rows compact and add 3px between date groups compared with the prior layout (5px group spacer).
- One holiday in the sidebar. Dates and artwork are independent.
- No em dashes in product copy or project documentation.

## Implementation defaults

- America/Los_Angeles timezone; ongoing events remain until they end.
- User-selected schedule: once daily at midnight (12 AM), America/Los_Angeles, including daylight saving changes. Mostly battery power.
- Calendar-first build. To Do integration and button behavior remain a separate build step.
- Read-only Google service account or Desktop OAuth access for unattended refresh. A connector snapshot can seed the preview but is explicitly labeled as a snapshot.
- Bundled Indian holiday dates are a cache from the existing holiday calendar, filtered to a documented selection. The selected Indian holidays are listed in `note_calendar/holidays.py`.

## Evidence

Public example: [Halloween calendar with fictional events](docs/images/calendar-halloween.png).
Hardware and transfer specification: https://wiki.zectrix.com/en/hardware/note4c/quick-start and https://github.com/LazyYoun/youn-ink-fourcolor-firmware/blob/2bp/docs/LAN_PHOTO_PUSH_API.md.

## Hub integration

The controller belongs inside ESL Hub as a tab named **Family Calendar - Note4**, beside Family Calendar. It uses the hub's dark appearance and contains the Note preview, settings and pairing controls.
