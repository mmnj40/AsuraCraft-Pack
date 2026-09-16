# -*- coding: utf-8 -*-
"""What the gear looks like on a player, rather than in a box.

Minecraft draws worn armour from one texture stretched over the player's own shape, in the same layout
as a skin: the head is a cube of six faces in the top-left corner, the body and one arm below it. So a
helmet is six small rectangles painted in the right places, and a vest is the body block plus an arm
block - there is no model to make, only a skin for the armour.

Since 1.21.2 the mapping is explicit: an item says which "equipment asset" it wears, and that asset
names the textures for each layer. That is what lets this pack put its own gear on a player without
touching leather dye or replacing iron armour for the whole server.
"""
import io
import json
import os
import random

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
ASURA = os.path.join(PACK, "assets", "asuracraft")
WORN = os.path.join(ASURA, "textures", "entity", "equipment", "humanoid")
ASSET = os.path.join(ASURA, "equipment")

# Where each face of each cube lives in the sixty-four by thirty-two sheet.
HEAD = {"top": (8, 0, 8, 8), "bottom": (16, 0, 8, 8), "right": (0, 8, 8, 8),
        "front": (8, 8, 8, 8), "left": (16, 8, 8, 8), "back": (24, 8, 8, 8)}
BODY = {"top": (20, 16, 8, 4), "bottom": (28, 16, 8, 4), "right": (16, 20, 4, 12),
        "front": (20, 20, 8, 12), "left": (28, 20, 4, 12), "back": (32, 20, 8, 12)}
ARM = {"top": (44, 16, 4, 4), "bottom": (48, 16, 4, 4), "right": (40, 20, 4, 12),
       "front": (44, 20, 4, 12), "left": (48, 20, 4, 12), "back": (52, 20, 4, 12)}


def sheet():
    return Image.new("RGBA", (64, 32), (0, 0, 0, 0))


def fill(image, box, colour):
    x, y, wide, tall = box
    pen = image.load()
    for px in range(x, x + wide):
        for py in range(y, y + tall):
            pen[px, py] = colour


def band(image, box, colour, top, height):
    """A horizontal stripe across one face, measured from the top of that face."""
    x, y, wide, tall = box
    pen = image.load()
    for px in range(x, x + wide):
        for py in range(y + top, min(y + tall, y + top + height)):
            pen[px, py] = colour


def wear(image, seed, amount=90, light=(255, 255, 255, 40), dark=(0, 0, 0, 55)):
    """Scuffs. Applied to whatever is already painted, never to empty pixels."""
    rng = random.Random(seed)
    pen = image.load()
    for _ in range(amount):
        x = rng.randrange(0, 64)
        y = rng.randrange(0, 32)
        under = pen[x, y]
        if under[3] == 0:
            continue
        over = light if rng.random() < 0.5 else dark
        mix = tuple(int(under[i] + (over[i] - under[i]) * over[3] / 255.0) for i in range(3))
        pen[x, y] = (mix[0], mix[1], mix[2], 255)


def helmet(shell, strap, visor=None, goggles=False, seed=1):
    """A hat. Every face of the head cube, plus a band where the strap or the visor sits."""
    image = sheet()
    for name, box in HEAD.items():
        fill(image, box, shell if name != "bottom" else (0, 0, 0, 0))
    # A darker rim all the way round, so the helmet has an edge rather than ending in mid air.
    for name in ("front", "left", "right", "back"):
        band(image, HEAD[name], strap, 6, 2)
    if visor is not None:
        band(image, HEAD["front"], visor, 2, 4)
        band(image, HEAD["left"], visor, 2, 2)
        band(image, HEAD["right"], visor, 2, 2)
    if goggles:
        pen = image.load()
        x, y, wide, tall = HEAD["front"]
        for px in range(x + 2, x + 6):
            for py in range(y + 1, y + 3):
                pen[px, py] = (48, 62, 44, 255)
        pen[x + 2, y + 2] = (126, 186, 116, 255)
        pen[x + 5, y + 2] = (126, 186, 116, 255)
    wear(image, seed)
    return image


def vest(body, webbing, plate=None, seed=2):
    """A plate carrier: the torso block, a shoulder on each arm, and pouches across the front."""
    image = sheet()
    for name, box in BODY.items():
        fill(image, box, body)
    for name in ("top", "front", "back", "left", "right"):
        fill(image, ARM[name], body if name != "top" else webbing)
    # Only the top third of the arm is armour; the rest is sleeve, so it is cut away.
    pen = image.load()
    for name in ("front", "back", "left", "right"):
        x, y, wide, tall = ARM[name]
        for px in range(x, x + wide):
            for py in range(y + 5, y + tall):
                pen[px, py] = (0, 0, 0, 0)
    if plate is not None:
        band(image, BODY["front"], plate, 2, 6)
        band(image, BODY["back"], plate, 2, 6)
    # Webbing: two straps down the front and a belt across the middle.
    x, y, wide, tall = BODY["front"]
    for px in (x + 1, x + 6):
        for py in range(y, y + 10):
            pen[px, py] = webbing
    band(image, BODY["front"], webbing, 8, 2)
    band(image, BODY["back"], webbing, 8, 2)
    wear(image, seed)
    return image


PIECES = {
    "cap": helmet((86, 92, 68, 255), (60, 66, 48, 255), seed=3),
    "riot": helmet((196, 198, 204, 255), (52, 54, 60, 255), visor=(40, 44, 52, 255), seed=4),
    "military": helmet((78, 92, 62, 255), (48, 56, 40, 255), seed=5),
    "nvg": helmet((70, 82, 56, 255), (44, 52, 38, 255), goggles=True, seed=6),
    "light_vest": vest((96, 100, 108, 255), (58, 60, 66, 255), seed=7),
    "military_vest": vest((84, 96, 64, 255), (52, 60, 40, 255), plate=(66, 76, 50, 255), seed=8),
    "heavy_vest": vest((58, 60, 66, 255), (36, 38, 44, 255), plate=(96, 100, 110, 255), seed=9),
}


def main():
    os.makedirs(WORN, exist_ok=True)
    os.makedirs(ASSET, exist_ok=True)
    for name, image in PIECES.items():
        image.save(os.path.join(WORN, "warz_" + name + ".png"))
        with io.open(os.path.join(ASSET, "warz_" + name + ".json"), "w", encoding="utf-8") as out:
            json.dump({"layers": {"humanoid": [
                {"texture": "asuracraft:warz_" + name}]}}, out, indent=1)
    print("armour ", len(PIECES), "worn textures + equipment assets")


if __name__ == "__main__":
    main()
