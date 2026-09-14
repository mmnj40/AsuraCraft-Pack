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
FIRST = 0xE010                      # E010..E01A are the eleven bars

EDGE = (18, 18, 22, 255)
EMPTY = (58, 58, 64, 255)
FILL_LOW = (196, 44, 36, 255)
FILL_HIGH = (255, 108, 92, 255)
GLOSS = (255, 170, 160, 110)


def bar(step):
    """One bar, filled step/10 of the way."""
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
            colour = tuple(round(FILL_HIGH[i] + (FILL_LOW[i] - FILL_HIGH[i]) * share) for i in range(4))
            draw.line([(2, y), (1 + filled, y)], fill=colour)
        draw.line([(2, 2), (1 + filled, 2)], fill=GLOSS)
    return image


def main():
    os.makedirs(TEXTURES, exist_ok=True)
    os.makedirs(FONTS, exist_ok=True)
    providers = []
    for step in range(STEPS + 1):
        name = "bar_%02d.png" % step
        bar(step).save(os.path.join(TEXTURES, name))
        providers.append({
            "type": "bitmap",
            "file": "asuracraft:font/" + name,
            "ascent": 8,
            "height": HEIGHT,
            "chars": [chr(FIRST + step)],
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
