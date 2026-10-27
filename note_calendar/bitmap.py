"""Small BDF reader. Draw native bitmap glyphs without font smoothing."""
from functools import lru_cache
from pathlib import Path
import unicodedata
from PIL import Image
from .models import clean_text


class BitmapFont:
    def __init__(self, path: Path):
        lines = path.read_text(encoding="ascii").splitlines()
        self.glyphs = {}
        self.ascent = 0
        glyph = None
        bitmap = False
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            key = parts[0]
            if key == "FONTBOUNDINGBOX":
                self.width, self.height = map(int, parts[1:3])
            elif key == "FONT_ASCENT":
                self.ascent = int(parts[1])
            elif key == "STARTCHAR":
                glyph = {"rows": []}
            elif key == "ENDCHAR":
                self.glyphs[glyph["code"]] = glyph
                glyph, bitmap = None, False
            elif glyph is not None:
                if bitmap:
                    glyph["rows"].append(line)
                elif key == "ENCODING":
                    glyph["code"] = int(parts[1])
                elif key == "BBX":
                    glyph["box"] = tuple(map(int, parts[1:]))
                elif key == "BITMAP":
                    bitmap = True

    def normalize(self, text: str) -> str:
        result = ""
        for char in clean_text(text):
            if ord(char) in self.glyphs:
                result += char
            else:
                ascii_char = unicodedata.normalize("NFKD", char).encode("ascii", "ignore").decode()
                result += ascii_char or "?"
        return result

    def measure(self, text: str, scale=1) -> int:
        return len(self.normalize(text)) * self.width * scale

    def fit(self, text: str, width: int) -> str:
        text = self.normalize(text)
        maximum = max(0, width // self.width)
        return text if len(text) <= maximum else text[:max(0, maximum - 3)].rstrip() + "." * min(3, maximum)

    def draw(self, image, xy, text, color, scale=1):
        x, y = xy
        for char in self.normalize(text):
            glyph = self.glyphs.get(ord(char), self.glyphs[ord("?")])
            width, height, dx, dy = glyph["box"]
            for row, hex_value in enumerate(glyph["rows"]):
                bits = int(hex_value, 16)
                bit_count = len(hex_value) * 4
                for column in range(width):
                    if bits & (1 << (bit_count - column - 1)):
                        left = x + (dx + column) * scale
                        top = y + (self.ascent - height - dy + row) * scale
                        image.paste(color, (left, top, left + scale, top + scale))
            x += self.width * scale


@lru_cache(maxsize=4)
def font(size="6x12"):
    return BitmapFont(Path(__file__).parent / "assets" / "fonts" / f"Tamzen{size}b.bdf")
