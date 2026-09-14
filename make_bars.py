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

WIDTH, HEIGHT = 80, 9
STEPS = 10
FIRST = 0xE010                      # E010..E01A: bars for a monster's name tag
HUD_FIRST = 0xE020                  # E020..E02A: the same bars, lifted to the top of the screen
HUD_ASCENT = 100                    # how far above the text line the HUD is drawn
# A "space" font: characters whose only job is to move the pen, including backwards. This is what lets
# a HUD sit anywhere across the screen - the text is still sent through the action bar, but the pen is
# walked left before the picture is drawn. Powers of two compose any offset, like binary.
SPACE = {0xF801: -1, 0xF802: -2, 0xF804: -4, 0xF808: -8, 0xF810: -16, 0xF820: -32,
         0xF840: -64, 0xF880: -128, 0xF901: 1, 0xF902: 2, 0xF904: 4, 0xF908: 8,
         0xF910: 16, 0xF920: 32, 0xF940: 64, 0xF980: 128}

EDGE = (18, 18, 22, 255)
EMPTY = (58, 58, 64, 255)
GLOSS = (255, 255, 255, 90)
# three bars, three jobs: blood, magic, breath. Each is a dark-to-light pair so the fill is shaded
# rather than flat - flat colour reads as a sticker pasted on the screen.
KINDS = {
    "hp":   {"low": (196, 44, 36, 255),  "high": (255, 108, 92, 255),  "hud": 0xE020},
    "mana": {"low": (38, 92, 200, 255),  "high": (110, 176, 255, 255), "hud": 0xE030},
    "stam": {"low": (188, 150, 32, 255), "high": (252, 222, 108, 255), "hud": 0xE040},
}


def bar(step, kind="hp"):
    """One bar, filled step/10 of the way, in one of the three colours."""
    low = KINDS[kind]["low"]
    high = KINDS[kind]["high"]
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, WIDTH - 1, HEIGHT - 1], fill=EDGE)
    draw.rectangle([1, 1, WIDTH - 2, HEIGHT - 2], fill=EMPTY)

    inner = WIDTH - 4
    filled = round(inner * step / STEPS)
    if filled > 0:
        # a hint of a gradient down the bar: flat red reads as a sticker, shaded red reads as a bar
        for y in range(2, HEIGHT - 2):
            share = (y - 2) / max(1, HEIGHT - 5)
            colour = tuple(round(high[i] + (low[i] - high[i]) * share) for i in range(4))
            draw.line([(2, y), (1 + filled, y)], fill=colour)
        draw.line([(2, 2), (1 + filled, 2)], fill=GLOSS)
    return image


def main():
    os.makedirs(TEXTURES, exist_ok=True)
    os.makedirs(FONTS, exist_ok=True)
    providers = []
    for kind in KINDS:
        for step in range(STEPS + 1):
            name = "bar_%s_%02d.png" % (kind, step)
            bar(step, kind).save(os.path.join(TEXTURES, name))
            # once low on the screen, for a monster's name tag (health only), and once high, for the HUD
            if kind == "hp":
                providers.append({"type": "bitmap", "file": "asuracraft:font/" + name,
                                  "ascent": 8, "height": HEIGHT, "chars": [chr(FIRST + step)]})
            providers.append({"type": "bitmap", "file": "asuracraft:font/" + name,
                              "ascent": HUD_ASCENT, "height": HEIGHT,
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
