# -*- coding: utf-8 -*-
"""Draws the guns at thirty-two pixels, and the frames a reload plays through.

Sixteen pixels is the size of a vanilla item, and it is the size at which a gun becomes a grey wedge:
there is no room for a trigger guard, a charging handle, a sling loop or a rail, and those details are
the whole of what separates a rifle from a plank. An item texture may be any power of two, so these are
thirty-two - four times the room, at no cost to anything but the download.

The reload is an animation made out of nothing but display transforms. Three models share one texture
and differ only in how the hand is told to hold it: level, tipped down while the magazine is out, then
level again. Swapping which model the item asks for, a few ticks apart, is a reload animation that
needed no new art and no entity.
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

EDGE = (14, 14, 18, 255)
STEEL_DARK = (40, 44, 52, 255)
STEEL = (72, 78, 90, 255)
STEEL_LIT = (124, 132, 148, 255)
STEEL_HI = (176, 184, 198, 255)
WOOD_DARK = (64, 42, 22, 255)
WOOD = (110, 74, 42, 255)
WOOD_LIT = (152, 108, 64, 255)
GLASS = (150, 212, 244, 255)
GLASS_DARK = (78, 140, 178, 255)
BRASS = (204, 164, 74, 255)
POLY = (34, 36, 40, 255)      # polymer furniture, darker and flatter than steel

# Thirty-two across, muzzle to the right, magazine hanging down. Rectangles are (x, y, w, h, colour).
GUNS = {
    "pistol": [
        (12, 10, 18, 7, EDGE),            # slide
        (13, 11, 16, 2, STEEL_LIT),
        (13, 13, 16, 2, STEEL),
        (13, 15, 16, 1, STEEL_DARK),
        (15, 11, 9, 1, STEEL_HI),         # light along the top of the slide
        (26, 12, 1, 3, EDGE),             # ejection port
        (12, 17, 8, 12, EDGE),            # grip
        (13, 18, 5, 10, POLY),
        (13, 18, 2, 10, STEEL_DARK),      # grip panel edge
        (14, 20, 1, 6, STEEL_LIT),        # checkering highlight
        (20, 17, 7, 5, EDGE),             # trigger guard
        (21, 18, 5, 3, (0, 0, 0, 0)),     # hollow it out
        (21, 17, 2, 3, STEEL_DARK),       # trigger
        (29, 12, 2, 3, EDGE),             # muzzle
        (30, 13, 1, 1, STEEL_DARK),       # bore
        (24, 9, 2, 1, STEEL_DARK),        # rear sight
    ],
    "smg": [
        (4, 10, 26, 7, EDGE),             # receiver
        (5, 11, 24, 2, STEEL_LIT),
        (5, 13, 24, 2, STEEL),
        (5, 15, 24, 1, STEEL_DARK),
        (8, 11, 12, 1, STEEL_HI),
        (2, 11, 3, 5, EDGE),              # folding stock
        (3, 12, 1, 3, STEEL_DARK),
        (11, 17, 6, 13, EDGE),            # magazine
        (12, 18, 4, 11, STEEL_DARK),
        (12, 18, 1, 11, STEEL_LIT),
        (13, 21, 2, 1, STEEL),            # witness holes
        (13, 24, 2, 1, STEEL),
        (6, 17, 5, 9, EDGE),              # pistol grip
        (7, 18, 3, 7, POLY),
        (7, 18, 1, 7, STEEL_DARK),
        (17, 17, 6, 4, EDGE),             # trigger guard
        (18, 18, 4, 2, (0, 0, 0, 0)),
        (18, 17, 2, 2, STEEL_DARK),
        (24, 8, 2, 3, EDGE),              # front sight
        (25, 9, 1, 2, STEEL_LIT),
        (29, 12, 3, 3, EDGE),             # muzzle
        (30, 13, 2, 1, STEEL_DARK),
        (10, 8, 8, 2, EDGE),              # top rail
        (11, 9, 6, 1, STEEL_DARK),
    ],
    "rifle": [
        (2, 11, 29, 6, EDGE),             # receiver and barrel
        (3, 12, 27, 2, STEEL_LIT),
        (3, 14, 27, 2, STEEL),
        (3, 16, 26, 1, STEEL_DARK),
        (7, 12, 13, 1, STEEL_HI),
        (0, 10, 4, 9, EDGE),              # shoulder stock
        (1, 11, 2, 7, WOOD),
        (1, 11, 1, 7, WOOD_LIT),
        (2, 15, 1, 3, WOOD_DARK),
        (12, 17, 7, 12, EDGE),            # curved magazine
        (13, 18, 5, 4, STEEL_DARK),
        (14, 22, 5, 4, STEEL_DARK),
        (15, 26, 4, 3, STEEL_DARK),
        (13, 18, 1, 4, STEEL_LIT),
        (7, 17, 5, 10, EDGE),             # grip
        (8, 18, 3, 8, POLY),
        (8, 18, 1, 8, STEEL_DARK),
        (19, 17, 6, 4, EDGE),             # trigger guard
        (20, 18, 4, 2, (0, 0, 0, 0)),
        (20, 17, 2, 2, STEEL_DARK),
        (21, 17, 8, 3, EDGE),             # handguard under the barrel
        (22, 18, 6, 1, WOOD),
        (22, 19, 6, 1, WOOD_DARK),
        (8, 8, 12, 3, EDGE),              # top rail
        (9, 9, 10, 1, STEEL_DARK),
        (9, 10, 10, 1, STEEL),
        (25, 8, 2, 4, EDGE),              # front sight post
        (26, 9, 1, 3, STEEL_LIT),
        (30, 12, 2, 4, EDGE),             # flash hider
        (31, 13, 1, 2, STEEL_DARK),
    ],
    "sniper": [
        (0, 13, 32, 5, EDGE),             # long barrel
        (1, 14, 30, 2, STEEL_LIT),
        (1, 16, 30, 1, STEEL),
        (1, 17, 29, 1, STEEL_DARK),
        (0, 11, 6, 10, EDGE),             # heavy stock with a cheek rest
        (1, 12, 4, 8, WOOD),
        (1, 12, 1, 8, WOOD_LIT),
        (4, 16, 2, 4, WOOD_DARK),
        (2, 10, 4, 2, EDGE),              # cheek piece
        (3, 11, 2, 1, WOOD_LIT),
        (8, 4, 18, 6, EDGE),              # scope tube
        (9, 5, 16, 2, STEEL_LIT),
        (9, 7, 16, 2, STEEL_DARK),
        (12, 5, 7, 1, STEEL_HI),
        (24, 5, 2, 4, GLASS),             # objective lens
        (24, 5, 1, 2, GLASS_DARK),
        (9, 5, 2, 4, GLASS_DARK),         # eyepiece
        (11, 10, 3, 4, EDGE),             # scope mounts
        (12, 11, 1, 3, STEEL_DARK),
        (20, 10, 3, 4, EDGE),
        (21, 11, 1, 3, STEEL_DARK),
        (10, 18, 5, 10, EDGE),            # grip
        (11, 19, 3, 8, POLY),
        (11, 19, 1, 8, STEEL_DARK),
        (16, 18, 6, 4, EDGE),             # trigger guard
        (17, 19, 4, 2, (0, 0, 0, 0)),
        (17, 18, 2, 2, STEEL_DARK),
        (15, 17, 4, 2, EDGE),             # bolt handle
        (16, 15, 2, 3, STEEL_LIT),
        (24, 18, 2, 8, EDGE),             # bipod
        (22, 24, 6, 2, EDGE),
        (25, 19, 1, 6, STEEL_DARK),
        (29, 13, 3, 5, EDGE),             # muzzle brake
        (30, 15, 2, 1, STEEL_DARK),
    ],
    "shotgun": [
        (1, 11, 31, 5, EDGE),             # barrel
        (2, 12, 29, 2, STEEL_LIT),
        (2, 14, 29, 1, STEEL),
        (2, 15, 28, 1, STEEL_DARK),
        (0, 10, 5, 9, EDGE),              # stock
        (1, 11, 3, 7, WOOD),
        (1, 11, 1, 7, WOOD_LIT),
        (3, 15, 1, 3, WOOD_DARK),
        (9, 17, 16, 5, EDGE),             # pump, running most of the length
        (10, 18, 14, 1, WOOD_LIT),
        (10, 19, 14, 2, WOOD),
        (10, 21, 14, 1, WOOD_DARK),
        (12, 18, 1, 4, WOOD_DARK),        # grooves
        (15, 18, 1, 4, WOOD_DARK),
        (18, 18, 1, 4, WOOD_DARK),
        (21, 18, 1, 4, WOOD_DARK),
        (5, 16, 5, 8, EDGE),              # wrist
        (6, 17, 3, 6, WOOD),
        (6, 17, 1, 6, WOOD_LIT),
        (10, 16, 6, 3, EDGE),             # loading port and trigger guard
        (11, 17, 4, 1, (0, 0, 0, 0)),
        (11, 16, 2, 1, STEEL_DARK),
        (13, 15, 2, 1, BRASS),            # a shell showing at the port
        (29, 11, 3, 5, EDGE),             # wide bore
        (30, 12, 2, 3, STEEL_DARK),
        (26, 9, 2, 2, EDGE),              # bead sight
        (26, 9, 1, 1, BRASS),
    ],
}

# How the hand holds it, and the two frames a reload tips through.
#
# A quarter turn about the vertical axis takes the sprite's right - the muzzle - and points it where the
# player is looking, leaving down still down so a magazine hangs where it was drawn. The Z scale is the
# depth of the extruded slab and is applied in the item's own axes before the turn, which is why it
# thickens the gun rather than lengthening it.
def display(tilt=0.0, drop=0.0):
    return {
        "thirdperson_righthand": {
            "rotation": [tilt, -90, 0], "translation": [0, 4.0 - drop, 0.5],
            "scale": [1.0, 1.0, 1.7],
        },
        "thirdperson_lefthand": {
            "rotation": [tilt, 90, 0], "translation": [0, 4.0 - drop, 0.5],
            "scale": [1.0, 1.0, 1.7],
        },
        "firstperson_righthand": {
            "rotation": [tilt, -90, 0], "translation": [0.8, 3.2 - drop, 2.0],
            "scale": [1.15, 1.15, 1.9],
        },
        "firstperson_lefthand": {
            "rotation": [tilt, 90, 0], "translation": [0.8, 3.2 - drop, 2.0],
            "scale": [1.15, 1.15, 1.9],
        },
        "gui": {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1.0, 1.0, 1.0]},
        "ground": {"rotation": [0, 0, 0], "translation": [0, 2, 0], "scale": [0.6, 0.6, 0.6]},
        "fixed": {"rotation": [0, 180, 0], "translation": [0, 0, 0], "scale": [1.0, 1.0, 1.0]},
    }


# The reload, in three beats: drop the muzzle, drop it further while the magazine is changed, come back.
FRAMES = {"": display(), "_r1": display(28, 1.5), "_r2": display(55, 3.0)}


def draw(shapes, size):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)
    for x, y, width, height, colour in shapes:
        if colour[3] == 0:
            # A hollow: punched straight into the pixels, since drawing transparent over opaque does
            # nothing at all - a trigger guard has to have a hole in it or it is a block.
            for at_x in range(x, x + width):
                for at_y in range(y, y + height):
                    if 0 <= at_x < size and 0 <= at_y < size:
                        image.putpixel((at_x, at_y), (0, 0, 0, 0))
            continue
        pen.rectangle([x, y, x + width - 1, y + height - 1], fill=colour)
    return image


def main():
    for folder in (ITEMS, MODELS, TEXTURES):
        os.makedirs(folder, exist_ok=True)

    for name, shapes in GUNS.items():
        draw(shapes, 32).save(os.path.join(TEXTURES, name + ".png"))
        for suffix, block in FRAMES.items():
            model = {
                "parent": "minecraft:item/generated",
                "textures": {"layer0": "asuracraft:item/" + name},
                "display": block,
            }
            with io.open(os.path.join(MODELS, name + suffix + ".json"), "w",
                         encoding="utf-8") as out:
                json.dump(model, out, ensure_ascii=False, indent=2)
            definition = {"model": {"type": "minecraft:model",
                                    "model": "asuracraft:item/" + name + suffix}}
            with io.open(os.path.join(ITEMS, name + suffix + ".json"), "w",
                         encoding="utf-8") as out:
                json.dump(definition, out, ensure_ascii=False, indent=2)

    print("guns   ", len(GUNS), "x", len(FRAMES), "frames ->", ", ".join(GUNS))


if __name__ == "__main__":
    main()
