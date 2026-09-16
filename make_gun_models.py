# -*- coding: utf-8 -*-
"""Builds the guns: eight weapons drawn as shapes, solidified, and written as Minecraft item models.

Three attempts got here. The first placed a dozen large boxes by hand and looked like a dozen large
boxes. The second drew each gun as ASCII at one character per model unit, which fixed the silhouette
but left every part the same thickness - a flat shape rolled out sideways, with square corners
everywhere and a pistol as big as a rifle. This one fixes what was left:

  drawn with shapes     circles, rounded rectangles, tapers and - for a trigger guard - an actual
                        annulus, at a third of a model unit, so curves are curves
  solid, not extruded   every material carries a cross-section, so a barrel is round, a receiver has
                        a broken edge and a sight is still a flat blade
  sized like a weapon   a pistol arrives in the hand at under half a block and a rifle at well over
                        one, instead of every gun being the same length because one constant decided
                        it

The drawing is still the part a person judges. Run with --profile for the side elevations.

Model space is sixteen units to a block, x along the barrel with the muzzle at +x, y up, z across.
Elements must sit between -16 and 32, which is where the forty-eight unit ceiling on length comes from.
"""
import io
import json
import math
import os
import random
import sys

from PIL import Image

from gunsmith import RES, Sketch, solidify

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
ITEMS = os.path.join(PACK, "assets", "asuracraft", "items")
MODELS = os.path.join(PACK, "assets", "asuracraft", "models", "item")
TEXTURES = os.path.join(PACK, "assets", "asuracraft", "textures", "item")

SIZE = 1024
LIMIT, FLOOR = 32.0, -16.0

# colour, finish, half-width in model units, cross-section
MATERIALS = {
    "s": ((78, 84, 96),    "brushed", 3.00, "dee"),    # slide / receiver
    "z": ((74, 80, 92),    "serrate", 3.00, "dee"),    # cut serrations at the back of a slide
    "t": ((116, 124, 140), "brushed", 2.55, "soft"),   # slide top rib
    "f": ((46, 50, 58),    "brushed", 2.70, "soft"),   # frame
    "b": ((26, 27, 32),    "grit",    1.45, "round"),  # barrel, muzzle
    "n": ((40, 43, 50),    "brushed", 1.90, "round"),  # heavy barrel
    "p": ((33, 35, 41),    "checker", 2.55, "soft"),   # grip
    "k": ((52, 57, 66),    "brushed", 1.05, "round"),  # trigger guard
    "x": ((26, 27, 32),    "grit",    0.70, "soft"),   # trigger
    "i": ((22, 23, 28),    "grit",    0.65, "rect"),   # iron sight
    "r": ((150, 52, 44),   "flat",    3.10, "rect"),   # painted marking, proud of the slide
    "l": ((150, 157, 170), "brushed", 3.25, "rect"),   # lever, catch, release
    "m": ((26, 27, 32),    "grit",    1.95, "soft"),   # magazine floor plate
    "d": ((50, 54, 62),    "brushed", 1.80, "soft"),   # magazine body
    "R": ((24, 25, 30),    "checker", 1.75, "rect"),   # rail
    "H": ((52, 56, 64),    "brushed", 2.25, "round"),  # handguard
    "V": ((20, 22, 27),    "grit",    1.30, "rect"),   # vent slot, recessed into its host
    "A": ((46, 49, 56),    "brushed", 2.50, "soft"),   # stock
    "P": ((24, 25, 30),    "checker", 2.75, "soft"),   # butt pad
    "W": ((124, 84, 48),   "grain",   2.65, "soft"),   # wood
    "w": ((86, 57, 32),    "grain",   2.80, "soft"),   # dark wood
    "S": ((48, 52, 60),    "brushed", 1.60, "round"),  # scope tube
    "N": ((40, 44, 52),    "brushed", 1.00, "soft"),   # scope mount
    "L": ((148, 210, 242), "glass",   1.35, "round"),  # lens
    "B": ((140, 147, 160), "brushed", 0.95, "round"),  # bolt handle
    "e": ((196, 158, 74),  "brushed", 0.80, "round"),  # brass
    "Q": ((152, 150, 144), "brushed", 1.60, "soft"),   # concrete panel
    "q": ((104, 102, 98),  "grit",    2.10, "soft"),   # concrete kerb and cap
    "G": ((72, 76, 84),    "brushed", 2.10, "soft"),   # steel post
    "E": ((126, 88, 58),   "grit",    1.70, "rect"),   # rust running down it
    "W1": ((240, 238, 232), "flat",    1.85, "rect"),   # gauze, rolled - a clean slab, no terracing
    "N1": ((240, 238, 232), "roll",    4.50, "rect"),   # a boxed dressing: rolled gauze
    "N2": ((219, 216, 208), "flat",    4.50, "rect"),   # the fold lines printed on it
    "N3": ((250, 250, 246), "flat",    4.66, "rect"),   # the cross, a shade proud so it catches light
    "D1": ((78, 178, 92),   "flat",    4.56, "rect"),   # tier band, green
    "D2": ((78, 148, 212),  "flat",    4.56, "rect"),   # tier band, blue
    "D3": ((206, 62, 54),   "flat",    4.56, "rect"),   # tier band, red
    "W2": ((214, 211, 203), "flat",    1.85, "rect"),   # the line between wraps, printed not cut
    "W3": ((246, 244, 239), "flat",    0.55, "rect"),   # the loose end, one thickness of gauze
    "B1": ((210, 213, 220), "flat",    0.45, "rect"),   # blister foil, genuinely thin
    "B3": ((162, 166, 174), "flat",    0.45, "rect"),   # the perforation down the middle
    "B2": ((236, 208, 86),  "flat",    0.95, "rect"),   # a pill under the foil
    "C1": ((86, 182, 96),   "flat",    1.85, "rect"),   # the green edge
    "C2": ((86, 152, 214),  "flat",    1.85, "rect"),   # the blue edge
    "C3": ((202, 66, 58),   "flat",    1.85, "rect"),   # the red edge
    "K1": ((198, 54, 48),   "flat",    2.95, "soft"),   # medical red, standing proud
    "K2": ((234, 234, 230), "flat",    2.60, "soft"),   # case shell
    "K3": ((104, 108, 118), "brushed", 1.30, "soft"),   # handle, seam and catches
    "K4": ((88, 102, 66),   "checker", 2.35, "soft"),   # olive webbing - the field pouch
    "K5": ((238, 240, 236), "flat",    2.55, "soft"),   # a white cross sewn onto it
    "K6": ((166, 170, 178), "brushed", 2.50, "rect"),   # a zip
    "K7": ((214, 216, 222), "brushed", 1.45, "soft"),   # chrome latch
    "K8": ((186, 46, 42),   "flat",    2.60, "soft"),   # the medkit's red shell
    "K9": ((242, 244, 240), "flat",    2.95, "soft"),   # a white cross standing proud of it
    "P1": ((224, 188, 62),  "brushed", 1.90, "round"),  # pill bottle
    "P2": ((240, 240, 236), "brushed", 2.00, "round"),  # its cap
    "Y1": ((222, 230, 238), "glass",   1.40, "round"),  # syringe barrel
    "Y2": ((92, 178, 108),  "flat",    1.15, "round"),  # what is in it
    "Y3": ((240, 242, 246), "flat",    1.15, "round"),
    "Y4": ((186, 190, 198), "brushed", 0.70, "round"),  # steel
    "Y5": ((216, 196, 96),  "brushed", 1.50, "round"),  # a gold collar on the good one
    "A1": ((54, 86, 138),   "flat",    1.95, "round"),  # the body of an auto-injector
    "A2": ((58, 148, 78),   "flat",    2.05, "round"),  # its cap
    "A3": ((28, 30, 36),    "flat",    2.00, "rect"),   # the grip band round it
    "A4": ((236, 238, 244), "flat",    2.02, "rect"),   # a white stripe down the body
    "o": ((96, 102, 114), "brushed", 3.00, "round"),  # revolver cylinder, proud of the frame
    "j": ((72, 78, 90),    "brushed", 1.95, "round"),  # revolver barrel, same steel as the frame
}

LIGHT = {"up": 1.22, "down": 0.52, "north": 1.03, "south": 0.88, "east": 1.12, "west": 0.74}


def shade(colour, factor):
    return tuple(max(0, min(255, int(round(channel * factor)))) for channel in colour)


# ---------------------------------------------------------------- the weapons
GUNS = {}


def design(name, length, height, blocks, build):
    """One weapon. `blocks` is how long it should appear in the hand, in blocks."""
    sketch = Sketch(length, height)
    build(sketch)
    GUNS[name] = (sketch, blocks)


def pistol(g):
    g.rect("m", 1.0, 0.0, 6.6, 0.7)
    g.taper("p", 1.4, 0.7, 6.9, 7.2, top_shift=1.5)
    g.rrect("f", 2.6, 7.0, 21.0, 9.7, 0.35)
    g.rect("R", 15.5, 6.5, 20.8, 7.1)
    g.ring("k", 11.0, 5.4, 3.4, 2.4, 0.75)
    g.rrect("x", 10.1, 4.3, 11.1, 6.3, 0.3)
    g.rrect("s", 2.0, 9.6, 21.6, 12.9, 0.45)
    g.rect("z", 2.0, 9.9, 7.6, 12.7)
    g.rect("t", 2.0, 12.6, 21.6, 13.1)
    g.rect("b", 13.2, 11.5, 16.6, 12.5)          # ejection port, recessed by its own width
    g.rrect("b", 21.6, 10.6, 23.8, 12.1, 0.5)    # muzzle
    g.rect("i", 20.0, 13.1, 20.9, 14.0)
    g.rect("i", 2.8, 13.1, 3.9, 14.0)
    g.erase(3.1, 13.5, 3.6, 14.1)                # the notch in the rear sight
    g.rect("l", 8.4, 9.1, 10.6, 9.7)
    g.rect("r", 8.9, 11.1, 9.6, 11.8)


def magnum(g):
    """A revolver, which is a completely different machine from the two automatics either side of it.

    The cylinder is the whole point. It is the widest part of the gun, it stands proud of the frame on
    both sides, it is fluted, and it is lighter than everything around it - the first attempt made it
    the same grey as the frame it sits in, which is the same as not drawing it at all.
    """
    g.rect("m", 1.6, 0.0, 5.6, 0.6)
    g.taper("p", 1.9, 0.6, 6.4, 7.2, top_shift=1.4)
    g.rrect("f", 3.4, 6.8, 13.4, 10.8, 0.5)      # frame
    g.ellipse("o", 8.6, 9.2, 3.0, 2.6)           # cylinder
    g.stripe("V", 6.6, 8.0, 10.8, 10.4, 1.1, 0.45)    # its flutes
    g.rect("f", 5.0, 11.2, 13.4, 12.4)           # top strap over the cylinder
    g.rrect("j", 12.4, 10.0, 22.8, 12.4, 0.5)    # barrel
    g.rect("R", 12.4, 12.3, 22.8, 12.8)          # the rib along the top of it
    g.rrect("j", 12.6, 8.6, 21.4, 10.2, 0.5)     # under-lug
    g.rrect("b", 22.6, 10.2, 24.4, 12.2, 0.4)    # muzzle
    g.ring("k", 10.0, 5.4, 2.8, 2.2, 0.7)
    g.rrect("x", 9.2, 4.4, 10.1, 6.2, 0.3)
    g.rect("l", 3.4, 10.8, 5.0, 12.0)            # hammer spur
    g.rect("i", 21.4, 12.8, 22.3, 13.6)
    g.rect("i", 5.6, 12.4, 6.7, 13.2)
    g.erase(6.0, 12.8, 6.4, 13.3)


def deagle(g):
    g.rect("m", 1.0, 0.0, 7.4, 0.8)
    g.taper("p", 1.4, 0.8, 7.8, 7.4, top_shift=1.4)
    g.rrect("f", 2.6, 7.2, 25.0, 10.0, 0.35)
    g.rect("R", 18.0, 6.7, 24.6, 7.3)
    g.ring("k", 11.4, 5.6, 3.5, 2.5, 0.8)
    g.rrect("x", 10.5, 4.5, 11.5, 6.5, 0.3)
    g.rrect("s", 2.0, 9.9, 25.4, 13.6, 0.5)      # the big square slide the Eagle is known for
    g.rect("z", 2.0, 10.2, 8.4, 13.4)
    g.rect("t", 2.0, 13.4, 25.4, 13.9)
    g.stripe("V", 15.0, 13.4, 24.0, 13.95, 1.6, 0.6)  # barrel flats
    g.rect("b", 15.0, 12.1, 19.2, 13.1)
    g.rrect("b", 25.4, 11.0, 27.8, 13.0, 0.6)
    g.rect("i", 24.0, 13.9, 24.9, 14.9)
    g.rect("i", 3.2, 13.9, 4.4, 14.9)
    g.erase(3.6, 14.3, 4.0, 15.0)
    g.rect("l", 9.4, 9.4, 11.8, 10.0)
    g.rect("r", 9.8, 11.8, 10.5, 12.5)


def smg(g):
    g.rect("P", 0.0, 7.4, 1.6, 12.6)
    g.rrect("A", 1.6, 9.2, 8.0, 11.2, 0.4)       # folding stock arm
    g.rrect("s", 8.0, 7.6, 22.0, 12.8, 0.5)
    g.rect("z", 8.0, 7.9, 12.0, 12.6)
    g.rect("R", 9.0, 12.7, 21.0, 13.3)
    g.rrect("H", 22.0, 8.8, 28.0, 11.8, 0.7)     # handguard
    g.stripe("V", 22.6, 9.4, 27.4, 11.2, 1.4, 0.5)
    g.rrect("n", 28.0, 9.6, 32.4, 11.0, 0.5)
    g.rrect("b", 32.4, 9.4, 33.8, 11.2, 0.4)
    g.taper("p", 10.6, 1.6, 14.0, 7.6, top_shift=1.1)
    g.rect("d", 16.0, 1.4, 19.0, 7.6)            # magazine, straight and forward of the grip
    g.rect("m", 15.7, 0.8, 19.3, 1.5)
    g.ring("k", 14.6, 6.0, 2.2, 1.8, 0.6)
    g.rrect("x", 13.9, 5.2, 14.8, 6.7, 0.3)
    g.rect("i", 10.4, 13.3, 11.3, 15.0)
    g.rect("i", 25.6, 13.0, 26.5, 15.2)
    g.rect("l", 20.4, 12.2, 22.0, 12.8)


def rifle(g):
    g.rect("P", 0.0, 7.0, 1.8, 12.8)
    g.rrect("A", 1.8, 7.6, 9.0, 12.4, 0.5)       # stock
    g.erase(3.0, 8.4, 8.0, 10.4)                  # the cut-out through it
    g.rrect("s", 9.0, 7.8, 28.0, 13.0, 0.5)
    g.rect("R", 9.6, 12.9, 38.0, 13.5)
    g.rrect("H", 28.0, 8.8, 38.0, 12.4, 0.8)
    g.stripe("V", 28.8, 9.4, 37.2, 11.8, 1.6, 0.6)
    g.rrect("n", 38.0, 9.8, 43.4, 11.4, 0.5)
    g.rrect("b", 43.4, 9.4, 45.6, 11.8, 0.6)     # flash hider
    g.taper("p", 11.0, 1.8, 14.6, 7.8, top_shift=1.2)
    g.taper("d", 16.6, 2.2, 19.8, 7.8, bottom_shift=1.3)
    g.rect("m", 17.6, 1.5, 21.4, 2.4)
    g.ring("k", 15.4, 6.2, 2.3, 1.8, 0.6)
    g.rrect("x", 14.6, 5.4, 15.6, 6.9, 0.3)
    g.rect("i", 11.4, 13.5, 12.4, 15.6)          # rear aperture
    g.erase(11.7, 14.6, 12.1, 15.7)
    g.rect("i", 36.0, 13.5, 37.0, 16.0)          # front post
    g.rect("N", 35.4, 15.8, 37.6, 16.4)
    g.rect("l", 26.0, 12.4, 27.8, 13.0)
    g.rect("b", 24.0, 11.4, 27.0, 12.4)          # ejection port


def ak(g):
    g.rect("w", 0.0, 7.2, 8.4, 12.4)             # wooden butt
    g.erase(1.6, 8.2, 6.4, 10.2)
    g.rrect("s", 8.4, 7.6, 27.0, 12.8, 0.5)
    g.rrect("W", 27.0, 10.2, 36.0, 12.4, 0.6)    # upper handguard
    g.rrect("W", 26.4, 7.6, 35.0, 9.8, 0.7)      # lower handguard, held by the front hand
    g.rrect("n", 36.0, 9.6, 42.8, 11.4, 0.5)
    g.rrect("b", 42.8, 9.2, 45.4, 11.8, 0.6)
    g.rect("B", 25.4, 12.4, 28.6, 13.4)          # the charging handle, on its own side
    g.taper("p", 11.2, 2.0, 14.8, 7.6, top_shift=1.2)
    # The banana: two tapers, each leaning further forward than the one above it.
    g.taper("d", 16.4, 4.2, 20.0, 7.6, bottom_shift=1.0)
    g.taper("d", 17.4, 1.4, 21.0, 4.4, bottom_shift=1.6)
    g.rect("m", 18.8, 0.8, 22.8, 1.7)
    g.ring("k", 15.6, 6.0, 2.3, 1.8, 0.6)
    g.rrect("x", 14.8, 5.2, 15.8, 6.7, 0.3)
    g.rect("i", 10.6, 12.9, 11.6, 14.8)
    g.rect("i", 34.2, 12.5, 35.2, 15.0)
    g.rect("N", 33.6, 14.8, 35.8, 15.4)


def sniper(g):
    g.rect("P", 0.0, 6.4, 1.8, 12.4)
    g.rrect("W", 1.8, 6.8, 10.0, 12.6, 0.6)
    g.rrect("W", 6.0, 12.4, 14.0, 13.6, 0.5)     # the comb, where a cheek goes
    g.rrect("s", 10.0, 8.0, 28.0, 12.6, 0.5)
    g.rrect("n", 28.0, 9.4, 42.0, 11.6, 0.6)     # heavy barrel
    g.rrect("b", 42.0, 9.0, 45.0, 12.0, 0.7)     # muzzle brake
    g.rrect("W", 20.0, 7.2, 34.0, 9.6, 0.6)      # forend
    g.rrect("S", 12.0, 15.2, 32.0, 18.0, 0.9)    # scope tube
    g.rrect("S", 11.0, 14.8, 13.4, 18.4, 0.6)    # eyepiece bell
    g.rrect("S", 30.6, 14.8, 33.0, 18.4, 0.6)    # objective bell
    g.rect("L", 11.0, 15.2, 11.7, 18.0)
    g.rect("L", 32.3, 15.2, 33.0, 18.0)
    g.rect("N", 13.6, 12.4, 16.2, 15.4)          # mounts, reaching down to the receiver
    g.rect("N", 25.6, 12.4, 28.2, 15.4)
    g.rrect("N", 20.0, 18.0, 22.4, 19.2, 0.4)    # elevation turret
    g.rect("B", 25.0, 12.2, 28.4, 13.2)
    g.taper("p", 11.6, 2.4, 15.0, 8.0, top_shift=1.0)
    g.rect("d", 17.0, 3.4, 20.0, 8.0)
    g.rect("m", 16.7, 2.6, 20.3, 3.5)
    g.ring("k", 15.8, 6.4, 2.2, 1.8, 0.6)
    g.rrect("x", 15.0, 5.6, 16.0, 7.1, 0.3)


def shotgun(g):
    g.rect("P", 0.0, 6.6, 1.8, 12.4)
    g.rrect("W", 1.8, 7.0, 10.0, 12.4, 0.6)
    g.taper("W", 7.2, 4.4, 10.8, 8.6, top_shift=0.8)   # the wrist, gripped like a stock
    g.rrect("s", 10.0, 8.4, 19.0, 12.6, 0.4)
    g.rrect("n", 19.0, 9.6, 42.0, 12.0, 0.7)     # barrel
    g.rrect("b", 42.0, 9.4, 44.4, 12.2, 0.5)
    g.rrect("d", 19.0, 7.4, 38.0, 9.4, 0.5)      # tube magazine under the barrel
    g.rrect("W", 22.0, 6.0, 33.0, 8.4, 0.6)      # pump
    g.stripe("w", 22.6, 6.2, 32.4, 8.2, 1.8, 0.7)
    g.ring("k", 13.6, 6.6, 2.0, 1.7, 0.6)
    g.rrect("x", 12.9, 5.9, 13.8, 7.2, 0.3)
    g.rect("b", 12.0, 11.6, 15.6, 12.6)          # ejection port
    g.rect("e", 40.0, 12.0, 40.8, 12.8)          # bead sight


def barricade(g):
    """A concrete panel between two steel posts - the thing a player puts down to hide behind.

    Two blocks by two in the drawing; the display entity stretches it sideways to the two and a half
    that the collision behind it actually covers.
    """
    g.rect("q", 0, 0, 32, 5)                       # kerb
    g.rrect("Q", 2, 5, 30, 26, 1.2)                # panel
    g.rect("q", 0, 26, 32, 30)                     # capping
    g.rect("G", 0, 0, 3, 32)                       # posts
    g.rect("G", 29, 0, 32, 32)
    g.stripe("E", 4, 13, 28, 14, 5.0, 1.6)         # rust
    g.rect("E", 3, 20, 29, 21)


# Held props: medicine, built exactly like a gun and shown like one. These were flat sixteen pixel
# sprites, which next to a two hundred box rifle looked like placeholders - because that is what they
# were. They are the same drawing pipeline now.
HELD = {}


def held(name, length, height, blocks, build):
    sketch = Sketch(length, height)
    build(sketch)
    HELD[name] = (sketch, blocks)


def roll(band):
    """A roll of gauze, and nothing else on it.

    A real one is about eleven centimetres long and four across - a stubby cylinder, not the thin disc
    the icon for one usually is - so that is what this is now. Everything printed on it has gone: no
    wrap lines, no groove between layers, no hole down the middle. One white capsule, one paper band
    round the middle carrying the tier colour, one loose end. The cross-section is flat rather than
    round, because a curved one is quantised into a handful of widths and those steps are exactly the
    roughness this was being asked to lose.

    It is drawn at twice the size it is shown at, which is the only way the edge of a curve gets
    smoother: the steps are the grid, so the answer is more grid per object, not a different curve.
    """
    def build(g):
        g.rrect("W1", 1.5, 2.0, 24.5, 12.0, 4.6)          # the roll
        g.recolour(band, 10.0, 1.5, 16.0, 12.5)           # the paper band round the middle
        g.rrect("W3", 23.0, 5.6, 29.0, 8.4, 1.2)          # the end, pulled loose
    return build


def cross(g, cx, cy, arm, thick, material="N3"):
    """A plus sign, drawn as two overlapping bars."""
    g.rect(material, cx - thick, cy - arm, cx + thick, cy + arm)
    g.rect(material, cx - arm, cy - thick, cx + arm, cy + thick)


def dressing(band):
    """A boxed dressing: a square box with one bevelled edge all the way round.

    The shape is a rectangle and stays a rectangle - a rounded one turns its corner over several steps
    and at this size that reads as a blob. What takes the hardness off is a single forty-five degree
    cut at each corner, which is the one bevel a moulded box actually has.

    The top and bottom are painted as the end of a roll rather than as a lid, so the thing reads as
    wound cloth from above and as the edges of the wraps from the side.
    """
    def build(g):
        # Three of them, because one box on its own is a box. Two lying down with the third stood up
        # against them gives the item a silhouette instead of an outline, and it is how dressings
        # actually sit in a kit bag.
        # One box. Not three - a stack needed air gaps to keep the mesher from welding it into a lump,
        # and every extra piece is more elements in the model and more patches in the texture atlas for
        # something nobody is going to study in a hotbar slot.
        g.rect("N1", 0.0, 0.0, 12.0, 20.0)
        g.chamfer(0.0, 0.0, 12.0, 20.0, 1.0)
        g.recolour(band, 0.0, 7.0, 12.0, 13.0)
        cross(g, 6.0, 10.0, 2.6, 0.9)
    return build


def blister(g):
    """Painkillers: a card and ten pills. No perforation, no print, no lines."""
    g.rrect("B1", 0.8, 1.4, 27.2, 14.6, 2.2)
    for index in range(5):
        g.ellipse("B2", 4.0 + index * 5.0, 4.6, 1.7, 2.0)
        g.ellipse("B2", 4.0 + index * 5.0, 11.4, 1.7, 2.0)


def autopen(g):
    """The full cure: a sealed auto-injector, not a syringe.

    Twenty per cent and a hundred per cent were the same syringe with a different coloured ring, which
    at the size these are seen is no difference at all. This one is a pen - a fat tube with a screw
    cap, a rubber grip band and no plunger - in a deep blue nobody else on the shelf is wearing.
    """
    g.rrect("A1", 2.6, 1.2, 15.0, 6.8, 1.4)
    g.rrect("A2", 14.4, 0.8, 18.4, 7.2, 1.6)               # the cap
    g.rect("A3", 5.0, 1.0, 8.4, 7.0)                       # grip band
    g.rect("A4", 9.6, 1.2, 10.8, 6.8)                      # a stripe down it
    g.rrect("A1", 0.8, 2.6, 2.8, 5.4, 0.7)                 # the blunt end
    g.rect("A3", 11.6, 3.2, 13.4, 4.8)                     # a window showing it is still loaded


def pouch(g):
    """The first aid kit: a soft olive pouch with a zip and a white cross.

    Deliberately nothing like the medkit. The two were the same white box with the same red cross at
    two sizes, which told the player nothing at a glance - and a glance is all either of them gets.
    One is now cloth, olive, soft-cornered, zipped, with a strap; the other is a hard white case with
    chrome latches and a carrying handle. Different material, different colour, different silhouette.
    """
    g.rrect("K4", 0.6, 0.4, 11.4, 9.4, 2.0)
    g.rect("K6", 0.9, 6.6, 11.1, 7.2)                  # the zip across the top
    g.rect("K4", 4.6, 9.2, 7.4, 10.8)                  # a strap loop
    g.erase(5.3, 9.6, 6.7, 10.4)
    g.rect("K5", 4.9, 1.8, 7.1, 6.0)                   # the cross
    g.rect("K5", 3.2, 3.2, 8.8, 4.6)


def case(shell, cross, wide, tall, latch):
    """The medkit: a hard case, chrome latches, a handle with a hole through it.

    Red with a white cross rather than the other way round. The colour is doing a job here - this is
    the one item on the server that puts a player back to full, and it should be the one that catches
    the eye in a pile of loot from across a room.
    """
    def build(g):
        g.rrect("K3", wide / 2 - 2.2, tall - 0.4, wide / 2 + 2.2, tall + 2.8, 0.7)
        g.erase(wide / 2 - 1.4, tall + 0.5, wide / 2 + 1.4, tall + 2.1)
        g.rrect(shell, 0, 0, wide, tall, 1.2)
        g.rect("K3", 0, tall * 0.60, wide, tall * 0.60 + 0.5)
        g.rect(cross, wide / 2 - 1.3, tall * 0.14, wide / 2 + 1.3, tall * 0.86)
        g.rect(cross, wide / 2 - 3.6, tall * 0.38, wide / 2 + 3.6, tall * 0.62)
        if latch:
            g.rrect("K7", wide * 0.10, tall * 0.50, wide * 0.24, tall * 0.72, 0.3)
            g.rrect("K7", wide * 0.76, tall * 0.50, wide * 0.90, tall * 0.72, 0.3)
    return build


def injector(fluid, collar):
    """A syringe: thumb rest, plunger, barrel, hub, and a needle that comes to a point.

    The needle was a bar of even thickness, which is a nail. It steps down twice and ends on a single
    cell, so it reads as sharp; and there is now a disc on the back of the plunger to push, which is
    the part of a syringe everybody's eye looks for first.
    """
    def build(g):
        g.rrect("Y4", 0.0, 1.5, 1.7, 6.5, 0.6)          # thumb rest, the disc you press
        g.rect("Y4", 1.7, 3.4, 5.2, 4.6)                # plunger rod
        g.rrect("Y4", 4.8, 0.5, 6.2, 7.5, 0.5)          # finger flange
        g.rrect("Y1", 6.2, 1.7, 15.4, 6.3, 0.9)         # barrel
        g.recolour(fluid, 7.4, 1.7, 14.2, 6.3)
        g.recolour("Y4", 6.4, 1.7, 7.4, 6.3)            # the plunger head inside it
        g.stripe("Y4", 8.4, 5.4, 13.8, 5.7, 1.5, 0.28)  # graduations
        if collar:
            g.rect(collar, 14.2, 1.7, 15.2, 6.3)
        g.rrect("Y4", 15.4, 2.9, 16.8, 5.1, 0.4)        # hub
        g.rect("Y4", 16.8, 3.5, 18.4, 4.5)              # needle, stepping down to a point
        g.rect("Y4", 18.4, 3.7, 19.3, 4.3)
        g.rect("Y4", 19.3, 3.85, 20.0, 4.15)
    return build


held("bandage_green", 12, 20, 0.20, dressing("D1"))
held("bandage_blue", 12, 20, 0.20, dressing("D2"))
held("bandage_red", 12, 20, 0.20, dressing("D3"))
held("firstaid", 12, 11, 0.38, pouch)
held("medkit", 16, 15, 0.50, case("K8", "K9", 16, 11, True))
held("painkillers", 28, 16, 0.34, blister)
held("epinephrine", 20, 8, 0.40, injector("Y3", "Y5"))
held("antidote", 20, 8, 0.38, injector("Y2", None))
held("antidote_full", 19, 8, 0.40, autopen)


# Props are built the same way as the weapons and differ only in how they are displayed: a barricade is
# never held, so it gets one transform, for the display entity that carries it.
PROPS = {}
PROPS["barricade"] = Sketch(32, 32)
barricade(PROPS["barricade"])

design("pistol", 26, 16, 0.46, pistol)
design("magnum", 26, 16, 0.48, magnum)
design("deagle", 30, 17, 0.56, deagle)
design("smg", 36, 17, 0.85, smg)
design("rifle", 47, 18, 1.15, rifle)
design("ak", 47, 17, 1.15, ak)
design("sniper", 46, 21, 1.25, sniper)
design("shotgun", 46, 15, 1.15, shotgun)


# ---------------------------------------------------------------- the texture
class Atlas:
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


def finish(atlas, spot, width, height, base, kind, face, rng, buried, outer,
           top_open=True, bottom_open=True):
    """Paints one face: the light it catches, the shadow where it meets, and the marks on it.

    Three things happen to the colour and the second is the one that was missing. The face is lit by
    which way it points; then it is darkened by how much of it is pressed against other geometry, which
    is what puts contact shadows into crevices and lets the eye read which part is in front of which;
    then the tool marks, and finally an edge - a pixel of light along a border that is genuinely the
    outline of the object rather than a seam between two boxes of the same material.
    """
    lit = shade(base, LIGHT[face] * (1.0 - 0.42 * buried))
    flat = face in ("up", "down")
    for row in range(height):
        for column in range(width):
            colour = lit
            if kind == "brushed":
                colour = shade(colour, 1.0 + 0.022 * math.sin(row * 2.3)
                               + rng.uniform(-0.012, 0.012))
            elif kind == "grit":
                colour = shade(colour, 1.0 + rng.uniform(-0.09, 0.09))
            elif kind == "serrate":
                colour = shade(colour, (0.74, 1.12, 1.0)[column % 3])
            elif kind == "checker":
                colour = shade(colour, 1.12 if ((column // 2) + (row // 2)) % 2 == 0 else 0.88)
            elif kind == "grain":
                streak = math.sin(row * 1.9 + math.sin(row * 0.7) * 2.0)
                colour = shade(colour, 1.0 + 0.10 * streak + rng.uniform(-0.03, 0.03))
            elif kind == "roll":
                # The end of a roll of cloth on the top and bottom, the edges of the wraps on the
                # sides. The only finish that cares which face it is painting, and the reason the top
                # of a boxed dressing reads as wound gauze rather than as a lid.
                if flat:
                    ring = min(column, row, width - 1 - column, height - 1 - row)
                    colour = shade(colour, 1.0 if (ring // 2) % 2 == 0 else 0.91)
                # The sides are left plain. They carried a fine horizontal stripe, which on a box made
                # of stacked pieces landed on top of the seam shading and read as corrugation.
            elif kind == "glass":
                across = (column / max(1.0, width - 1.0)) - 0.35
                down = (row / max(1.0, height - 1.0)) - 0.3
                colour = shade(colour, 1.30 - 0.85 * min(1.0, across * across + down * down) ** 0.5)

            # The edge light, and the rule that took three goes to get right: a face's top row is only
            # an edge if there is nothing sitting on top of the box. Stacked boxes share a border, and
            # lighting both sides of it draws a bright line across the middle of a flat surface at
            # every seam - which is exactly the striping that kept appearing on things built out of
            # several pieces.
            if outer and width > 2 and height > 2:
                if row == 0 and top_open:
                    colour = shade(colour, 1.28)
                elif row == height - 1 and bottom_open:
                    colour = shade(colour, 0.78)
                elif column == 0 or column == width - 1:
                    colour = shade(colour, 1.08)
            elif not flat and height > 2:
                if row == 0 and top_open:
                    colour = shade(colour, 1.10)
                elif row == height - 1 and bottom_open:
                    colour = shade(colour, 0.88)
            atlas.pixels[spot[0] + column, spot[1] + row] = colour + (255,)


# ---------------------------------------------------------------- the model
def build(name, sketch):
    for scale in (8, 7, 6, 5, 4, 3):
        atlas = Atlas(scale)
        rng = random.Random(name)
        try:
            out = []
            offset = max(FLOOR + 1, min(8.0 - sketch.length / 2.0, LIMIT - sketch.length - 1))
            rise = max(0.0, 8.0 - sketch.height / 2.0)
            for box in solidify(sketch, MATERIALS):
                colour, kind, ignored, also = MATERIALS[box["material"]]
                x0, y0, z0 = box["from"]
                x1, y1, z1 = box["to"]
                faces = {}
                for face in ("north", "south", "east", "west", "up", "down"):
                    buried = box["buried"][face]
                    # A face lying flat against something else is never seen. Leaving it out costs the
                    # model nothing and hands its share of the texture to the faces that do show - which
                    # is most of why the texture can now afford eight pixels to the unit instead of five.
                    if buried >= 0.999:
                        continue
                    if face in ("north", "south"):
                        units = (x1 - x0, y1 - y0)
                    elif face in ("east", "west"):
                        units = (z1 - z0, y1 - y0)
                    else:
                        units = (x1 - x0, z1 - z0)
                    wide = max(1, int(round(units[0] * scale)))
                    high = max(1, int(round(units[1] * scale)))
                    spot = atlas.place(wide, high)
                    finish(atlas, spot, wide, high, colour, kind, face, rng,
                           buried, buried < 0.05,
                           box["buried"]["up"] < 0.5, box["buried"]["down"] < 0.5)
                    faces[face] = {"uv": atlas.uv(spot, wide, high), "texture": "#t"}
                if not faces:
                    continue
                out.append({
                    "from": [round(offset + x0, 3), round(rise + y0, 3), round(z0, 3)],
                    "to": [round(offset + x1, 3), round(rise + y1, 3), round(z1, 3)],
                    "faces": faces})
            return atlas.image, out, scale
        except MemoryError:
            continue
    raise MemoryError(name + " does not fit its texture")


def display(length, blocks, tilt=0.0, drop=0.0):
    """Where the gun sits in the hand, which way it points, and how big it is.

    The direction was wrong for a long time and is worth writing down. Minecraft turns a display
    transform about +Y the right-handed way, so a model laid along +x - which every gun here is - has
    its nose sent to +z by `rotation.y = -90` and to -z by `+90`. In the hand, -z is away from the
    player. The transform was copied from `item/handheld`, which uses -90 and is correct for a sword
    because a sword's texture runs diagonally and the roll dominates; applied to something built
    straight along one axis it simply turns the weapon round. Every gun was aimed at its owner.

    So: +90 in the right hand, -90 in the left, matching the mirrored convention vanilla uses. The
    reload tilt is negated with it, because the same tilt that dipped a backwards muzzle raises a
    forwards one.

    The scale comes from how long the weapon should actually appear - a pistol under half a block, a
    rifle over one - rather than from one constant applied to all of them.
    """
    held = round(blocks * 16.0 / length, 4)
    turn = round(-tilt, 2) or 0
    return {
        "thirdperson_righthand": {
            "rotation": [turn, 90, 0], "translation": [0, 3.0 - drop, 0], "scale": [held] * 3},
        "thirdperson_lefthand": {
            "rotation": [turn, -90, 0], "translation": [0, 3.0 - drop, 0], "scale": [held] * 3},
        "firstperson_righthand": {
            "rotation": [turn, 90, 0], "translation": [0.8, 2.2 - drop, 1.2],
            "scale": [round(held * 1.15, 4)] * 3},
        "firstperson_lefthand": {
            "rotation": [turn, -90, 0], "translation": [0.8, 2.2 - drop, 1.2],
            "scale": [round(held * 1.15, 4)] * 3},
        # In a slot the muzzle should point right and away, which is +45 rather than the 135 that had
        # it pointing left and away - the same error as the hand, seen from a different angle.
        "gui": {"rotation": [30, 45, 0], "translation": [0, 0, 0],
                "scale": [round(13.5 / length, 4)] * 3},
        "ground": {"rotation": [0, 0, 0], "translation": [0, 2, 0],
                   "scale": [round(8.0 / length, 4)] * 3},
        # In an item frame a weapon is shown broadside, which needs no turn at all.
        "fixed": {"rotation": [0, 0, 0], "translation": [0, 0, 0],
                  "scale": [round(15.0 / length, 4)] * 3},
    }


# The reload tips the muzzle down and brings it back. Same boxes, different hand - which is why the
# three frames are parents of one shape file rather than three copies of several hundred elements.
FRAMES = {"": (0.0, 0.0), "_r1": (30.0, 1.5), "_r2": (58.0, 3.0)}


def profile_sheet():
    cell = 3
    widest = max(sketch.wide for sketch, ignored in GUNS.values())
    tall = sum(sketch.tall + 6 for sketch, ignored in GUNS.values())
    image = Image.new("RGBA", (widest * cell, tall * cell), (26, 28, 34, 255))
    pixels = image.load()
    top = 0
    for name, (sketch, ignored) in GUNS.items():
        for y in range(sketch.tall):
            for x in range(sketch.wide):
                material = sketch.cells[y][x]
                if material is None:
                    continue
                colour = MATERIALS[material][0] + (255,)
                for dy in range(cell):
                    for dx in range(cell):
                        pixels[x * cell + dx, (top + y) * cell + dy] = colour
        top += sketch.tall + 6
    path = os.path.join(HERE, "gun_profiles.png")
    image.save(path)
    print("wrote", path)


def main():
    if "--profile" in sys.argv:
        profile_sheet()
        return

    for folder in (ITEMS, MODELS, TEXTURES):
        os.makedirs(folder, exist_ok=True)

    for name, sketch in PROPS.items():
        image, built, scale = build(name, sketch)
        image.save(os.path.join(TEXTURES, "gun_" + name + ".png"))
        flat = {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]}
        model = {
            "textures": {"t": "asuracraft:item/gun_" + name,
                         "particle": "asuracraft:item/gun_" + name},
            "elements": built,
            "gui_light": "front",
            "display": {"fixed": flat, "ground": flat, "head": flat,
                        "gui": {"rotation": [20, -30, 0], "translation": [0, 0, 0],
                                "scale": [0.42, 0.42, 0.42]}},
        }
        with io.open(os.path.join(MODELS, name + ".json"), "w", encoding="utf-8") as out:
            json.dump(model, out, separators=(",", ":"))
        with io.open(os.path.join(ITEMS, name + ".json"), "w", encoding="utf-8") as out:
            json.dump({"model": {"type": "minecraft:model",
                                 "model": "asuracraft:item/" + name}}, out, indent=1)
        print("  %-8s prop -> %3d boxes" % (name, len(built)))

    for name, (sketch, blocks) in HELD.items():
        image, built, scale = build(name, sketch)
        image.save(os.path.join(TEXTURES, "gun_" + name + ".png"))
        model = {
            "textures": {"t": "asuracraft:item/gun_" + name,
                         "particle": "asuracraft:item/gun_" + name},
            "elements": built,
            "display": display(sketch.length, blocks),
            "gui_light": "front",
        }
        with io.open(os.path.join(MODELS, name + ".json"), "w", encoding="utf-8") as out:
            json.dump(model, out, separators=(",", ":"))
        with io.open(os.path.join(ITEMS, name + ".json"), "w", encoding="utf-8") as out:
            json.dump({"model": {"type": "minecraft:model",
                                 "model": "asuracraft:item/" + name}}, out, indent=1)
        print("  %-14s held -> %3d boxes" % (name, len(built)))

    for name, (sketch, blocks) in GUNS.items():
        image, built, scale = build(name, sketch)
        image.save(os.path.join(TEXTURES, "gun_" + name + ".png"))

        shape = {
            "textures": {"t": "asuracraft:item/gun_" + name,
                         "particle": "asuracraft:item/gun_" + name},
            "elements": built,
            "gui_light": "front",
        }
        with io.open(os.path.join(MODELS, name + "_shape.json"), "w", encoding="utf-8") as out:
            json.dump(shape, out, separators=(",", ":"))

        for suffix, (tilt, drop) in FRAMES.items():
            with io.open(os.path.join(MODELS, name + suffix + ".json"), "w",
                         encoding="utf-8") as out:
                json.dump({"parent": "asuracraft:item/" + name + "_shape",
                           "display": display(sketch.length, blocks, tilt, drop)},
                          out, ensure_ascii=False, indent=1)
            with io.open(os.path.join(ITEMS, name + suffix + ".json"), "w",
                         encoding="utf-8") as out:
                json.dump({"model": {"type": "minecraft:model",
                                     "model": "asuracraft:item/" + name + suffix}},
                          out, ensure_ascii=False, indent=1)

        size = os.path.getsize(os.path.join(MODELS, name + "_shape.json"))
        print("  %-8s %2du long -> %4d boxes, %5.1f KB, %dpx/unit, %.2f blocks in hand"
              % (name, sketch.length, len(built), size / 1024.0, scale, blocks))

    print("guns   ", len(GUNS), "at", RES, "cells per unit")


if __name__ == "__main__":
    main()
