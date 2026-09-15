# -*- coding: utf-8 -*-
"""Draws the guns the way Minecraft expects a held item to be drawn.

The first attempt drew them flat, muzzle to the right, and they came out pointing across the player's
chest. That is not a bug in the display settings - it is what the game does with every held item. A
vanilla sword, pickaxe and axe are all drawn along the DIAGONAL, tip at the top right, because the hand
holds a sprite rotated forty-five degrees. Draw a gun flat and the game faithfully holds it sideways.

So everything here is built from diagonal strokes running bottom-left to top-right: the stock sits in
the corner by the wrist and the muzzle points where the player is looking, which is what "pointing
forward" actually means for a held sprite.
"""
import io
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
ITEMS = os.path.join(PACK, "assets", "asuracraft", "items")
MODELS = os.path.join(PACK, "assets", "asuracraft", "models", "item")
TEXTURES = os.path.join(PACK, "assets", "asuracraft", "textures", "item")

# Five tones. Three was enough to tell the guns apart and not enough to make any of them look made of
# anything: a barrel needs a lit top and a shaded underside or it reads as a grey stick.
EDGE = (18, 18, 22, 255)
STEEL_DARK = (44, 48, 56, 255)
STEEL = (72, 78, 88, 255)
STEEL_LIT = (122, 130, 142, 255)
WOOD = (110, 74, 42, 255)
WOOD_LIT = (146, 102, 60, 255)
WOOD_DARK = (70, 46, 26, 255)
GLASS = (150, 210, 240, 255)
BRASS = (198, 158, 70, 255)


def stroke(pen, x0, y0, x1, y1, colour, width=1):
    """A band of pixels from one point to another, thickened across the diagonal.

    Walking the longer axis one pixel at a time keeps the line solid - a naive step of one on both axes
    leaves corner gaps that read as a dotted line at this size.
    """
    steps = max(abs(x1 - x0), abs(y1 - y0))
    if steps == 0:
        steps = 1
    for step in range(steps + 1):
        x = round(x0 + (x1 - x0) * step / steps)
        y = round(y0 + (y1 - y0) * step / steps)
        for across in range(width):
            # Clamped rather than trusted: a stroke drawn to the very corner of a sixteen pixel square
            # with any thickness at all runs off the edge, and one stray pixel takes the whole file down.
            at_x = min(15, max(0, x))
            at_y = min(15, max(0, y + across))
            pen[at_x, at_y] = colour


def gun(strokes):
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    pen = image.load()
    for args in strokes:
        stroke(pen, *args)
    return image


# Coordinates run with y downward. Bottom-left is the wrist, top-right is the muzzle - the same axis a
# sword's blade runs along, which is the only orientation the game holds correctly.
GUNS = {
    # Short, blunt, no stock. Reads as a sidearm by being half the length of everything else.
    "pistol": [
        (5, 10, 11, 4, EDGE, 4),
        (5, 10, 11, 4, STEEL, 3),
        (5, 10, 11, 4, STEEL_LIT, 1),
        (4, 13, 6, 10, WOOD_DARK, 3),
        (4, 13, 6, 10, WOOD, 2),
        (11, 4, 12, 3, EDGE, 2),
    ],
    # A long thin receiver with a magazine hanging straight down: the outline everyone reads as an SMG.
    "smg": [
        (3, 12, 12, 3, EDGE, 4),
        (3, 12, 12, 3, STEEL_DARK, 3),
        (3, 12, 12, 3, STEEL, 2),
        (3, 12, 12, 3, STEEL_LIT, 1),
        (6, 13, 5, 15, STEEL_DARK, 2),
        (4, 12, 3, 13, EDGE, 2),
        (12, 3, 14, 1, EDGE, 2),
        (12, 3, 13, 2, STEEL_LIT, 1),
    ],
    # Full length, curved magazine, wooden furniture, a sight standing up off the receiver.
    "rifle": [
        (1, 14, 14, 1, EDGE, 4),
        (1, 14, 14, 1, STEEL_DARK, 3),
        (2, 13, 14, 1, STEEL, 2),
        (2, 13, 13, 2, STEEL_LIT, 1),
        (1, 14, 4, 11, WOOD_DARK, 4),
        (2, 14, 4, 12, WOOD, 3),
        (2, 14, 3, 13, WOOD_LIT, 1),
        (6, 12, 5, 15, STEEL_DARK, 2),
        (7, 11, 6, 14, STEEL_DARK, 2),
        (9, 7, 10, 6, EDGE, 2),
        (14, 1, 15, 0, EDGE, 2),
        (8, 9, 9, 8, WOOD, 2),
    ],
    # The longest outline, a scope sitting above the barrel, and a bipod under the muzzle.
    "sniper": [
        (0, 15, 15, 0, EDGE, 4),
        (0, 15, 15, 0, STEEL_DARK, 3),
        (1, 15, 15, 1, STEEL, 2),
        (1, 14, 14, 1, STEEL_LIT, 1),
        (0, 15, 3, 12, WOOD_DARK, 4),
        (1, 15, 3, 13, WOOD, 3),
        (6, 9, 11, 4, EDGE, 3),
        (6, 9, 11, 4, STEEL_DARK, 2),
        (7, 9, 10, 5, GLASS, 1),
        (6, 11, 7, 10, STEEL_DARK, 2),
        (10, 7, 11, 6, STEEL_DARK, 2),
        (13, 4, 13, 7, STEEL_DARK, 1),
        (15, 0, 15, 2, EDGE, 1),
    ],
    # A fat bore and a wooden pump running most of the length underneath it.
    "shotgun": [
        (1, 14, 14, 1, EDGE, 4),
        (1, 14, 14, 1, STEEL_DARK, 3),
        (2, 14, 14, 2, STEEL, 2),
        (2, 13, 13, 2, STEEL_LIT, 1),
        (0, 15, 3, 12, WOOD_DARK, 4),
        (1, 15, 3, 13, WOOD, 3),
        (4, 14, 10, 8, WOOD_DARK, 3),
        (4, 14, 10, 8, WOOD, 2),
        (5, 14, 10, 9, WOOD_LIT, 1),
        (13, 2, 15, 0, EDGE, 3),
        (13, 2, 15, 0, STEEL_DARK, 2),
        (7, 12, 8, 11, BRASS, 1),
    ],
}


def main():
    for folder in (ITEMS, MODELS, TEXTURES):
        os.makedirs(folder, exist_ok=True)

    for name, strokes in GUNS.items():
        gun(strokes).save(os.path.join(TEXTURES, name + ".png"))

        # handheld, with no display overrides of our own. Its defaults are what a sword uses, and the
        # art is now drawn on the axis those defaults expect - so the gun points where the player looks
        # without a single number being tuned by hand.
        model = {
            "parent": "minecraft:item/handheld",
            "textures": {"layer0": "asuracraft:item/" + name},
        }
        with io.open(os.path.join(MODELS, name + ".json"), "w", encoding="utf-8") as out:
            json.dump(model, out, ensure_ascii=False, indent=2)

        definition = {"model": {"type": "minecraft:model", "model": "asuracraft:item/" + name}}
        with io.open(os.path.join(ITEMS, name + ".json"), "w", encoding="utf-8") as out:
            json.dump(definition, out, ensure_ascii=False, indent=2)

    print("guns   ", len(GUNS), "->", ", ".join(GUNS))


if __name__ == "__main__":
    main()
