---
name: Note calendar
description: A compact e-paper agenda and a quiet browser controller for the Note 4c.
colors:
  red: "#871f2b"
  red-dark: "#681a23"
  note-yellow: "#e1b42d"
  note-black: "#191816"
  note-paper: "#f1efe4"
  paper: "#f5f3ed"
  ink: "#292b28"
  muted: "#63665f"
  rule: "#d9d9ce"
  white: "#fffef9"
  focus: "#995d13"
  preview-case: "#fdfcf6"
  secondary-border: "#aeb0a6"
  secondary-hover: "#eae9e1"
  field-border: "#acaea3"
  source-snapshot: "#9b792c"
  source-live: "#487a4a"
typography:
  display:
    fontFamily: "Carlito"
    fontSize: "64px"
    fontWeight: 700
  note-heading:
    fontFamily: "Carlito"
    fontSize: "14px"
    fontWeight: 700
  note-body:
    fontFamily: "Carlito"
    fontSize: "14px"
    fontWeight: 700
    lineHeight: "14px"
  headline:
    fontFamily: '"Segoe UI", system-ui, sans-serif'
    fontSize: "30px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.035em"
  title:
    fontFamily: '"Segoe UI", system-ui, sans-serif'
    fontSize: "17px"
    fontWeight: 650
    lineHeight: 1.35
  body:
    fontFamily: '"Segoe UI", system-ui, sans-serif'
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: '"Segoe UI", system-ui, sans-serif'
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.3
  caption:
    fontFamily: '"Segoe UI", system-ui, sans-serif'
    fontSize: "12px"
    fontWeight: 400
rounded:
  native: "0px"
  scale: "4px"
  field: "5px"
  control: "6px"
  screen: "9px"
  device: "22px"
spacing:
  group-gap: "5px"
  compact: "8px"
  regular: "12px"
  agenda-row: "14px"
  agenda-heading: "14px"
  preview-inset: "24px"
  page-inset: "36px"
  workspace-gap: "44px"
components:
  note-frame:
    backgroundColor: "{colors.note-paper}"
    rounded: "{rounded.native}"
    width: "400px"
    height: "300px"
  note-sidebar:
    backgroundColor: "{colors.red}"
    textColor: "{colors.note-paper}"
    width: "104px"
    height: "300px"
  note-today-date:
    backgroundColor: "{colors.red}"
    textColor: "{colors.note-paper}"
    typography: "{typography.note-heading}"
  note-event:
    textColor: "{colors.note-black}"
    typography: "{typography.note-body}"
    height: "{spacing.agenda-row}"
  button-primary:
    backgroundColor: "{colors.red}"
    textColor: "{colors.white}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "9px 15px"
  button-primary-hover:
    backgroundColor: "{colors.red-dark}"
    textColor: "{colors.white}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "9px 15px"
  button-secondary-hover:
    backgroundColor: "{colors.secondary-hover}"
  button-quiet:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    padding: "8px 12px"
  field:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "8px 10px"
  preview-frame:
    backgroundColor: "{colors.preview-case}"
    rounded: "{rounded.device}"
    padding: "{spacing.preview-inset}"
    width: "848px"
  scale-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.white}"
    rounded: "{rounded.scale}"
---

# Design System: Note calendar

## Overview

**Creative North Star: "The supplied desk calendar"**

The user's original photograph establishes the warm paper field, deep red sidebar, compact agenda, small week strip and holiday illustration. The October 27 refinement replaces the robotic lettering with Carlito and tightens the sidebar date group. This document records the implemented system in [render.py](note_calendar/render.py), [typography.py](note_calendar/typography.py), [art.py](note_calendar/art.py), [index.html](note_calendar/templates/index.html), and [app.css](note_calendar/static/app.css).

The Note output is a dense, glanceable pixel composition. The browser companion supports inspecting that output, reading displayed events, connecting a calendar, and managing the device. Its quiet system typography and restrained controls keep attention on the calendar preview.

**Key Characteristics:**

- A fixed four-color native frame with a strong red date-and-holiday sidebar.
- Proportional sans-serif lettering, single-line events, and date groups that consume available height across years.
- Original geometric holiday sprites with deliberately visible pixel edges.
- A warm, responsive browser workspace with an accessible text equivalent of the preview.

**The Reference Rule.** Preserve the supplied photograph's compact visual language while honoring the user's explicit content changes.

Visual example: [Halloween calendar with fictional events](docs/images/calendar-halloween.png), rendered at 2x by `scripts/render_readme.py`.

## Colors

The native preview approximates printed e-paper ink. Browser controls use a related warm neutral palette. The frontmatter owns their exact values.

### Primary

- **Deep calendar red** (red): the native sidebar, today's date badge, other date headings, browser actions, and links.
- **Pressed red** (red-dark): the browser primary button's hover treatment.

### Secondary

- **E-paper yellow** (note-yellow): small holiday illustration details.
- **Focus ochre** (focus): visible keyboard focus in the browser.
- **Snapshot amber** (source-snapshot) and **live green** (source-live): source-state dots, paired with explanatory text.

### Neutral

- **Printed black** (note-black) and **e-paper cream** (note-paper): the native agenda text and its field, with cream lettering in the red sidebar.
- **Workspace paper** (paper), **browser ink** (ink), and **muted ink** (muted): the page, primary text, and secondary information.
- **Divider gray** (rule): fine section boundaries.
- **Control white** (white) and **case ivory** (preview-case): fields, action text, and the preview surround.
- **Control outlines** (secondary-border, field-border) and **quiet hover paper** (secondary-hover): secondary buttons and inputs.

**The Four Inks Rule.** Native pixels use only palette indices 0 through 3: black, white, yellow, and red. The frame is an indexed image, not an antialiased RGB illustration. The native-color PNG option substitutes pure device colors; the binary frame preserves those same index meanings.

## Typography

The Note renderer reads bundled Carlito TrueType fonts and rasterizes them to solid ink pixels. It does not render browser fonts into the image. The browser uses Segoe UI with system sans-serif fallbacks. Tamzen remains on the firmware setup screen.

- **Native date number:** Carlito Bold at 64px, with approximately 42px ink height.
- **Native headings:** Carlito Bold at 14px for agenda dates; Regular at 14px for weekday and month/year.
- **Native body:** Carlito Bold at 14px for event titles, Regular at 13px for holiday labels and 12px for the time column, and Bold at 11px for week letters. Agenda rows advance 14px.
- **Browser headline:** the headline token on wide screens; it reduces to 27px at 1050px and 25px at 760px.
- **Browser section titles:** the title token for the control rail. Settings use a 23px heading and 16px subsection headings.
- **Browser text:** the body token for the base page, 13px for most control prose, and the caption size for supporting metadata. Schedule times and status values use tabular numerals.

**The Native Pixels Rule.** Rasterize letters to solid palette indices without introducing grayscale or color dithering. Enlarge previews with nearest-neighbor sampling. Keep event titles on one line. Measure actual proportional glyph widths when fitting long text with three periods. Preserve supported route arrows.

## Layout

All Note measurements below refer to native pixels. The frame is 400 by 300 pixels. Its sidebar occupies the left 104 pixels and the agenda occupies the remaining width. The 2x evidence image is an 800 by 600 nearest-neighbor rendering of this same frame.

The sidebar anchors the weekday at (12, 16), the large day at (10, 34), and the month/year at (12, 82), forming one tight date group. The seven-letter week strip uses 12 by 16px cells beginning at (12, 112). Each glyph's visible ink is centered in its cell. Today receives a white cell with a 2px corner radius and a dark letter. Up to three small dots per day indicate event counts. There is no yellow week-progress line.

A holiday sprite sits at (4, 182), followed by its independent date at (12, 253) and up to two name lines beginning at (12, 268). The sprite is 96 by 64 pixels, enlarged from its original 48 by 32 grid.

The agenda starts at (116, 14), fits text within 274px, and stops at the bottom boundary of 288px. Every date label uses weekday, day and month, with no year. Only the current date receives a red badge, using a 3px corner radius and visible-ink padding of 4px horizontally and 3px vertically. Other dates use red text. Group headings and event rows normally advance 14px; actual ink bounds add minimal clearance when accents or the badge require it. Later groups add a 5px spacer, 3px more than the prior layout.

Times occupy the first 52px, followed by an 8px separator area with a 2 by 2px interpunct. Timed titles start at x=176 and fit within 214px. All-day titles omit time and separator and use the full 274px width from x=116. A group is added only when its heading, badge if applicable, and first event fit together. Capacity depends on grouping: the busy fixture shows 13 events, eight distinct date groups fit, and 18 events can fit on a single date. There is no fixed week or year horizon; the date label's omitted year does not affect chronology.

**The Available Height Rule.** Fill the agenda according to the space occupied by real date groups and rows. Do not reserve blank weeks or assume a fixed event count.

The browser uses a centered container with a maximum width of 1328px and 36px page insets. The desktop workspace has a preview column up to 848px, a control column from 240px to 300px, and a 44px gap. The device surround adds 24px around the image; the 1x state caps its outer width at 448px.

Responsive behavior follows the implemented breakpoints:

- At 1400px and wider, the preview surround holds at 848px.
- At 1050px and narrower, the rail is 245px, the workspace gap is 28px, the surround inset is 18px, and settings use two columns.
- At 760px and narrower, the workspace stacks, the page inset becomes 20px, the surround inset becomes 13px, settings use one column, and controls use two columns below the preview.
- At 430px and narrower, controls also use one column.

The browser image retains a 4:3 aspect ratio as it shrinks. The native calendar never reflows to the browser width. A disclosure below the preview exposes the displayed events as ordinary text.

## Elevation & Depth

The native frame is flat: color blocks, pixel silhouettes, and spacing establish hierarchy. The browser adds soft depth only to the device surround, with a faint inset edge around the screen. Controls and content sections remain flat and are separated by fine rules.

**The Device Surround Rule.** Use the existing preview shell's shadows to distinguish the displayed object from its page. Do not add those shadows to agenda groups or control sections.

Exact shadow and focus values live in the sidecar because the frontmatter schema does not carry them. Buttons transition background and text color over 0.15 seconds. Reduced-motion preferences remove transitions.

## Shapes

Native shapes align to the pixel grid. The current-date badge and weekday marker use modest 3px and 2px corner radii. Event dots, the interpunct and holiday artwork remain solid native pixels without smoothing colors.

The browser softens the device object with the device and screen radii from the frontmatter. At the mobile breakpoint these become 17px and 6px. Buttons, inputs, and the selected scale control use their smaller dedicated radii. Status dots are circular; the small wordmark uses a red-and-paper split rectangle.

## Components

### Native calendar

The sidebar combines present-day context with a single upcoming holiday. Dates and artwork are independent. The original sprite set contains lamps, a tree, a crescent, a flag, a harvest shape, a sun, a Halloween pumpkin and cat, and a generic sparkle fallback. Every sprite is drawn with the same four palette indices.

Agenda rows use 12-hour times. All-day rows omit a time prefix. An ongoing event from an earlier day receives an ONGOING prefix when timed. Empty output uses a small red heading with a short body message. Stale output adds a compact saved-calendar status at the bottom.

### Preview and event disclosure

The image is the primary artifact. A preview selector provides the real calendar and illustrative busy, quiet, and empty examples. The 1x/2x scale control uses dark fill for the selected state. A caption reports image dimensions and shown-event count, while examples carry an explicit illustrative label. The event disclosure supplies an accessible list beneath the image.

### Buttons and links

Primary buttons use red fill and light text, secondary buttons use a fine outline, and quiet buttons use text alone. Primary and secondary controls have a minimum height of 42px; quiet controls have a minimum height of 40px, with smaller scale controls at 34px. All retain a visible keyboard focus outline. Disabled buttons reduce opacity and show a waiting cursor.

### Fields and settings

Fields use a light fill, fine border, small corner radius, and a minimum height of 41px. Labels remain visible above them. Settings expand inline beneath the main workspace. Pairing details are separately disclosed in the control rail. Password-style device-key fields stay masked by default.

### Status and control sections

Status combines a small colored dot with text. The control rail uses titled sections, concise explanatory copy, definition-list values, and thin separators. It shows calendar source state, the selected four-check-in schedule, connection actions, and device status. Neutral and error notices use distinct warm backgrounds with readable text and a live status region.

## Do's and Don'ts

### Do:

- **Do** preserve the red sidebar, paper agenda, compact density and small holiday illustration, using the user's revised preference for proportional sans-serif lettering.
- **Do** render the Note frame at 400 by 300 indexed pixels and use nearest-neighbor enlargement.
- **Do** use consistent weekday/day/month labels, single-line events, 12-hour times with an interpunct, untimed all-day titles, and a rounded red badge only for today.
- **Do** let event capacity follow the actual date groups and available height.
- **Do** keep one holiday in the sidebar, with its date independent from its artwork.
- **Do** keep browser source state explicit and pair the preview with readable event text.
- **Do** preserve visible focus, labeled controls, and reduced-motion behavior.

### Don't:

- **Don't** put week numbers, a calendar name, an account email, or a "Next holiday" label on the Note screen.
- **Don't** antialias native text, blur enlarged pixels, or introduce colors outside the four native indices.
- **Don't** turn the busy fixture's 12 displayed events into a fixed product capacity.
- **Don't** stretch the native frame or reflow its agenda at browser breakpoints.
- **Don't** treat a screenshot or documentation label as a new approved visual comp.
- **Don't** use em dashes in product copy or project documentation.

## ESL Hub tab

The deployed controller lives in **Family Calendar - Note4**, directly after Family Calendar in the hub's existing tab strip. The tab retains Bootstrap's selection, keyboard behavior, horizontal overflow and saved-tab behavior. Its direct link is `/?tab=note4`; old `/note/` links open the tab.

The embedded controller adopts the hub's existing dark palette through `static/hub.css`: background `#0d1117`, surface `#161b22`, border `#30363d`, text `#e6edf3`, secondary text `#a8b2bd` and primary action `#1f6feb`. The native four-color calendar image is unchanged. A compact toolbar replaces the standalone wordmark and introductory heading. Settings remain inline. The parent page hides its general configuration action while the Note tab is selected.

The embedded document keeps its settings forms independent of the hub's configuration form. Its height follows the content, including expanded settings and pairing details, so the parent page owns scrolling. It loads when selected and provides a retry action if loading fails. Only the same origin may embed this view; standalone controller pages continue to forbid framing.
