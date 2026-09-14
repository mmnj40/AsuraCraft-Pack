# -*- coding: utf-8 -*-
"""Draws the damage numbers as pictures, with a real outline.

Minecraft's text shadow is a single dark copy one pixel down and to the right - good enough for chat,
but on a number flying over a monster it reads as a smudge on two sides rather than an edge on four.
A drawn glyph can have a proper outline all the way round, which is what every RPG's floating damage
looks like, and it costs the server nothing: the picture is chosen by the client from the pack, and the
server still just sends a short string.

Colour has to be baked in. A bitmap glyph ignores the colour the server asks for, so there is one set
per colour: white for an ordinary hit, gold and larger for a critical.
"""
import io
import json
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
TEXTURES = os.path.join(PACK, "assets", "asuracraft", "textures", "font")
FONTS = os.path.join(PACK, "assets", "asuracraft", "font")
TTF = os.path.join(PACK, "assets", "minecraft", "font", "thai.ttf")

GLYPHS = "0123456789.,KM+"
# white ordinary hits at U+E100, gold criticals at U+E120
SETS = {
    "white": {"first": 0xE100, "size": 13, "fill": (255, 255, 255, 255)},
    "crit":  {"first": 0xE120, "size": 19, "fill": (255, 198, 64, 255)},
}
OUTLINE = (0, 0, 0, 255)


def glyph(character, size, fill):
    """One character: solid colour, hard black outline, no soft edges anywhere."""
    font = ImageFont.truetype(TTF, size)
    pad = 3
    box = font.getbbox(character)
    width = max(1, box[2] - box[0]) + pad * 2
    height = size + pad * 2

    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).text((pad - box[0], pad - box[1]), character, font=font, fill=255)
    # the font is drawn smooth; everything at least half lit becomes solid, so no grey fringe survives
    mask = mask.point(lambda level: 255 if level > 110 else 0)
    ring = mask.filter(ImageFilter.MaxFilter(3))

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    image.paste(OUTLINE, mask=ring)
    image.paste(fill, mask=mask)
    return image


def build(providers):
    for name, spec in SETS.items():
        for index, character in enumerate(GLYPHS):
            file = "num_%s_%02d.png" % (name, index)
            picture = glyph(character, spec["size"], spec["fill"])
            picture.save(os.path.join(TEXTURES, file))
            providers.append({
                "type": "bitmap",
                "file": "asuracraft:font/" + file,
                "ascent": picture.height - 3,
                "height": picture.height,
                "chars": [chr(spec["first"] + index)],
            })
    return providers


if __name__ == "__main__":
    path = os.path.join(FONTS, "ui.json")
    existing = json.load(io.open(path, encoding="utf-8"))["providers"]
    kept = [p for p in existing if p["type"] != "bitmap" or "num_" not in p.get("file", "")]
    with io.open(path, "w", encoding="utf-8") as out:
        json.dump({"providers": build(kept)}, out, ensure_ascii=False, indent=2)
    print("digits", len(GLYPHS) * len(SETS), "glyphs at U+E100 (white) and U+E120 (crit)")
