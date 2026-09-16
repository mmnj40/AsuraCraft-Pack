# -*- coding: utf-8 -*-
"""Builds the guns, drawn as pixel art and extruded into the item JSON Minecraft reads.

The first two attempts at these placed a dozen large boxes by hand and then argued about the texture.
Both looked like boxes, because they were. The models people admire - the ones that read as a real
firearm at a glance - are not a dozen boxes; they are a couple of hundred one-pixel steps that add up
to a curve, a taper and a trigger guard you could put a finger through. Nobody places those by hand
either. They are drawn, in two dimensions, and the third is an extrusion.

So that is what this is. Each gun is a side view drawn in ASCII at one character per model unit -
a pistol is twenty-six units long, a rifle forty-six - where every character names a material. That
grid is then:

  1. merged      into the largest rectangles of one material that will fit, so a hundred and eighty
                 pixels become forty-odd boxes rather than a hundred and eighty
  2. extruded    to each material's own thickness: a slide is wide, a barrel is narrow, a sight is a
                 blade, a grip panel is a skin on the outside of the grip
  3. painted     face by face into the gun's own texture - serrations across a slide, chequering on a
                 grip, grain along wood, a lit top edge and a dark underside on everything

The drawing is the part a person can judge. Run this file with --profile and it writes the side views
out as a picture; if the silhouette is wrong there, no amount of texturing will save it, and if it is
right there the model is right.

Model space is sixteen units to a block, x running along the barrel with the muzzle at +x, y up, z
across. Minecraft allows element coordinates from -16 to 32, which is where the forty-eight unit
ceiling on gun length comes from.
"""
import io
import json
import math
import os
import random
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
ITEMS = os.path.join(PACK, "assets", "asuracraft", "items")
MODELS = os.path.join(PACK, "assets", "asuracraft", "models", "item")
TEXTURES = os.path.join(PACK, "assets", "asuracraft", "textures", "item")

SIZE = 512          # the texture each gun gets to itself
LIMIT = 32.0        # the furthest a model element may reach
FLOOR = -16.0

# ---------------------------------------------------------------- materials
#
# colour, finish, and how thick the part is across the gun. Thickness is what turns a flat drawing into
# an object: the slide is the widest thing on a pistol, the barrel is narrower, a sight is a blade and
# a grip panel is a two-tenths skin stuck on the outside of the grip.
MATERIALS = {
    #          colour               finish      z0     z1
    "s": ((78, 84, 96),    "brushed", 5.0, 11.0),   # slide / receiver
    "z": ((74, 80, 92),    "serrate", 5.0, 11.0),   # the cut serrations at the back of a slide
    "t": ((116, 124, 140), "brushed", 5.2, 10.8),   # slide top rib
    "f": ((58, 63, 72),    "brushed", 5.3, 10.7),   # frame
    "b": ((28, 29, 34),    "grit",    6.4, 9.6),    # barrel, muzzle
    "n": ((40, 43, 50),    "brushed", 6.0, 10.0),   # heavy barrel / shroud
    "p": ((40, 42, 48),    "checker", 5.2, 10.8),   # grip
    "k": ((52, 57, 66),    "brushed", 7.0, 9.0),    # trigger guard
    "x": ((26, 27, 32),    "grit",    7.1, 8.9),    # trigger
    "i": ((24, 25, 30),    "grit",    7.2, 8.8),    # iron sight
    "r": ((150, 52, 44),   "flat",    4.9, 11.1),   # a painted marking
    "l": ((150, 157, 170), "brushed", 4.7, 11.3),   # lever, catch, bolt release
    "m": ((26, 27, 32),    "grit",    6.2, 9.8),    # magazine floor plate
    "d": ((54, 59, 68),    "brushed", 6.2, 9.8),    # magazine body
    "R": ((24, 25, 30),    "checker", 6.2, 9.8),    # rail
    "H": ((34, 36, 42),    "brushed", 5.8, 10.2),   # handguard
    "V": ((20, 21, 26),    "grit",    5.6, 10.4),   # vent slot cut into a handguard
    "A": ((46, 49, 56),    "brushed", 5.4, 10.6),   # stock
    "P": ((24, 25, 30),    "checker", 5.2, 10.8),   # butt pad
    "W": ((124, 84, 48),   "grain",   5.2, 10.8),   # wood
    "w": ((86, 57, 32),    "grain",   5.0, 11.0),   # dark wood
    "S": ((48, 52, 60),    "brushed", 5.6, 10.4),   # scope tube
    "N": ((40, 44, 52),    "brushed", 6.6, 9.4),    # scope mount
    "L": ((148, 210, 242), "glass",   6.2, 9.8),    # lens
    "B": ((140, 147, 160), "brushed", 6.8, 11.8),   # bolt handle, proud on one side
    "e": ((196, 158, 74),  "brushed", 6.6, 9.4),    # brass
    "o": ((36, 39, 46),    "brushed", 6.6, 9.4),    # cylinder
}

# How much light each face is given. The gun is lit from above and a little from the muzzle end, which
# is what stops a box from reading as a single grey lump.
LIGHT = {"up": 1.22, "down": 0.50, "north": 1.03, "south": 0.88, "east": 1.12, "west": 0.72}


def shade(colour, factor):
    return tuple(max(0, min(255, int(round(channel * factor)))) for channel in colour)


# ---------------------------------------------------------------- the drawings
#
# One character per model unit, muzzle to the right, top row first. Everything up to and including the
# leading pipe is stripped, so the art can be indented to sit neatly in the file.
GUNS = {}


def gun(name, art):
    rows = [line for line in art.strip("\n").split("\n")]
    rows = [row[row.index("|") + 1:] if "|" in row else row for row in rows]
    width = max(len(row) for row in rows)
    GUNS[name] = [row.ljust(width, ".") for row in rows]


gun("pistol", """
    |..........................
    |..........................
    |....i................i....
    |..tttttttttttttttttttt....
    |..zzzzzzzsssssssssssss....
    |..zzzzzzzssssssssssssbbbb.
    |..zzzzzzzrssssslsssssbbbb.
    |..zzzzzzzsssssssssssss....
    |...ffffffffffffffffff.....
    |...ffffffffffffffffff.....
    |...fffffffffffffRRRRR.....
    |..ppppppp..kx..k..........
    |..ppppppp..kx..k..........
    |.ppppppp...kkkkk..........
    |.ppppppp..................
    |ppppppp...................
    |ppppppp...................
    |mmmmmmm...................
""")

gun("magnum", """
    |..........................
    |......i...............i...
    |......tttttttttttttttt....
    |......ssssssssssssssssbbbb
    |.....sssssssssssssssssbbbb
    |.....ssooooosssssssssss...
    |.....ffooooofffff.........
    |.....ffooooofff...........
    |....ppffffffff............
    |....ppppp.kx.k............
    |....ppppp.kx.k............
    |...ppppp..kkkk............
    |...ppppp..................
    |..ppppp...................
    |..ppppp...................
    |..ppppp...................
    |...mmm....................
""")

gun("deagle", """
    |..............................
    |..............................
    |.....i....................i...
    |...tttttttttttttttttttttttt...
    |...zzzzzzzzsssssssssssssssss..
    |...zzzzzzzzssssssssssssssssbbb
    |...zzzzzzzzrsssssslssssssssbbb
    |...zzzzzzzzsssssssssssssssss..
    |...ffffffffffffffffffffffff...
    |...ffffffffffffffffffRRRRRR...
    |..pppppppp..kx..k.............
    |..pppppppp..kx..k.............
    |..pppppppp..kkkkk.............
    |.pppppppp.....................
    |.pppppppp.....................
    |pppppppp......................
    |pppppppp......................
    |mmmmmmmm......................
""")

gun("smg", """
    |..................................
    |..........i.............i.........
    |..........i.............ii........
    |........RRRRRRRRRRRR....ii........
    |PPssssssssssssssssssss..HHHH......
    |PPssssssssssssssssssss.HHHHHH.....
    |PPsssssssssssssssssssssHVHVHHnnnnn
    |PPsssssssssssssssssssssHVHVHHnnnnn
    |PPssssssssssssssssssssslHHHHHnnnnn
    |PPffffffffffffffffffff..HHHH......
    |..fffffffffffffffffff.............
    |....ppppp.ddddd.k.................
    |....ppppp.ddddd.k.................
    |...ppppp..ddddd.k.................
    |...ppppp..dddddkk.................
    |..ppppp...ddddd...................
    |..ppppp...ddddd...................
    |..ppppp...mmmmm...................
""")

gun("rifle", """
    |..............................................
    |..............................................
    |.......i.........................i............
    |......RRRRRRRRRRRRRRRRRRRRRRRRR..i............
    |PPAAAAssssssssssssssssssssss..HHHHHH..........
    |PPAAAAsssssssssssssssssssssssHHHHHHHHnnnnnnbbb
    |PPAAAAssssssssssssssssssssssHVHVHVHVHnnnnnnbbb
    |PPAAAAsssssssssssssssssssssslHVHVHVHHnnnnnnbbb
    |PPAAAAssssssssssssssssssssssHHHHHHHHHnnnnnnbbb
    |PPAAAAffffffffffffffffffffff..HHHHHH..........
    |..AAAAfffffffffffffffffffff...................
    |.......ppppp..ddddddd.k.......................
    |.......ppppp..ddddddd.k.......................
    |......ppppp...ddddddd.k.......................
    |......ppppp...dddddddkk.......................
    |.....ppppp.....ddddddd........................
    |.....ppppp.....ddddddd........................
    |.....ppppp......mmmmm.........................
""")

gun("ak", """
    |..............................................
    |..............................................
    |.......i..........................i...........
    |.......i..........................i...........
    |wwwwwwwsssssssssssssssssssss..WWWWWW..........
    |wwwwwwwssssssssssssssssssssssWWWWWWWWnnnnnnbbb
    |wwwwwwwsssssssssssssssssssssBWWWWWWWWnnnnnnbbb
    |wwwwwwwssssssssssssssssssssssWWWWWWWWnnnnnnbbb
    |.wwwwwwffffffffffffffffffffff.WWWWWW..........
    |..wwwwwffffffffffffffffffff...................
    |...wwww.ppppp..ddddddd.k......................
    |........ppppp..ddddddd.k......................
    |.......ppppp....ddddddd.k.....................
    |.......ppppp.....dddddddkk....................
    |......ppppp.......ddddddd.....................
    |......ppppp........ddddddd....................
    |.....ppppp..........mmmmmm....................
""")

gun("sniper", """
    |..........SSSSSSSSSSSSSSSSSSSSSS
    |.........LSSSSSSSSSSSSSSSSSSSSSSL
    |..........SSSSSSSSSSSSSSSSSSSSSS
    |..........NNN.............NNN
    |..........NNN.............NNN
    |PPWWWWWWWWssssssssssssssssssssnnnnnnnnnnnnbbbb
    |PPWWWWWWWWssssssssssssssssssssnnnnnnnnnnnnbbbb
    |PPWWWWWWWWsssssssssssssssssBssnnnnnnnnnnnnbbbb
    |PPWWWWWWWWssssssssssssssssssssnnnnnnnnnnnnbbbb
    |PPWWWWWWWWffffffffffffWWWWWWWWWWWWWWWWWW
    |..WWWWWWWWffffffffffffWWWWWWWWWWWWWWWWWW
    |...WWWWWWW.ddddd.k....WWWWWWWWWWWWWWWW
    |....pppp...ddddd.k
    |....pppp...ddddd.k
    |...pppp....dddddkk
    |...pppp....mmmmm
    |..pppp
""")

gun("shotgun", """
    |..............................................
    |...........................................e..
    |PPWWWWWWWW....................................
    |PPWWWWWWWWssssssssnnnnnnnnnnnnnnnnnnnnnnnnnbbb
    |PPWWWWWWWWssssssssnnnnnnnnnnnnnnnnnnnnnnnnnbbb
    |PPWWWWWWWWssssssssnnnnnnnnnnnnnnnnnnnnnnnnnbbb
    |PPWWWWWWWWssssssssdddddddddddddddddddddddd....
    |..WWWWWWWWffffffffdddddddddddddddddddddddd....
    |...WWWWWWWfffffff.WWWWWWWWWWWWWWWWWWWW........
    |....WWWWWW.k.k....WwWWwWWwWWwWWwWWwWWWW.......
    |....WWWWWW.kxk....WWWWWWWWWWWWWWWWWWWW........
    |...WWWWWW..kkk................................
    |...WWWWWW.....................................
    |..WWWWWW......................................
    |..WWWWWW......................................
    |.PWWWWW.......................................
    |.PPPPPP.......................................
""")


# ---------------------------------------------------------------- merging the drawing into boxes
def rectangles(rows):
    """The fewest rectangles of one material each that cover the drawing.

    Greedy and good enough: take the first unclaimed pixel, run right while the material holds, then
    run down while the whole width still holds. A pistol drops from a hundred and eighty pixels to
    about forty boxes, which is what keeps the model a sensible size.
    """
    height = len(rows)
    width = len(rows[0])
    taken = [[False] * width for _ in range(height)]
    out = []
    for y in range(height):
        for x in range(width):
            material = rows[y][x]
            if material == "." or taken[y][x]:
                continue
            span = 1
            while (x + span < width and rows[y][x + span] == material
                   and not taken[y][x + span]):
                span += 1
            deep = 1
            while y + deep < height:
                row = rows[y + deep]
                if any(row[x + step] != material or taken[y + deep][x + step]
                       for step in range(span)):
                    break
                deep += 1
            for down in range(deep):
                for step in range(span):
                    taken[y + down][x + step] = True
            out.append((material, x, y, span, deep))
    return bevel(rows, out)


def bevel(rows, boxes):
    """Shaves the exposed top and bottom edge of every part in by half a unit.

    A slab six units thick with square corners is the thing that makes a model read as a box rather
    than as an object, and no texture fixes it. Real weapons are radiused everywhere; one chamfered
    pixel along each exposed edge is enough to suggest it, and costs a handful of extra elements.

    Only edges with nothing above or below them are shaved - an edge with another part against it is
    inside the gun, and chamfering it would open a seam.
    """
    height = len(rows)
    width = len(rows[0])

    def solid(x, y):
        return 0 <= y < height and 0 <= x < width and rows[y][x] != "."

    out = []
    for material, x, y, span, deep in boxes:
        top = not any(solid(x + step, y - 1) for step in range(span))
        bottom = not any(solid(x + step, y + deep) for step in range(span))
        # A one-unit part that is exposed on both sides is chamfered once, as a whole.
        if deep == 1 and (top or bottom):
            out.append((material, x, y, span, deep, 0.5))
            continue
        if top:
            out.append((material, x, y, span, 1, 0.5))
            y, deep = y + 1, deep - 1
        if bottom and deep > 0:
            out.append((material, x, y + deep - 1, span, 1, 0.5))
            deep -= 1
        if deep > 0:
            out.append((material, x, y, span, deep, 0.0))
    return out


# ---------------------------------------------------------------- the texture
class Atlas:
    """A shelf packer. Every face of every box gets its own rectangle, so every face can be painted."""

    def __init__(self, scale):
        self.scale = scale
        self.image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        self.pixels = self.image.load()
        self.x, self.y, self.shelf = 0, 0, 0

    def place(self, width, height):
        if self.x + width > SIZE:
            self.x, self.y, self.shelf = 0, self.y + self.shelf, 0
        if self.y + height > SIZE:
            raise MemoryError("atlas full")
        spot = (self.x, self.y)
        self.x += width
        self.shelf = max(self.shelf, height)
        return spot

    def uv(self, spot, width, height):
        step = 16.0 / SIZE
        return [round(spot[0] * step, 4), round(spot[1] * step, 4),
                round((spot[0] + width) * step, 4), round((spot[1] + height) * step, 4)]


def finish(atlas, spot, width, height, base, kind, face, rng):
    """Paints one face: the light it catches, the tool marks on it, and the edge that catches more."""
    lit = shade(base, LIGHT[face])
    flat = face in ("up", "down")
    for row in range(height):
        for column in range(width):
            colour = lit
            if kind == "brushed":
                colour = shade(colour, 1.0 + 0.020 * math.sin(row * 2.3)
                               + rng.uniform(-0.012, 0.012))
            elif kind == "grit":
                colour = shade(colour, 1.0 + rng.uniform(-0.09, 0.09))
            elif kind == "serrate":
                if column % 3 == 0:
                    colour = shade(colour, 0.72)
                elif column % 3 == 1:
                    colour = shade(colour, 1.10)
                else:
                    colour = shade(colour, 1.0 + rng.uniform(-0.02, 0.02))
            elif kind == "checker":
                colour = shade(colour, 1.09 if ((column // 2) + (row // 2)) % 2 == 0 else 0.91)
            elif kind == "grain":
                streak = math.sin(row * 1.9 + math.sin(row * 0.7) * 2.0)
                colour = shade(colour, 1.0 + 0.10 * streak + rng.uniform(-0.03, 0.03))
            elif kind == "glass":
                across = (column / max(1.0, width - 1.0)) - 0.35
                down = (row / max(1.0, height - 1.0)) - 0.3
                colour = shade(colour, 1.28 - 0.80 * min(1.0, across * across + down * down) ** 0.5)

            # The bevel. A lighter pixel along the top and a darker one along the bottom is the cheapest
            # thing in this file and does more for the shape than any extra box would.
            if not flat:
                if row == 0:
                    colour = shade(colour, 1.20)
                elif row == height - 1:
                    colour = shade(colour, 0.74)
            atlas.pixels[spot[0] + column, spot[1] + row] = colour + (255,)


# ---------------------------------------------------------------- the model
def elements(rows, atlas, rng):
    """Every rectangle of the drawing, extruded and painted."""
    height = len(rows)
    width = len(rows[0])
    # Centred on the block so the display transform turns it about its own middle, and shifted far
    # enough back that a long rifle still fits inside the coordinates a model is allowed to use.
    offset = max(FLOOR + 1, min(8.0 - width / 2.0, LIMIT - width - 1))
    rise = 3.0

    out = []
    for material, x, y, span, deep, inset in rectangles(rows):
        colour, kind, z0, z1 = MATERIALS[material]
        # Never shave a part thinner than a unit and a half - a sight blade chamfered by half a unit
        # on each side would have almost nothing left of it.
        if z1 - z0 > 1.5:
            z0, z1 = z0 + inset, z1 - inset
        x0 = offset + x
        x1 = x0 + span
        y1 = rise + (height - y)
        y0 = y1 - deep

        faces = {}
        for face in ("north", "south", "east", "west", "up", "down"):
            if face in ("north", "south"):
                units = (span, deep)
            elif face in ("east", "west"):
                units = (z1 - z0, deep)
            else:
                units = (span, z1 - z0)
            pixels_wide = max(1, int(round(units[0] * atlas.scale)))
            pixels_high = max(1, int(round(units[1] * atlas.scale)))
            spot = atlas.place(pixels_wide, pixels_high)
            finish(atlas, spot, pixels_wide, pixels_high, colour, kind, face, rng)
            faces[face] = {"uv": atlas.uv(spot, pixels_wide, pixels_high), "texture": "#t"}

        out.append({"from": [round(x0, 2), round(y0, 2), z0],
                    "to": [round(x1, 2), round(y1, 2), z1],
                    "faces": faces})
    return out


def display(length, tilt=0.0, drop=0.0):
    """A quarter turn takes the muzzle - which is +x - and points it where the player is looking.

    The scale comes from the gun's own length, so a pistol and a rifle both arrive in the hand at a
    believable size: the drawing decides how long the weapon is, and the transform makes it fit.
    """
    held = round(22.0 / length, 3)
    return {
        "thirdperson_righthand": {
            "rotation": [tilt, -90, 0], "translation": [0, 3.2 - drop, 0],
            "scale": [held, held, held],
        },
        "thirdperson_lefthand": {
            "rotation": [tilt, 90, 0], "translation": [0, 3.2 - drop, 0],
            "scale": [held, held, held],
        },
        "firstperson_righthand": {
            "rotation": [tilt, -90, 0], "translation": [1.0, 2.4 - drop, 1.4],
            "scale": [round(held * 1.08, 3)] * 3,
        },
        "firstperson_lefthand": {
            "rotation": [tilt, 90, 0], "translation": [1.0, 2.4 - drop, 1.4],
            "scale": [round(held * 1.08, 3)] * 3,
        },
        "gui": {"rotation": [30, 135, 0], "translation": [0, 0, 0],
                "scale": [round(14.0 / length, 3)] * 3},
        "ground": {"rotation": [0, 0, 0], "translation": [0, 2, 0],
                   "scale": [round(9.0 / length, 3)] * 3},
        "fixed": {"rotation": [0, 90, 0], "translation": [0, 0, 0],
                  "scale": [round(16.0 / length, 3)] * 3},
    }


# The reload tips the muzzle down and brings it back. Same boxes, different hand.
FRAMES = {"": (0.0, 0.0), "_r1": (30.0, 1.5), "_r2": (58.0, 3.0)}


def paint(name, rows):
    """Every box painted into one texture. Falls to a coarser scale rather than overflowing it."""
    for scale in (6, 5, 4, 3, 2):
        atlas = Atlas(scale)
        rng = random.Random(name)
        try:
            built = elements(rows, atlas, rng)
        except MemoryError:
            continue
        return atlas.image, built, scale
    raise MemoryError(name + " does not fit its texture")


def profile_sheet():
    """Writes the side views out as a picture, so the silhouettes can be judged before anything else."""
    cell = 7
    widest = max(len(rows[0]) for rows in GUNS.values())
    tall = sum(len(rows) + 2 for rows in GUNS.values())
    image = Image.new("RGBA", (widest * cell, tall * cell), (26, 28, 34, 255))
    pixels = image.load()
    top = 0
    for name, rows in GUNS.items():
        for y, row in enumerate(rows):
            for x, material in enumerate(row):
                if material == ".":
                    continue
                colour = MATERIALS[material][0] + (255,)
                for dy in range(cell):
                    for dx in range(cell):
                        pixels[x * cell + dx, (top + y) * cell + dy] = colour
        top += len(rows) + 2
    path = os.path.join(HERE, "gun_profiles.png")
    image.save(path)
    print("wrote", path)


def main():
    if "--profile" in sys.argv:
        profile_sheet()
        return

    for folder in (ITEMS, MODELS, TEXTURES):
        os.makedirs(folder, exist_ok=True)

    for name, rows in GUNS.items():
        image, built, scale = paint(name, rows)
        image.save(os.path.join(TEXTURES, "gun_" + name + ".png"))
        length = len(rows[0])
        for suffix, (tilt, drop) in FRAMES.items():
            model = {
                "textures": {"t": "asuracraft:item/gun_" + name,
                             "particle": "asuracraft:item/gun_" + name},
                "elements": built,
                "display": display(length, tilt, drop),
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
        print("  %-8s %2d x %2d drawing -> %3d boxes, %dpx per unit"
              % (name, length, len(rows), len(built), scale))

    print("guns   ", len(GUNS), "models x", len(FRAMES), "frames")


if __name__ == "__main__":
    main()
