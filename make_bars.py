# -*- coding: utf-8 -*-
"""Draws the health bars that sit over a monster's head, as font glyphs.

Minecraft will draw any picture you like in a name tag, as long as the picture is pretending to be a
letter. A bitmap font provider maps a character to a PNG, so a name tag that contains one private-use
character comes out as a 80x9 image of a health bar - no extra entity, no packets of our own, and it
follows the mob for free because it IS the mob's name.

Eleven glyphs, one per tenth, is enough: the eye cannot tell 63% from 67% on a bar this size, and eleven
pictures cost nothing next to one display entity per monster.
"""
import io
import json
import os
import zipfile

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
TEXTURES = os.path.join(PACK, "assets", "asuracraft", "textures", "font")
FONTS = os.path.join(PACK, "assets", "asuracraft", "font")

WIDTH, HEIGHT = 76, 7
STEPS = 10
FIRST = 0xE010                      # E010..E01A: bars for a monster's name tag
HUD_FIRST = 0xE020                  # E020..E02A: the same bars, lifted to the top of the screen
# How far above the text line the HUD is drawn.
#
# It cannot simply be an ascent of 100: the client validates that ascent <= height (checked in
# BitmapProvider$Definition in the 26.2 jar), and a provider that fails validation is thrown away whole,
# which is why every glyph in the font came out as an empty square. So the picture is given a tall
# transparent canvas instead, with the bar at the very top: height and ascent both equal the canvas, and
# the bar ends up LIFT pixels above the line because that is how much empty space is under it.
HUD_LIFT = 100
# A "space" font: characters whose only job is to move the pen, including backwards. This is what lets
# a HUD sit anywhere across the screen - the text is still sent through the action bar, but the pen is
# walked left before the picture is drawn. Powers of two compose any offset, like binary.
SPACE = {0xF801: -1, 0xF802: -2, 0xF804: -4, 0xF808: -8, 0xF810: -16, 0xF820: -32,
         0xF840: -64, 0xF880: -128, 0xF901: 1, 0xF902: 2, 0xF904: 4, 0xF908: 8,
         0xF910: 16, 0xF920: 32, 0xF940: 64, 0xF980: 128}

# Flat, thin, and slightly see-through, the way a bar in Albion or BDO sits on the screen: it is meant
# to be read without being looked at. A glossy bar with a gradient reads as a sticker pasted over the
# world - which is exactly how the first version looked.
EDGE = (10, 10, 13, 230)
EMPTY = (28, 28, 32, 150)
# three bars, three jobs: blood, magic, breath. Each is a dark-to-light pair so the fill is shaded
# rather than flat - flat colour reads as a sticker pasted on the screen.
# Each bar is lifted a different amount so the two can be stacked: a line of text runs sideways, so
# two pictures at the same height would simply sit on top of each other - which they did.
KINDS = {
    "hp":   {"fill": (176, 46, 42, 235),  "hud": 0xE020, "lift": 100},
    "mana": {"fill": (46, 96, 178, 235),  "hud": 0xE030, "lift": 90},
}


def bar(step, kind="hp", lift=0):
    """One bar, filled step/10 of the way. Flat: one colour, one thin outline, nothing else."""
    image = Image.new("RGBA", (WIDTH, HEIGHT + lift), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, WIDTH - 1, HEIGHT - 1], fill=EDGE)
    draw.rectangle([1, 1, WIDTH - 2, HEIGHT - 2], fill=EMPTY)
    inner = WIDTH - 2
    filled = round(inner * step / STEPS)
    if filled > 0:
        draw.rectangle([1, 1, filled, HEIGHT - 2], fill=KINDS[kind]["fill"])
    return image


def main():
    os.makedirs(TEXTURES, exist_ok=True)
    os.makedirs(FONTS, exist_ok=True)
    providers = []
    for kind in KINDS:
        for step in range(STEPS + 1):
            name = "bar_%s_%02d.png" % (kind, step)
            hud_name = "hud_%s_%02d.png" % (kind, step)
            bar(step, kind).save(os.path.join(TEXTURES, name))
            bar(step, kind, KINDS[kind]["lift"]).save(os.path.join(TEXTURES, hud_name))
            # once low on the screen, for a monster's name tag (health only), and once high, for the HUD
            if kind == "hp":
                providers.append({"type": "bitmap", "file": "asuracraft:font/" + name,
                                  "ascent": 8, "height": HEIGHT, "chars": [chr(FIRST + step)]})
            providers.append({"type": "bitmap", "file": "asuracraft:font/" + hud_name,
                              "ascent": HEIGHT + KINDS[kind]["lift"],
                              "height": HEIGHT + KINDS[kind]["lift"],
                              "chars": [chr(KINDS[kind]["hud"] + step)]})
    providers.append({
        "type": "space",
        "advances": {chr(code): width for code, width in SPACE.items()},
    })
    with io.open(os.path.join(FONTS, "ui.json"), "w", encoding="utf-8") as out:
        json.dump({"providers": providers}, out, ensure_ascii=False, indent=2)

    # rebuild the pack the server hands out
    zip_path = os.path.join(HERE, "AsuraCraft-Thai.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as pack:
        for folder, _, files in os.walk(PACK):
            for name in files:
                full = os.path.join(folder, name)
                pack.write(full, os.path.relpath(full, PACK).replace("\\", "/"))
    print("bars   ", STEPS + 1, "glyphs at U+%04X..U+%04X" % (FIRST, FIRST + STEPS))
    print("pack   ", zip_path, os.path.getsize(zip_path), "bytes")


if __name__ == "__main__":
    main()
