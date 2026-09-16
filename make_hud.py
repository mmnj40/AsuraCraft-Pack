# -*- coding: utf-8 -*-
"""The heads-up display: bars instead of hearts, and a hotbar that looks like it has been used.

Minecraft draws its status rows out of one small sprite repeated ten times. Nothing says that sprite
has to be a heart: draw a slab that meets its neighbours at the edges and ten of them in a row read as
a single bar, which is what every survival game made since 1998 puts on the screen. The only rule is
that each sprite must carry its own left and right edge, because at eight pixels of spacing and nine
pixels of width the last column of one lands on the first column of the next.

Everything here is drawn rather than painted over a copy of the vanilla file - there is no vanilla
asset in this repository to start from, and a bar is a rectangle, which is the one thing that can be
drawn from nothing without looking like it was.
"""
import io
import json
import os
import random

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
VANILLA = os.path.join(PACK, "assets", "minecraft")
HUD = os.path.join(VANILLA, "textures", "gui", "sprites", "hud")
MISC = os.path.join(VANILLA, "textures", "misc")
EFFECT = os.path.join(VANILLA, "textures", "mob_effect")

# The palette. Survival, not science fiction: everything is a dirty version of itself, and nothing is
# the pure red or pure green that a default health bar reaches for.
INK = (18, 19, 23, 255)          # the outline everything sits inside
HOLLOW = (38, 36, 40, 255)       # an empty segment
BLOOD = (166, 46, 40, 255)       # health
BLOOD_LOW = (118, 30, 28, 255)   # its shadow
BREAD = (150, 116, 62, 255)      # food
BREAD_LOW = (104, 78, 40, 255)
STEEL = (146, 152, 162, 255)     # armour
STEEL_LOW = (98, 104, 114, 255)
AMBER = (222, 164, 44, 255)      # stamina, on the experience bar
AMBER_LOW = (158, 112, 26, 255)
PLATE = (44, 44, 50, 255)        # the hotbar itself
PLATE_LIT = (74, 74, 82, 255)
PLATE_DARK = (26, 26, 31, 255)


def blank(width, height):
    return Image.new("RGBA", (width, height), (0, 0, 0, 0))


def segment(fill, shadow, part=1.0, empty=False):
    """One cell of a status row, nine by nine, drawn as a slice of bar.

    The bar is five pixels tall and sits on the middle of the cell, which is where the middle of a
    heart was, so nothing else on the screen has to move. A half segment fills the left half only -
    the game asks for one of these whenever a player is on an odd number, and filling the left is what
    makes a row of them drain from the right like a bar rather than blink like a row of icons.
    """
    cell = blank(9, 9)
    pen = cell.load()
    top, bottom = 2, 6
    for x in range(9):
        for y in range(top, bottom + 1):
            edge = y == top or y == bottom
            if empty:
                pen[x, y] = INK if edge else HOLLOW
                continue
            lit = x < round(9 * part)
            if not lit:
                pen[x, y] = INK if edge else HOLLOW
            elif edge:
                pen[x, y] = INK
            else:
                pen[x, y] = shadow if y == bottom - 1 else fill
    # A hairline down each side so ten of them in a row still read as one object rather than ten.
    for y in range(top, bottom + 1):
        pen[0, y] = INK
        pen[8, y] = INK
    return cell


def hotbar():
    """The hotbar: a strip of scratched steel with the slots stamped into it.

    A hundred and eighty two by twenty two, which is nine slots of twenty plus a pixel of frame either
    side. The wear is deterministic - seeded - because a resource pack that looked different every time
    it was built would be unreviewable.
    """
    strip = Image.new("RGBA", (182, 22), PLATE)
    pen = strip.load()
    rng = random.Random(7)

    for x in range(182):
        for y in range(22):
            if y in (0, 21) or x in (0, 181):
                pen[x, y] = INK
            elif y in (1, 20):
                pen[x, y] = PLATE_DARK
            elif y == 2:
                pen[x, y] = PLATE_LIT              # a lit edge along the top, like a bent lip
    # Slot divisions, stamped rather than drawn: a dark line with a light one beside it.
    for slot in range(1, 9):
        x = 1 + slot * 20
        for y in range(3, 20):
            pen[x, y] = PLATE_DARK
            pen[x + 1, y] = (56, 56, 63, 255)
    # Scratches and pitting. Sparse - the point is that the metal is not new, not that it is ruined.
    for _ in range(90):
        x = rng.randrange(3, 179)
        y = rng.randrange(4, 19)
        pen[x, y] = (58, 58, 66, 255) if rng.random() < 0.6 else (34, 34, 39, 255)
    for _ in range(14):
        x = rng.randrange(6, 172)
        y = rng.randrange(5, 18)
        for step in range(rng.randrange(3, 9)):
            if x + step < 179:
                pen[x + step, y] = (64, 64, 72, 200)
    return strip


def selection():
    """The box around the chosen slot: a bright steel frame, two pixels thick."""
    frame = blank(24, 24)
    pen = frame.load()
    for x in range(24):
        for y in range(24):
            near = x < 2 or y < 2 or x > 21 or y > 21
            outer = x == 0 or y == 0 or x == 23 or y == 23
            if outer:
                pen[x, y] = (14, 15, 18, 255)
            elif near:
                pen[x, y] = (214, 206, 190, 255) if (x + y) % 7 else (168, 160, 146, 255)
    return frame


def experience(fill, shadow, empty=False):
    """The experience bar, which on this server is stamina. Amber, because green reads as magic."""
    strip = blank(182, 5)
    pen = strip.load()
    for x in range(182):
        for y in range(5):
            if y == 0 or y == 4:
                pen[x, y] = INK
            elif empty:
                pen[x, y] = HOLLOW
            else:
                pen[x, y] = shadow if y == 3 else fill
    return strip


def effect_icon():
    """The icon for a boost, eighteen by eighteen, shown in the corner while a drug is working.

    It is put on the luck effect, which is the one thing in the game that changes nothing a player can
    feel - so the icon is carrying the information and the effect itself is only the peg it hangs on.
    """
    icon = blank(18, 18)
    pen = icon.load()
    # A syringe on the diagonal: barrel, plunger, needle.
    for step in range(11):
        x = 3 + step
        y = 13 - step
        for thick in (-1, 0, 1):
            if 0 <= x + thick < 18 and 0 <= y < 18:
                pen[x + thick, y] = (226, 232, 240, 255) if thick == 0 else (150, 158, 170, 255)
    for step in range(5):
        x = 7 + step
        y = 9 - step
        pen[x, y] = (92, 196, 120, 255)
    for step in range(3):
        pen[14 + step, 2 - step if 2 - step >= 0 else 0] = (214, 220, 228, 255)
    for step in range(4):
        pen[2 + step, 15] = (120, 128, 140, 255)
        pen[2, 12 + step] = (120, 128, 140, 255)
    return icon


def flash():
    """The screen while a flashbang is going off.

    Minecraft draws one full-screen overlay that a server can trigger without a mod: the blur a carved
    pumpkin puts over the view. Replacing that texture with white glare and putting a pumpkin on
    somebody's head for a second and a half is a flashbang - the client scales this to the whole
    window, so it only has to be bright in the middle and fall away at the corners.
    """
    size = 256
    glare = blank(size, size)
    pen = glare.load()
    middle = size / 2.0
    for x in range(size):
        for y in range(size):
            away = ((x - middle) ** 2 + (y - middle) ** 2) ** 0.5 / middle
            near = max(0.0, 1.0 - away * 0.78)
            alpha = int(255 * (near ** 0.65))
            pen[x, y] = (255, 253, 246, max(0, min(255, alpha)))
    return glare


def main():
    for folder in (HUD, os.path.join(HUD, "heart"), MISC, EFFECT):
        os.makedirs(folder, exist_ok=True)

    # Health. Every state the game can ask for gets the same slab, because a bar that changed shape
    # when a player was poisoned would be a bar nobody could read at a glance.
    full = segment(BLOOD, BLOOD_LOW)
    half = segment(BLOOD, BLOOD_LOW, 0.5)
    hollow = segment(BLOOD, BLOOD_LOW, 0, True)
    hearts = {
        "full": full, "full_blinking": segment((208, 74, 66, 255), BLOOD),
        "half": half, "half_blinking": segment((208, 74, 66, 255), BLOOD, 0.5),
        "container": hollow, "container_blinking": segment(BLOOD, BLOOD_LOW, 0, True),
        "poisoned_full": segment((136, 158, 52, 255), (92, 108, 34, 255)),
        "poisoned_half": segment((136, 158, 52, 255), (92, 108, 34, 255), 0.5),
        "withered_full": segment((78, 78, 86, 255), (48, 48, 54, 255)),
        "withered_half": segment((78, 78, 86, 255), (48, 48, 54, 255), 0.5),
        "absorbing_full": segment((214, 178, 62, 255), (150, 122, 38, 255)),
        "absorbing_half": segment((214, 178, 62, 255), (150, 122, 38, 255), 0.5),
        "frozen_full": segment((104, 168, 214, 255), (64, 110, 150, 255)),
        "frozen_half": segment((104, 168, 214, 255), (64, 110, 150, 255), 0.5),
    }
    for name, image in hearts.items():
        image.save(os.path.join(HUD, "heart", name + ".png"))

    # Food, in the same shape. Hunger on this server is a timer, and a timer belongs on a bar.
    segment(BREAD, BREAD_LOW).save(os.path.join(HUD, "food_full.png"))
    segment(BREAD, BREAD_LOW, 0.5).save(os.path.join(HUD, "food_half.png"))
    segment(BREAD, BREAD_LOW, 0, True).save(os.path.join(HUD, "food_empty.png"))
    segment((176, 146, 78, 255), BREAD).save(os.path.join(HUD, "food_full_hunger.png"))
    segment((176, 146, 78, 255), BREAD, 0.5).save(os.path.join(HUD, "food_half_hunger.png"))
    segment(BREAD, BREAD_LOW, 0, True).save(os.path.join(HUD, "food_empty_hunger.png"))

    # Armour, above the health, as a thinner strip of the same idea.
    segment(STEEL, STEEL_LOW).save(os.path.join(HUD, "armor_full.png"))
    segment(STEEL, STEEL_LOW, 0.5).save(os.path.join(HUD, "armor_half.png"))
    segment(STEEL, STEEL_LOW, 0, True).save(os.path.join(HUD, "armor_empty.png"))

    experience(AMBER, AMBER_LOW).save(os.path.join(HUD, "experience_bar_progress.png"))
    experience(AMBER, AMBER_LOW, True).save(os.path.join(HUD, "experience_bar_background.png"))

    hotbar().save(os.path.join(HUD, "hotbar.png"))
    selection().save(os.path.join(HUD, "hotbar_selection.png"))

    effect_icon().save(os.path.join(EFFECT, "luck.png"))
    flash().save(os.path.join(MISC, "pumpkin_blur.png"))

    print("hud     hearts+food+armour as bars, amber stamina, worn hotbar, flash overlay")


if __name__ == "__main__":
    main()
