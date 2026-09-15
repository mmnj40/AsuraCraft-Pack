# -*- coding: utf-8 -*-
"""Builds the guns as real three-dimensional models, the way Blockbench writes them.

A Blockbench model is not a special format - it is the same item JSON Minecraft has always read, with
an "elements" list of boxes instead of a flat sprite. So a gun can be built here, box by box, and it
will open in Blockbench afterwards for anyone who wants to push a barrel a pixel to the left.

The first version of this file textured every face from a sixteen colour palette, one flat colour per
face, and it looked like it: a shape with no surface. The models people admire are not made of more
boxes than these - look closely at any of them and the boxes are just as few and just as square - they
are made of boxes whose faces have been *painted*. A slide has serrations cut across it, a grip has a
chequered panel, wood has grain running along it, every edge catches a little light at the top and
loses it at the bottom. That is the whole difference, and it is done here rather than by hand: each box
is given its own patch of the gun's own texture, and each of its six faces is painted into that patch
with the shading and the detail that face should carry.

Model space is sixteen units to a block, x running along the barrel with the muzzle at +x, y up, and z
across. The display transform then turns that to point where the player is looking.
"""
import io
import json
import math
import os
import random

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
ITEMS = os.path.join(PACK, "assets", "asuracraft", "items")
MODELS = os.path.join(PACK, "assets", "asuracraft", "models", "item")
TEXTURES = os.path.join(PACK, "assets", "asuracraft", "textures", "item")

SIZE = 256          # the texture each gun gets to itself

# The materials. Colour, and how the surface is finished - which is the part that was missing.
MATERIALS = {
    "steel":    ((84, 90, 102),   "brushed"),
    "steel_d":  ((52, 57, 66),    "brushed"),
    "steel_l":  ((122, 130, 146), "brushed"),
    "slide":    ((74, 80, 92),    "serrate"),
    "black":    ((26, 27, 32),    "grit"),
    "poly":     ((38, 40, 46),    "checker"),
    "rubber":   ((30, 31, 36),    "checker"),
    "wood":     ((122, 82, 48),   "grain"),
    "wood_d":   ((84, 55, 31),    "grain"),
    "wood_l":   ((156, 110, 64),  "grain"),
    "brass":    ((198, 158, 72),  "brushed"),
    "glass":    ((146, 208, 240), "glass"),
    "red":      ((150, 52, 44),   "flat"),
    "bright":   ((148, 155, 168), "brushed"),
    "grey":     ((96, 102, 114),  "brushed"),
}

# How much light each face is given. The gun is lit from above and a little from the muzzle end, which
# is what stops a box from reading as a single grey lump.
LIGHT = {"up": 1.20, "down": 0.52, "north": 1.02, "south": 0.90, "east": 1.10, "west": 0.74}


def shade(colour, factor):
    return tuple(max(0, min(255, int(round(channel * factor)))) for channel in colour)


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
                # Drawn metal keeps faint lengthways streaks, and they tell the eye it is metal.
                colour = shade(colour, 1.0 + 0.022 * math.sin(row * 2.3) + rng.uniform(-0.012, 0.012))
            elif kind == "grit":
                colour = shade(colour, 1.0 + rng.uniform(-0.10, 0.10))
            elif kind == "serrate":
                # Slide serrations: cut across the rear third, which is exactly where a thumb goes.
                if column < width * 0.42 and column % 3 == 0:
                    colour = shade(colour, 0.66)
                elif column < width * 0.42 and column % 3 == 1:
                    colour = shade(colour, 1.14)
                else:
                    colour = shade(colour, 1.0 + rng.uniform(-0.02, 0.02))
            elif kind == "checker":
                # The chequering on a grip panel - two pixels on, two off, which at this size reads as
                # texture rather than as a pattern.
                colour = shade(colour, 1.16 if ((column // 2) + (row // 2)) % 2 == 0 else 0.84)
            elif kind == "grain":
                streak = math.sin(row * 1.9 + math.sin(row * 0.7) * 2.0)
                colour = shade(colour, 1.0 + 0.11 * streak + rng.uniform(-0.03, 0.03))
            elif kind == "glass":
                # A lens: bright in one corner, dark away from it.
                across = (column / max(1.0, width - 1.0)) - 0.35
                down = (row / max(1.0, height - 1.0)) - 0.3
                colour = shade(colour, 1.25 - 0.75 * min(1.0, across * across + down * down) ** 0.5)

            # The bevel. A lighter pixel along the top and a darker one along the bottom is the cheapest
            # thing in this file and does more for the shape than any extra box would.
            if not flat:
                if row == 0:
                    colour = shade(colour, 1.22)
                elif row == height - 1:
                    colour = shade(colour, 0.70)
            if column == 0 or column == width - 1:
                colour = shade(colour, 0.90)

            atlas.pixels[spot[0] + column, spot[1] + row] = colour + (255,)


def box(x0, y0, z0, x1, y1, z1, material, top=None, deco=None):
    """One cuboid, held as numbers until an atlas exists to paint it into."""
    return {"box": (x0, y0, z0, x1, y1, z1), "material": material, "top": top, "deco": deco}


def build(part, atlas, rng):
    """Turns one held cuboid into a model element, painting its six faces on the way past."""
    x0, y0, z0, x1, y1, z1 = part["box"]
    across, tall, deep = x1 - x0, y1 - y0, z1 - z0
    faces = {}
    for face in ("north", "south", "east", "west", "up", "down"):
        material = part["material"]
        if face == "up" and part["top"]:
            material = part["top"]
        base, kind = MATERIALS[material]
        if part["deco"] and face in ("north", "south", "up"):
            kind = part["deco"]

        if face in ("north", "south"):
            units = (across, tall)
        elif face in ("east", "west"):
            units = (deep, tall)
        else:
            units = (across, deep)
        width = max(1, int(round(units[0] * atlas.scale)))
        height = max(1, int(round(units[1] * atlas.scale)))

        spot = atlas.place(width, height)
        finish(atlas, spot, width, height, base, kind, face, rng)
        faces[face] = {"uv": atlas.uv(spot, width, height), "texture": "#t"}
    return {"from": [x0, y0, z0], "to": [x1, y1, z1], "faces": faces}


# Each gun: a list of boxes, built lying along x with the muzzle to the right. A trigger guard is three
# thin bars rather than one block, so there is a real hole for a finger; a grip is a short stack of
# boxes stepped backwards, which is how a slanted grip is made out of square things.
GUNS = {
    # A pistol built the way the reference is: a slide with serrations, a frame under it, a grip made of
    # three boxes stepped backwards so it leans, and small hard parts - sights, lever, hammer - for the
    # eye to catch on.
    "pistol": [
        box(4.6, 8.2, 6.6, 13.2, 11.0, 9.4, "slide", top="steel_l"),      # slide
        box(4.6, 10.6, 6.5, 13.2, 11.1, 9.5, "steel_l"),                  # top rib
        box(8.6, 9.4, 9.4, 11.4, 10.4, 9.6, "black"),                     # ejection port
        box(12.9, 9.0, 7.2, 14.1, 10.4, 8.8, "black"),                    # muzzle
        box(13.6, 9.3, 7.5, 14.2, 10.1, 8.5, "steel_d"),                  # crown
        box(4.9, 5.4, 6.9, 12.6, 8.3, 9.1, "steel_d", top="steel"),       # frame
        box(11.2, 5.6, 6.8, 12.8, 7.4, 9.2, "black", deco="checker"),     # accessory rail
        box(7.4, 8.4, 6.5, 8.2, 9.2, 9.5, "red"),                         # marking
        box(9.6, 8.5, 6.4, 10.2, 9.1, 9.6, "bright"),                     # slide-stop lever
        box(4.4, 4.2, 6.9, 7.9, 5.6, 9.1, "poly"),                        # grip, leaning back
        box(3.9, 2.6, 6.9, 7.4, 4.3, 9.1, "poly"),
        box(3.4, 1.0, 6.9, 6.9, 2.7, 9.1, "poly"),
        box(3.2, 0.6, 6.8, 7.0, 1.2, 9.2, "black"),                       # magazine floor
        box(3.3, 1.1, 6.75, 6.9, 5.4, 6.95, "rubber", deco="checker"),    # chequered panels
        box(3.3, 1.1, 9.05, 6.9, 5.4, 9.25, "rubber", deco="checker"),
        box(7.6, 5.0, 7.3, 8.4, 5.6, 8.7, "steel_d"),                     # guard, front bar
        box(7.6, 3.9, 7.3, 10.6, 4.6, 8.7, "steel_d"),                    # guard, bottom bar
        box(10.0, 4.4, 7.3, 10.8, 5.5, 8.7, "steel_d"),                   # guard, rear joint
        box(8.4, 4.6, 7.5, 9.1, 5.6, 8.5, "black"),                       # trigger
        box(12.1, 11.0, 7.6, 12.7, 11.9, 8.4, "black"),                   # front sight
        box(5.0, 11.0, 7.0, 5.7, 11.9, 9.0, "black"),                     # rear sight
        box(5.0, 11.0, 7.8, 5.7, 11.9, 8.2, "steel_d"),                   # its notch
        box(4.2, 8.6, 7.4, 4.9, 9.8, 8.6, "steel_d"),                     # hammer
    ],
    # Everything longer than a pistol is laid out in the same order along x, tail to nose, with nothing
    # buried inside anything else: butt, stock, receiver, handguard, barrel, muzzle. That one rule is
    # what the first draft of these was missing and why they read as a pile of blocks.
    "smg": [
        box(0.0, 8.4, 6.9, 0.7, 11.2, 9.1, "black", deco="checker"),      # butt pad
        box(0.7, 9.0, 7.4, 2.4, 10.4, 8.6, "steel_d"),                    # folding stock arm
        box(2.4, 8.2, 6.6, 10.0, 11.0, 9.4, "slide", top="steel_l"),      # receiver
        box(2.6, 11.0, 7.2, 9.8, 11.6, 8.8, "black", deco="checker"),     # top rail
        box(10.0, 8.4, 6.8, 13.0, 10.6, 9.2, "black"),                    # handguard
        box(10.3, 8.9, 6.7, 12.7, 10.1, 6.85, "steel_d", deco="checker"), # its vents
        box(10.3, 8.9, 9.15, 12.7, 10.1, 9.3, "steel_d", deco="checker"),
        box(13.0, 9.2, 7.4, 15.0, 10.2, 8.6, "steel_d"),                  # barrel
        box(15.0, 9.0, 7.2, 15.7, 10.4, 8.8, "black"),                    # muzzle
        box(7.0, 5.0, 7.4, 8.6, 8.2, 8.6, "steel_d", top="steel"),        # magazine
        box(7.2, 2.2, 7.4, 8.8, 5.2, 8.6, "steel_d"),                     # its lower half, forward
        box(7.05, 5.1, 7.3, 8.55, 8.1, 7.45, "black", deco="checker"),    # its ribs
        box(7.0, 1.7, 7.3, 9.0, 2.4, 8.7, "black"),                       # floor plate
        box(4.6, 4.6, 7.0, 6.6, 8.2, 9.0, "poly", deco="checker"),        # grip
        box(4.4, 2.8, 7.0, 6.4, 4.8, 9.0, "poly", deco="checker"),
        box(4.3, 2.3, 6.9, 6.5, 3.0, 9.1, "black"),
        box(6.5, 6.4, 7.4, 7.1, 8.2, 8.6, "steel_d"),                     # guard, front
        box(6.5, 5.7, 7.4, 9.0, 6.5, 8.6, "steel_d"),                     # guard, bottom
        box(7.2, 6.4, 7.6, 7.9, 7.4, 8.4, "black"),                       # trigger
        box(8.6, 9.4, 6.3, 9.8, 10.2, 6.6, "bright"),                     # charging handle
        box(12.5, 11.0, 7.6, 13.1, 12.6, 8.4, "black"),                   # front post
        box(12.4, 12.4, 7.5, 13.2, 12.8, 8.5, "steel_d"),                 # its hood
        box(3.0, 11.6, 7.4, 3.6, 12.8, 8.6, "black"),                     # rear aperture
        box(3.0, 11.6, 7.85, 3.6, 12.8, 8.15, "steel_d"),
    ],
    "rifle": [
        box(0.0, 7.6, 6.8, 0.7, 11.4, 9.2, "black", deco="checker"),      # butt pad
        box(0.7, 8.0, 7.0, 3.2, 11.2, 9.0, "steel_d", top="steel"),       # stock
        box(1.0, 7.6, 7.4, 3.0, 8.2, 8.6, "black"),                       # its underside
        box(3.2, 8.0, 6.6, 9.8, 11.2, 9.4, "slide", top="steel_l"),       # receiver
        box(3.4, 11.2, 7.2, 13.0, 11.8, 8.8, "black", deco="checker"),    # rail, full length
        box(9.8, 8.4, 6.8, 13.2, 10.8, 9.2, "black"),                     # handguard
        box(10.1, 8.9, 6.7, 12.9, 10.3, 6.85, "steel_d", deco="checker"), # its vents
        box(10.1, 8.9, 9.15, 12.9, 10.3, 9.3, "steel_d", deco="checker"),
        box(13.2, 9.2, 7.4, 15.2, 10.2, 8.6, "steel_d"),                  # barrel
        box(15.2, 9.0, 7.2, 16.0, 10.4, 8.8, "black", deco="checker"),    # flash hider
        box(12.8, 10.8, 7.5, 13.4, 13.0, 8.5, "black"),                   # gas block and front post
        box(12.7, 12.8, 7.4, 13.5, 13.2, 8.6, "steel_d"),
        box(3.6, 11.8, 7.4, 4.2, 13.0, 8.6, "black"),                     # rear aperture
        box(3.6, 11.8, 7.85, 4.2, 13.0, 8.15, "steel_d"),
        box(7.2, 5.0, 7.3, 8.8, 8.0, 8.7, "steel_d", top="steel"),        # magazine
        box(7.5, 2.6, 7.3, 9.1, 5.2, 8.7, "steel_d"),                     # its curve
        box(7.9, 1.4, 7.3, 9.5, 2.9, 8.7, "steel_d"),
        box(7.25, 5.1, 7.2, 8.75, 7.9, 7.35, "black", deco="checker"),
        box(4.4, 4.6, 7.0, 6.4, 8.0, 9.0, "poly", deco="checker"),        # grip
        box(4.2, 2.8, 7.0, 6.2, 4.8, 9.0, "poly", deco="checker"),
        box(4.1, 2.3, 6.9, 6.3, 3.0, 9.1, "black"),
        box(6.4, 6.4, 7.4, 7.0, 8.0, 8.6, "steel_d"),                     # guard, front
        box(6.4, 5.7, 7.4, 9.0, 6.5, 8.6, "steel_d"),                     # guard, bottom
        box(7.1, 6.4, 7.6, 7.8, 7.4, 8.4, "black"),                       # trigger
        box(8.6, 9.6, 9.4, 9.8, 10.6, 9.6, "black"),                      # ejection port cover
        box(9.2, 10.4, 6.4, 9.9, 11.0, 6.6, "bright"),                    # forward assist
    ],
    "sniper": [
        box(0.0, 7.0, 6.7, 0.8, 11.4, 9.3, "black", deco="checker"),      # recoil pad
        box(0.8, 7.2, 6.8, 3.4, 11.2, 9.2, "wood", top="wood_l"),         # butt stock
        box(2.0, 11.2, 6.9, 4.6, 12.1, 9.1, "wood_l"),                    # comb
        box(3.2, 5.6, 7.0, 5.8, 8.6, 9.0, "wood", top="wood_d"),          # wrist
        box(3.3, 5.5, 6.95, 5.7, 8.0, 7.1, "wood_d", deco="checker"),     # chequering
        box(3.3, 5.5, 8.9, 5.7, 8.0, 9.05, "wood_d", deco="checker"),
        box(3.4, 8.4, 6.7, 10.0, 11.0, 9.3, "slide", top="steel_l"),      # receiver
        box(10.0, 9.0, 7.3, 15.0, 10.4, 8.7, "steel_d"),                  # heavy barrel
        box(15.0, 8.8, 7.2, 16.0, 10.6, 8.8, "black"),                    # muzzle brake
        box(15.2, 9.3, 7.0, 15.8, 10.1, 9.0, "steel_d"),                  # its ports
        box(10.0, 7.8, 6.9, 13.2, 9.2, 9.1, "wood", top="wood_l"),        # forend
        box(10.1, 7.7, 6.85, 13.1, 8.2, 9.15, "wood_d"),
        box(4.6, 12.2, 7.0, 11.4, 14.2, 9.0, "steel_d", top="steel"),     # scope tube
        box(4.2, 12.0, 6.8, 5.2, 14.4, 9.2, "black"),                     # eyepiece bell
        box(10.8, 12.0, 6.8, 11.8, 14.4, 9.2, "black"),                   # objective bell
        box(4.15, 12.3, 7.1, 4.3, 14.2, 8.9, "glass"),                    # the lenses
        box(11.7, 12.3, 7.1, 11.85, 14.2, 8.9, "glass"),
        box(7.2, 14.2, 7.6, 8.4, 14.9, 8.4, "black", deco="checker"),     # elevation turret
        box(7.8, 12.8, 9.0, 8.6, 13.6, 9.6, "black", deco="checker"),     # windage turret
        box(5.4, 11.0, 7.5, 6.2, 12.3, 8.5, "steel_d"),                   # mounts
        box(9.6, 11.0, 7.5, 10.4, 12.3, 8.5, "steel_d"),
        box(6.6, 4.4, 7.3, 8.4, 8.4, 8.7, "steel_d", top="steel"),        # short magazine
        box(6.5, 3.8, 7.2, 8.5, 4.6, 8.8, "black"),
        box(5.8, 7.0, 7.4, 6.4, 8.4, 8.6, "steel_d"),                     # guard, front
        box(5.8, 6.3, 7.4, 8.4, 7.1, 8.6, "steel_d"),                     # guard, bottom
        box(6.5, 7.0, 7.6, 7.2, 7.9, 8.4, "black"),                       # trigger
        box(8.4, 10.2, 9.3, 10.0, 10.9, 9.5, "bright"),                   # bolt body
        box(9.4, 9.8, 9.5, 10.0, 10.6, 10.4, "bright"),                   # bolt handle
        box(9.9, 9.5, 10.2, 10.3, 10.3, 10.7, "black"),                   # its knob
        box(13.4, 5.4, 7.6, 14.0, 7.8, 8.4, "steel_d"),                   # bipod
        box(13.4, 4.6, 6.2, 14.0, 5.6, 7.8, "black"),
        box(13.4, 4.6, 8.2, 14.0, 5.6, 9.8, "black"),
    ],
    "shotgun": [
        box(0.0, 7.4, 6.8, 0.8, 11.2, 9.2, "black", deco="checker"),      # recoil pad
        box(0.8, 7.6, 6.9, 3.0, 11.0, 9.1, "wood", top="wood_l"),         # butt stock
        box(1.6, 5.4, 7.0, 4.0, 8.2, 9.0, "wood", top="wood_d"),          # wrist
        box(1.7, 5.3, 6.95, 3.9, 7.8, 7.1, "wood_d", deco="checker"),     # chequering
        box(1.7, 5.3, 8.9, 3.9, 7.8, 9.05, "wood_d", deco="checker"),
        box(3.0, 8.2, 6.8, 6.0, 11.0, 9.2, "steel", top="steel_l"),       # receiver
        box(3.2, 11.0, 7.5, 5.8, 11.4, 8.5, "steel_l"),                   # its rib
        box(6.0, 9.0, 7.2, 15.0, 10.6, 8.8, "steel", top="steel_l"),      # barrel
        box(15.0, 8.9, 7.1, 15.9, 10.7, 8.9, "black"),                    # muzzle
        box(6.0, 7.4, 7.4, 13.6, 8.7, 8.6, "steel_d"),                    # magazine tube
        box(7.6, 6.6, 6.85, 11.2, 8.4, 9.15, "wood", top="wood_l"),       # pump
        box(7.8, 6.5, 6.8, 8.2, 8.5, 9.2, "wood_d"),                      # its grooves
        box(8.8, 6.5, 6.8, 9.2, 8.5, 9.2, "wood_d"),
        box(9.8, 6.5, 6.8, 10.2, 8.5, 9.2, "wood_d"),
        box(10.6, 6.5, 6.8, 11.0, 8.5, 9.2, "wood_d"),
        box(4.0, 7.2, 7.4, 4.6, 8.4, 8.6, "steel_d"),                     # guard, front
        box(4.0, 6.5, 7.4, 6.2, 7.3, 8.6, "steel_d"),                     # guard, bottom
        box(4.7, 7.2, 7.6, 5.4, 8.1, 8.4, "black"),                       # trigger
        box(4.4, 8.6, 9.2, 5.6, 9.6, 9.4, "black"),                       # ejection port
        box(4.6, 8.8, 9.4, 5.3, 9.4, 9.6, "brass"),                       # a shell in it
        box(14.0, 10.6, 7.7, 14.5, 11.3, 8.3, "brass"),                   # bead sight
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


def paint(name, boxes):
    """Every box painted into one texture. Falls to a coarser scale rather than overflowing it."""
    for scale in (5, 4, 3, 2):
        atlas = Atlas(scale)
        rng = random.Random(name)
        try:
            elements = [build(part, atlas, rng) for part in boxes]
        except MemoryError:
            continue
        return atlas.image, elements, scale
    raise MemoryError(name + " does not fit its texture")


def main():
    for folder in (ITEMS, MODELS, TEXTURES):
        os.makedirs(folder, exist_ok=True)

    for name, boxes in GUNS.items():
        image, elements, scale = paint(name, boxes)
        image.save(os.path.join(TEXTURES, "gun_" + name + ".png"))
        for suffix, block in FRAMES.items():
            model = {
                "textures": {"t": "asuracraft:item/gun_" + name,
                             "particle": "asuracraft:item/gun_" + name},
                "elements": elements,
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
        print("  %-8s %2d boxes, %d faces painted at %dpx per unit"
              % (name, len(boxes), len(boxes) * 6, scale))

    print("guns   ", len(GUNS), "models x", len(FRAMES), "frames")


if __name__ == "__main__":
    main()
