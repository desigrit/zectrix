"""Compile the bundled bitmap font into the setup screen's small C++ table."""
from pathlib import Path
from note_calendar.bitmap import font

f=font()
lines=["#pragma once", "#include <stdint.h>", "// Tamzen font, see note_calendar/assets/fonts/LICENSE.txt", "static const uint8_t FONT6X12[95][12] = {"]
for code in range(32,127):
    glyph=f.glyphs[code]
    width,height,dx,dy=glyph["box"]
    rows=[0]*12
    for i,value in enumerate(glyph["rows"]):
        y=f.ascent-height-dy+i
        if 0<=y<12: rows[y]=int(value,16)
    lines.append("  {"+",".join(f"0x{x:02x}" for x in rows)+"},")
lines.append("};")
Path("firmware/include/font6x12.h").write_text("\n".join(lines)+"\n",encoding="ascii")
