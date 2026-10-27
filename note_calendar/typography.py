"""Proportional lettering rasterized directly to the Note's solid ink palette."""
from functools import lru_cache
from math import ceil
from pathlib import Path

from PIL import ImageDraw, ImageFont

from .models import clean_text


class ScreenFont:
    def __init__(self, size, weight):
        path = Path(__file__).parent / "assets" / "fonts" / f"Carlito-{weight}.ttf"
        self.face = ImageFont.truetype(str(path), size)
        bounds = self.face.getbbox("Ag", anchor="ls")
        self.ascent = -bounds[1]
        self.height = bounds[3] - bounds[1]

    def ink_box(self, text):
        text = clean_text(text)
        mask, offset = self.face.getmask2(text, mode="1", anchor="ls")
        bounds = mask.getbbox()
        if bounds is None:
            return 0, 0, 0, 0
        left = min(0,self.face.getbbox(text,anchor="ls")[0])
        return (offset[0]-left+bounds[0],offset[1]+self.ascent+bounds[1],
                offset[0]-left+bounds[2],offset[1]+self.ascent+bounds[3])

    def ink_bounds(self, text):
        _, top, _, bottom = self.ink_box(text)
        return top, bottom

    def measure(self, text):
        text = clean_text(text)
        if not text:
            return 0
        bounds = self.face.getbbox(text, anchor="ls")
        return ceil(max(self.face.getlength(text), bounds[2]) - min(0, bounds[0]))

    def fit(self, text, width):
        text = clean_text(text)
        if self.measure(text) <= width:
            return text
        suffix = "..."
        while suffix and self.measure(suffix) > width:
            suffix = suffix[:-1]
        low, high = 0, len(text)
        while low < high:
            middle = (low + high + 1) // 2
            if self.measure(text[:middle].rstrip() + suffix) <= width:
                low = middle
            else:
                high = middle - 1
        return text[:low].rstrip() + suffix

    def draw(self, image, xy, text, color):
        text = clean_text(text)
        left = min(0, self.face.getbbox(text, anchor="ls")[0])
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1"
        draw.text((xy[0] - left, xy[1] + self.ascent), text,
                  font=self.face, fill=color, anchor="ls")


@lru_cache(maxsize=12)
def font(size=14, weight="Bold"):
    return ScreenFont(size, weight)
