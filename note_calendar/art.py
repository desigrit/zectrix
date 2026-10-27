"""Original geometric pixel sprites, drawn on a 48 x 32 grid."""
from PIL import Image, ImageDraw

BLACK, WHITE, YELLOW, RED = range(4)


def holiday_art(kind: str) -> Image.Image:
    sprite = Image.new("P", (48, 32), RED)
    draw = ImageDraw.Draw(sprite)

    def spark(x, y, color=YELLOW):
        draw.rectangle((x - 2, y, x + 2, y), fill=color)
        draw.rectangle((x, y - 2, x, y + 2), fill=color)

    if kind == "diya":
        # Two stepped clay-lamp silhouettes with separate flame and wick pixels.
        for x, y, width in [(15, 24, 12), (35, 26, 9)]:
            draw.polygon([(x-width,y-4),(x+width,y-4),(x+width-2,y+1),
                          (x+width-5,y+5),(x-width+5,y+5),(x-width+2,y+1)], fill=BLACK)
            draw.rectangle((x-width+1,y-5,x+width-1,y-3), fill=WHITE)
            draw.rectangle((x-width+4,y-2,x+width-4,y-1), fill=YELLOW)
            draw.rectangle((x-1,y-9,x,y-5), fill=BLACK)
            draw.polygon([(x,y-20),(x+3,y-15),(x+4,y-11),(x+2,y-8),
                          (x-2,y-8),(x-4,y-11),(x-3,y-15)], fill=YELLOW)
            draw.rectangle((x-1,y-13,x,y-9), fill=WHITE)
        spark(30, 5)
        spark(4, 13, WHITE)
        spark(44, 12)
    elif kind == "halloween":
        # A jack-o'-lantern and a black cat, using the same four display inks.
        draw.rectangle((15,8,18,13),fill=BLACK)
        draw.polygon([(16,8),(18,5),(21,5),(19,9)],fill=YELLOW)
        draw.polygon([(9,12),(23,12),(28,17),(29,24),(25,29),(8,29),(4,24),(5,17)],fill=YELLOW)
        draw.polygon([(10,16),(7,21),(13,21)],fill=BLACK)
        draw.polygon([(22,16),(19,21),(25,21)],fill=BLACK)
        draw.polygon([(9,24),(13,26),(16,24),(20,26),(24,23),(22,28),(12,28)],fill=BLACK)
        draw.arc((36,16,47,30),270,110,fill=BLACK,width=3)
        draw.ellipse((29,19,41,30),fill=BLACK)
        draw.polygon([(29,16),(28,6),(34,10),(37,10),(42,5),(42,17)],fill=BLACK)
        draw.ellipse((28,10,42,22),fill=BLACK)
        draw.rectangle((30,14,33,16),fill=WHITE)
        draw.rectangle((37,14,40,16),fill=WHITE)
        draw.point((32,15),fill=BLACK)
        draw.point((38,15),fill=BLACK)
        draw.point((35,19),fill=YELLOW)
        draw.rectangle((3,30,43,31),fill=BLACK)
        draw.polygon([(2,4),(5,6),(8,3),(11,6),(14,4),(12,8),(8,7),(4,8)],fill=BLACK)
        spark(24,3,WHITE)
        spark(45,12)
    elif kind == "tree":
        draw.rectangle((23, 25, 26, 30), fill=BLACK)
        for y, width in [(7, 5), (13, 9), (19, 13)]:
            draw.polygon([(24, y-5), (24+width,y+6), (24-width,y+6)], fill=WHITE)
        for x,y in [(20,14),(28,18),(17,24),(30,25)]:
            draw.rectangle((x,y,x+1,y+1), fill=YELLOW)
        spark(24, 2)
        spark(6, 11)
        spark(40, 7)
    elif kind == "moon":
        draw.ellipse((9, 1, 35, 27), fill=YELLOW)
        draw.ellipse((17, 0, 38, 21), fill=RED)
        draw.rectangle((8, 29, 39, 30), fill=BLACK)
        spark(35, 5, WHITE)
        spark(42, 15)
    elif kind == "flag":
        draw.rectangle((11, 3, 12, 30), fill=BLACK)
        draw.rectangle((13, 4, 36, 19), fill=WHITE)
        for y in range(5, 20, 4):
            draw.rectangle((13,y,36,y+1), fill=YELLOW)
        draw.rectangle((13,4,22,11), fill=BLACK)
        for x,y in [(15,6),(19,6),(17,9)]:
            draw.point((x,y),fill=WHITE)
        draw.rectangle((7,30,17,31),fill=BLACK)
        spark(41,5)
    elif kind == "harvest":
        draw.ellipse((8,11,37,30), fill=YELLOW)
        draw.rectangle((22,6,25,13),fill=BLACK)
        for x in (15,24,32):
            draw.line((x,13,x,27),fill=BLACK)
        spark(6,5,WHITE)
        spark(39,8)
    elif kind == "sun":
        draw.ellipse((15,7,32,24),fill=YELLOW)
        for x,y in [(24,1),(24,30),(7,15),(40,15),(11,4),(37,27),(11,27),(37,4)]:
            draw.rectangle((x,y,x+1,y+1),fill=WHITE)
        draw.rectangle((8,30,39,31),fill=BLACK)
    else:
        for x,y in [(13,10),(34,7),(25,22)]:
            spark(x,y)
            for dx,dy in [(-5,-5),(5,-5),(-5,5),(5,5)]:
                draw.rectangle((x+dx,y+dy,x+dx+1,y+dy+1),fill=WHITE)
        draw.rectangle((8,30,40,31),fill=BLACK)
    return sprite.resize((96, 64), Image.Resampling.NEAREST)
