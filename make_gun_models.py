# -*- coding: utf-8 -*-
"""Builds the guns as real three-dimensional models, the way Blockbench writes them.

A Blockbench model is not a special format - it is the same item JSON Minecraft has always read, with
an "elements" list of boxes instead of a flat sprite. So a gun can be built here, box by box, and it
will open in Blockbench afterwards for anyone who wants to push a barrel a pixel to the left.

Every face points at a patch of one small palette texture rather than at a drawing of a gun. That is
how most hand-built weapon models are textured: the shape carries the detail and the texture only
carries colour, which means a sixteen pixel palette dresses all five guns and adding a sixth costs
nothing. It also means no part of this is traced from anybody else's model - the boxes are ours.

Model space is sixteen units to a block, x running along the barrel with the muzzle at +x, y up, and z
across. The display transform then turns that to point where the player is looking.
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

# The palette, four by four swatches on a sixteen pixel square.
PALETTE = [
    (18, 18, 22),      # 0 black
    (44, 48, 56),      # 1 steel dark
    (78, 84, 96),      # 2 steel
    (126, 134, 150),   # 3 steel lit
    (70, 46, 26),      # 4 wood dark
    (116, 78, 46),     # 5 wood
    (156, 112, 66),    # 6 wood lit
    (34, 36, 40),      # 7 polymer
    (200, 160, 72),    # 8 brass
    (150, 212, 244),   # 9 glass
    (96, 40, 36),      # 10 red, for a dot sight
    (58, 62, 70),      # 11 steel mid
    (24, 26, 30),      # 12 rubber
    (140, 146, 158),   # 13 bright metal
    (30, 34, 40),      # 14 shadow
    (86, 92, 104),     # 15 grey
]
BLACK, STEEL_D, STEEL, STEEL_L, WOOD_D, WOOD, WOOD_L, POLY = 0, 1, 2, 3, 4, 5, 6, 7
BRASS, GLASS, RED, STEEL_M, RUBBER, BRIGHT, SHADOW, GREY = 8, 9, 10, 11, 12, 13, 14, 15


def swatch(index):
    """Where one colour sits in the palette texture, in the sixteen unit space a face UV uses."""
    column = index % 4
    row = index // 4
    return [column * 4 + 1, row * 4 + 1, column * 4 + 3, row * 4 + 3]


def box(x0, y0, z0, x1, y1, z1, colour, top=None, side=None):
    """One cuboid. A different colour may be given for the top and the sides to fake a light source."""
    faces = {}
    for face in ("north", "south", "east", "west", "up", "down"):
        if face == "up" and top is not None:
            which = top
        elif face in ("north", "south") and side is not None:
            which = side
        elif face == "down":
            which = SHADOW if colour in (STEEL, STEEL_M, STEEL_L) else colour
        else:
            which = colour
        faces[face] = {"uv": swatch(which), "texture": "#p"}
    return {"from": [x0, y0, z0], "to": [x1, y1, z1], "faces": faces}


# Each gun: a list of boxes. Built lying along x with the muzzle to the right, which is the same way the
# sprites were drawn - so the display transform that pointed those forward points these forward too.
GUNS = {
    "pistol": [
        box(5, 8, 6.5, 13, 11, 9.5, STEEL, top=STEEL_L),          # slide
        box(5.5, 8.5, 6.8, 12.5, 10.5, 9.2, STEEL_M),             # slide inset
        box(12, 9, 7, 14, 10.5, 9, BLACK),                        # muzzle
        box(5, 5, 7, 8, 8, 9, POLY),                              # frame
        box(4.5, 1, 7, 7.5, 5.5, 9, POLY, top=STEEL_D),           # grip
        box(4.4, 1.5, 6.9, 4.9, 5, 9.1, RUBBER),                  # grip panel
        box(8, 5.5, 7.2, 10, 7, 8.8, STEEL_D),                    # trigger guard top
        box(8, 4.5, 7.4, 8.8, 6, 8.6, STEEL_D),                   # trigger
        box(11.5, 11, 7.5, 12.3, 12, 8.5, BLACK),                 # front sight
        box(5.6, 11, 7.5, 6.4, 12, 8.5, BLACK),                   # rear sight
    ],
    "smg": [
        box(2, 8, 6.5, 13, 11, 9.5, STEEL, top=STEEL_L),          # receiver
        box(2.4, 8.4, 6.8, 12.6, 10.6, 9.2, STEEL_M),
        box(13, 9, 7.2, 15.5, 10.5, 8.8, BLACK),                  # barrel
        box(0.5, 8.6, 7.2, 2, 10.4, 8.8, STEEL_D),                # folding stock
        box(6, 2.5, 7.2, 8, 8, 8.8, STEEL_D, top=STEEL),          # magazine
        box(6.2, 3, 7.1, 7.8, 7.5, 8.9, STEEL_M),
        box(3.5, 3, 7.1, 5.5, 8, 8.9, POLY),                      # grip
        box(8, 6.5, 7.3, 10, 8, 8.7, STEEL_D),                    # trigger guard
        box(8.2, 5.6, 7.4, 9, 7, 8.6, STEEL_D),                   # trigger
        box(4, 11, 7.3, 11, 11.8, 8.7, STEEL_D),                  # top rail
        box(12.4, 11.2, 7.6, 13, 12.6, 8.4, BLACK),               # front sight
        box(3.2, 11.2, 7.6, 3.8, 12.4, 8.4, BLACK),               # rear sight
    ],
    "rifle": [
        box(2, 8, 6.5, 13.5, 11, 9.5, STEEL, top=STEEL_L),        # receiver
        box(2.4, 8.4, 6.8, 13.1, 10.6, 9.2, STEEL_M),
        box(13.5, 9, 7.2, 16, 10.4, 8.8, BLACK),                  # barrel
        box(15.4, 8.8, 7, 16, 10.6, 9, STEEL_D),                  # flash hider
        box(0, 7.5, 6.8, 2, 11, 9.2, WOOD, top=WOOD_L),           # stock
        box(0, 7.5, 6.8, 0.6, 11, 9.2, WOOD_D),
        box(6, 3, 7.1, 8.2, 8, 8.9, STEEL_D, top=STEEL),          # magazine
        box(6.4, 2, 7.2, 8.6, 4, 8.8, STEEL_D),                   # magazine curve
        box(3.4, 3, 7.1, 5.4, 8, 8.9, POLY),                      # grip
        box(8.4, 6.5, 7.3, 10.4, 8, 8.7, STEEL_D),                # trigger guard
        box(8.6, 5.6, 7.4, 9.4, 7, 8.6, STEEL_D),                 # trigger
        box(10.5, 7.6, 6.9, 13.4, 9.4, 9.1, WOOD, top=WOOD_L),    # handguard
        box(4, 11, 7.3, 10, 11.7, 8.7, STEEL_D),                  # top rail
        box(12.6, 11, 7.6, 13.2, 12.8, 8.4, BLACK),               # front post
        box(4.4, 11, 7.6, 5, 12.4, 8.4, BLACK),                   # rear sight
    ],
    "sniper": [
        box(1, 8, 6.8, 13, 10.6, 9.2, STEEL, top=STEEL_L),        # receiver
        box(13, 8.6, 7.3, 16, 10, 8.7, BLACK),                    # long barrel
        box(0, 7, 6.6, 2.4, 11.4, 9.4, WOOD, top=WOOD_L),         # heavy stock
        box(0, 7, 6.6, 0.7, 11.4, 9.4, WOOD_D),
        box(1.6, 11.2, 6.9, 4.2, 12.2, 9.1, WOOD_L),              # cheek rest
        box(4, 12.4, 7.0, 12, 14.4, 9.0, STEEL_D, top=STEEL),     # scope tube
        box(4, 12.8, 7.2, 4.6, 14, 8.8, GLASS),                   # eyepiece
        box(11.4, 12.6, 7.1, 12, 14.2, 8.9, GLASS),               # objective
        box(5, 11, 7.5, 5.8, 12.4, 8.5, STEEL_D),                 # mounts
        box(10, 11, 7.5, 10.8, 12.4, 8.5, STEEL_D),
        box(3.2, 3, 7.1, 5.2, 8, 8.9, POLY),                      # grip
        box(8, 6.5, 7.3, 10, 8, 8.7, STEEL_D),                    # trigger guard
        box(8.2, 5.6, 7.4, 9, 7, 8.6, STEEL_D),                   # trigger
        box(7.6, 10.4, 8.9, 9.2, 11.2, 9.6, BRIGHT),              # bolt handle
        box(12.5, 5.5, 7.6, 13.3, 8, 8.4, STEEL_D),               # bipod leg
        box(12.5, 4.6, 6.4, 13.3, 5.6, 9.6, STEEL_D),             # bipod feet
    ],
    "shotgun": [
        box(1.5, 8.2, 6.8, 14, 10.8, 9.2, STEEL, top=STEEL_L),    # barrel
        box(14, 8.4, 6.9, 16, 10.6, 9.1, BLACK),                  # bore
        box(0, 7.4, 6.7, 2.4, 11, 9.3, WOOD, top=WOOD_L),         # stock
        box(0, 7.4, 6.7, 0.7, 11, 9.3, WOOD_D),
        box(4.5, 6.2, 6.7, 11.5, 8.4, 9.3, WOOD, top=WOOD_L),     # pump
        box(5.5, 6.1, 6.6, 6, 8.5, 9.4, WOOD_D),                  # pump grooves
        box(7.5, 6.1, 6.6, 8, 8.5, 9.4, WOOD_D),
        box(9.5, 6.1, 6.6, 10, 8.5, 9.4, WOOD_D),
        box(2, 5.6, 7, 4.6, 8.4, 9, WOOD, top=WOOD_L),            # wrist
        box(4, 6.6, 7.3, 5, 8.2, 8.7, STEEL_D),                   # trigger guard
        box(4.2, 5.8, 7.4, 4.9, 7, 8.6, STEEL_D),                 # trigger
        box(4.8, 8.4, 7.4, 5.6, 9, 8.6, BRASS),                   # a shell at the port
        box(12.8, 11, 7.6, 13.3, 11.8, 8.4, BRASS),               # bead sight
    ],
}


def display(tilt=0.0, drop=0.0):
    """A quarter turn takes the muzzle - which is +x - and points it where the player is looking."""
    return {
        "thirdperson_righthand": {
            "rotation": [tilt, -90, 0], "translation": [0, 3.5 - drop, 0], "scale": [0.85, 0.85, 0.85],
        },
        "thirdperson_lefthand": {
            "rotation": [tilt, 90, 0], "translation": [0, 3.5 - drop, 0], "scale": [0.85, 0.85, 0.85],
        },
        "firstperson_righthand": {
            "rotation": [tilt, -90, 0], "translation": [1.2, 2.6 - drop, 1.2], "scale": [0.9, 0.9, 0.9],
        },
        "firstperson_lefthand": {
            "rotation": [tilt, 90, 0], "translation": [1.2, 2.6 - drop, 1.2], "scale": [0.9, 0.9, 0.9],
        },
        "gui": {"rotation": [30, 135, 0], "translation": [0, 0, 0], "scale": [0.9, 0.9, 0.9]},
        "ground": {"rotation": [0, 0, 0], "translation": [0, 2, 0], "scale": [0.5, 0.5, 0.5]},
        "fixed": {"rotation": [0, 90, 0], "translation": [0, 0, 0], "scale": [1.0, 1.0, 1.0]},
    }


# The reload tips the muzzle down and brings it back. Same boxes, different hand.
FRAMES = {"": display(), "_r1": display(30, 1.5), "_r2": display(58, 3.0)}


def palette_texture():
    image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)
    for index, colour in enumerate(PALETTE):
        column = index % 4
        row = index // 4
        pen.rectangle([column * 4, row * 4, column * 4 + 3, row * 4 + 3], fill=colour + (255,))
    return image


def main():
    for folder in (ITEMS, MODELS, TEXTURES):
        os.makedirs(folder, exist_ok=True)
    palette_texture().save(os.path.join(TEXTURES, "gun_palette.png"))

    for name, boxes in GUNS.items():
        for suffix, block in FRAMES.items():
            model = {
                "textures": {"p": "asuracraft:item/gun_palette", "particle": "asuracraft:item/gun_palette"},
                "elements": boxes,
                "display": block,
                "gui_light": "front",
            }
            with io.open(os.path.join(MODELS, name + suffix + ".json"), "w",
                         encoding="utf-8") as out:
                json.dump(model, out, ensure_ascii=False, indent=1)
            definition = {"model": {"type": "minecraft:model",
                                    "model": "asuracraft:item/" + name + suffix}}
            with io.open(os.path.join(ITEMS, name + suffix + ".json"), "w",
                         encoding="utf-8") as out:
                json.dump(definition, out, ensure_ascii=False, indent=1)
        print("  %-8s %2d boxes" % (name, len(boxes)))

    print("guns   ", len(GUNS), "models x", len(FRAMES), "frames")


if __name__ == "__main__":
    main()
