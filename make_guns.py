# -*- coding: utf-8 -*-
"""Draws the guns flat, and tells the hand how to hold them.

Two wrong turns got here, and both are worth writing down.

The first drew them flat and used the stock `handheld` display, which is a sword's display: a sword is
meant to point up and forward out of the fist, so the gun did too. The second redrew them along the
diagonal to suit that display - which fixed the angle and broke everything else, because the axis a
magazine hangs from is no longer down once the whole sprite has been turned forty-five degrees.

The right answer is the plain one: draw the gun the way a gun looks - muzzle right, magazine down - and
write the display transform instead of borrowing one. A quarter turn about the vertical axis takes the
sprite's right and points it where the player is looking, leaving down still down.

Depth comes from the same block. Minecraft extrudes a flat item texture into a real slab, and the
display scale is applied in the item's own axes before it is turned - so stretching Z thickens the
barrel rather than lengthening it, and the gun stops looking like a sticker.
"""
import io
import json
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
ITEMS = os.path.join(PACK, "assets", "asuracraft", "items")
MODELS = os.path.join(PACK, "assets", "asuracraft", "models", "item")
TEXTURES = os.path.join(PACK, "assets", "asuracraft", "textures", "item")

EDGE = (16, 16, 20, 255)
STEEL_DARK = (42, 46, 54, 255)
STEEL = (74, 80, 90, 255)
STEEL_LIT = (126, 134, 148, 255)
WOOD_DARK = (68, 44, 24, 255)
WOOD = (112, 76, 44, 255)
WOOD_LIT = (150, 106, 62, 255)
GLASS = (150, 210, 240, 255)
BRASS = (200, 160, 72, 255)

# Rectangles on a sixteen pixel grid: (x, y, width, height, colour), y downward, muzzle to the right.
# Each barrel gets a lit row along the top and a dark row underneath, which is the whole trick to making
# sixteen pixels read as a round metal tube.
GUNS = {
    "pistol": [
        (6, 5, 9, 4, EDGE),
        (7, 6, 8, 2, STEEL),
        (7, 6, 8, 1, STEEL_LIT),
        (7, 8, 7, 1, STEEL_DARK),
        (6, 9, 4, 5, EDGE),
        (7, 9, 2, 4, WOOD),
        (7, 9, 1, 4, WOOD_LIT),
        (10, 9, 3, 2, STEEL_DARK),
        (14, 6, 1, 2, EDGE),
    ],
    "smg": [
        (2, 5, 13, 4, EDGE),
        (3, 6, 12, 2, STEEL),
        (3, 6, 12, 1, STEEL_LIT),
        (3, 8, 11, 1, STEEL_DARK),
        (5, 9, 3, 6, EDGE),
        (6, 9, 1, 5, STEEL_DARK),
        (2, 9, 3, 3, EDGE),
        (3, 9, 1, 2, WOOD),
        (8, 9, 3, 2, STEEL_DARK),
        (14, 6, 2, 2, EDGE),
        (13, 4, 1, 2, STEEL_DARK),
    ],
    "rifle": [
        (1, 5, 15, 4, EDGE),
        (2, 6, 13, 2, STEEL),
        (2, 6, 13, 1, STEEL_LIT),
        (2, 8, 12, 1, STEEL_DARK),
        (0, 5, 3, 5, EDGE),
        (1, 6, 2, 3, WOOD),
        (1, 6, 1, 3, WOOD_LIT),
        (6, 9, 3, 6, EDGE),
        (7, 9, 1, 5, STEEL_DARK),
        (9, 9, 3, 2, STEEL_DARK),
        (4, 9, 2, 2, WOOD_DARK),
        (11, 3, 2, 3, STEEL_DARK),
        (14, 6, 2, 2, EDGE),
        (9, 3, 1, 2, STEEL_DARK),
    ],
    "sniper": [
        (0, 6, 16, 3, EDGE),
        (1, 7, 14, 1, STEEL),
        (1, 7, 14, 1, STEEL_LIT),
        (1, 8, 13, 1, STEEL_DARK),
        (0, 6, 3, 5, EDGE),
        (1, 7, 2, 3, WOOD),
        (1, 7, 1, 3, WOOD_LIT),
        (4, 2, 9, 3, EDGE),
        (5, 3, 7, 1, STEEL_LIT),
        (5, 4, 7, 1, STEEL_DARK),
        (11, 3, 1, 2, GLASS),
        (5, 5, 1, 2, STEEL_DARK),
        (10, 5, 1, 2, STEEL_DARK),
        (5, 9, 2, 3, WOOD_DARK),
        (12, 9, 3, 1, STEEL_DARK),
        (13, 10, 1, 3, STEEL_DARK),
    ],
    "shotgun": [
        (0, 5, 16, 3, EDGE),
        (1, 6, 14, 1, STEEL),
        (1, 6, 14, 1, STEEL_LIT),
        (1, 7, 13, 1, STEEL_DARK),
        (0, 5, 3, 5, EDGE),
        (1, 6, 2, 3, WOOD),
        (1, 6, 1, 3, WOOD_LIT),
        (4, 8, 8, 3, EDGE),
        (5, 9, 6, 1, WOOD_LIT),
        (5, 10, 6, 1, WOOD_DARK),
        (12, 8, 3, 2, STEEL_DARK),
        (14, 5, 2, 3, EDGE),
        (7, 11, 1, 1, BRASS),
    ],
}

# How the hand holds it.
#
# A quarter turn about Y and nothing else: the sprite's right becomes the direction the player faces,
# and its down stays down, so a magazine drawn hanging below the receiver still hangs below it. The Z
# scale is the depth of the extruded slab, applied in the item's own axes before the turn - which is
# why it fattens the gun instead of stretching it.
DISPLAY = {
    "thirdperson_righthand": {
        "rotation": [0, -90, 0], "translation": [0, 4.0, 0.5], "scale": [1.0, 1.0, 1.7],
    },
    "thirdperson_lefthand": {
        "rotation": [0, 90, 0], "translation": [0, 4.0, 0.5], "scale": [1.0, 1.0, 1.7],
    },
    "firstperson_righthand": {
        "rotation": [0, -90, 0], "translation": [0.8, 3.2, 2.0], "scale": [1.15, 1.15, 1.9],
    },
    "firstperson_lefthand": {
        "rotation": [0, 90, 0], "translation": [0.8, 3.2, 2.0], "scale": [1.15, 1.15, 1.9],
    },
    "gui": {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1.0, 1.0, 1.0]},
    "ground": {"rotation": [0, 0, 0], "translation": [0, 2, 0], "scale": [0.6, 0.6, 0.6]},
    "fixed": {"rotation": [0, 180, 0], "translation": [0, 0, 0], "scale": [1.0, 1.0, 1.0]},
}


def draw(shapes):
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)
    for x, y, width, height, colour in shapes:
        pen.rectangle([x, y, x + width - 1, y + height - 1], fill=colour)
    return image


def main():
    for folder in (ITEMS, MODELS, TEXTURES):
        os.makedirs(folder, exist_ok=True)

    for name, shapes in GUNS.items():
        draw(shapes).save(os.path.join(TEXTURES, name + ".png"))

        model = {
            "parent": "minecraft:item/generated",
            "textures": {"layer0": "asuracraft:item/" + name},
            "display": DISPLAY,
        }
        with io.open(os.path.join(MODELS, name + ".json"), "w", encoding="utf-8") as out:
            json.dump(model, out, ensure_ascii=False, indent=2)

        definition = {"model": {"type": "minecraft:model", "model": "asuracraft:item/" + name}}
        with io.open(os.path.join(ITEMS, name + ".json"), "w", encoding="utf-8") as out:
            json.dump(definition, out, ensure_ascii=False, indent=2)

    print("guns   ", len(GUNS), "->", ", ".join(GUNS))


if __name__ == "__main__":
    main()
