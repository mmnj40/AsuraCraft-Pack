# -*- coding: utf-8 -*-
"""Draws the guns, and tells the game which picture belongs to which item.

Pixel art rather than a modelled weapon, and on purpose. A gun held in Minecraft is seen at arm's
length for a fraction of a second between recoils; a hand-built three-dimensional model costs days of
work to be recognised in the same tenth of a second that a clear silhouette manages. What matters is
that a sniper cannot be mistaken for an SMG at a glance, which is a matter of outline, not of geometry.

Named item models rather than numbered variants: the item asks for "asuracraft:rifle" by name, so a gun
added next month cannot shuffle the numbering of the guns already in players' hands.
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

# A gun is drawn on a sixteen pixel grid, side on, muzzle to the right - the direction Minecraft holds
# an item in the first person. Three tones each: body, a darker edge, and one highlight so the shape
# reads against both a bright sky and a dark building.
STEEL = (58, 62, 70, 255)
STEEL_DARK = (32, 34, 40, 255)
STEEL_LIGHT = (96, 102, 112, 255)
WOOD = (104, 72, 42, 255)
WOOD_DARK = (68, 46, 26, 255)
BLACK = (22, 22, 26, 255)
GLASS = (140, 200, 230, 255)

# Each gun is a list of (x, y, width, height, colour) rectangles on the 16x16 grid.
GUNS = {
    "pistol": [
        (3, 6, 9, 3, STEEL),          # slide
        (3, 6, 9, 1, STEEL_LIGHT),    # highlight along the top
        (3, 9, 3, 1, STEEL_DARK),     # frame under the slide
        (4, 9, 2, 4, WOOD),           # grip
        (4, 9, 1, 4, WOOD_DARK),
        (6, 9, 2, 2, STEEL_DARK),     # trigger guard
        (11, 7, 1, 1, BLACK),         # muzzle
    ],
    "smg": [
        (2, 6, 11, 3, STEEL),
        (2, 6, 11, 1, STEEL_LIGHT),
        (1, 6, 1, 2, STEEL_DARK),     # stock stub
        (5, 9, 2, 5, STEEL_DARK),     # magazine, long and straight
        (3, 9, 2, 3, WOOD),           # grip
        (7, 9, 2, 2, STEEL_DARK),
        (12, 7, 2, 1, BLACK),         # barrel
        (13, 5, 1, 2, STEEL_DARK),    # front sight
    ],
    "rifle": [
        (1, 7, 13, 3, STEEL),
        (1, 7, 13, 1, STEEL_LIGHT),
        (0, 7, 2, 3, WOOD),           # shoulder stock
        (0, 7, 1, 3, WOOD_DARK),
        (6, 10, 2, 4, STEEL_DARK),    # curved magazine
        (7, 12, 2, 2, STEEL_DARK),
        (4, 10, 2, 3, WOOD),          # grip
        (13, 8, 3, 1, BLACK),         # long barrel
        (11, 5, 1, 2, STEEL_DARK),    # rear sight
        (3, 5, 4, 2, STEEL_DARK),     # top rail
    ],
    "sniper": [
        (1, 8, 14, 2, STEEL),
        (1, 8, 14, 1, STEEL_LIGHT),
        (0, 7, 2, 4, WOOD),           # heavy stock
        (0, 7, 1, 4, WOOD_DARK),
        (4, 4, 7, 2, STEEL_DARK),     # scope body
        (4, 4, 7, 1, STEEL_LIGHT),
        (10, 4, 1, 2, GLASS),         # lens
        (5, 6, 1, 2, STEEL_DARK),     # scope mounts
        (9, 6, 1, 2, STEEL_DARK),
        (4, 10, 2, 3, WOOD),          # grip
        (14, 8, 2, 1, BLACK),         # muzzle brake
        (11, 10, 3, 1, STEEL_DARK),   # bipod stub
    ],
    "shotgun": [
        (1, 7, 13, 2, STEEL),
        (1, 7, 13, 1, STEEL_LIGHT),
        (1, 9, 10, 2, WOOD),          # pump under the barrel
        (1, 9, 10, 1, WOOD_DARK),
        (0, 6, 2, 4, WOOD),           # stock
        (5, 11, 3, 2, STEEL_DARK),    # trigger group
        (13, 7, 3, 2, BLACK),         # wide bore
    ],
}


def draw(shapes):
    """One gun, on a transparent sixteen by sixteen square."""
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

        # The model: a flat sprite, held the way a tool is held so it points away from the player
        # rather than lying across their chest.
        model = {
            "parent": "minecraft:item/handheld",
            "textures": {"layer0": "asuracraft:item/" + name},
            "display": {
                "thirdperson_righthand": {
                    "rotation": [0, -90, 25],
                    "translation": [0, 4, 2],
                    "scale": [0.85, 0.85, 0.85],
                },
                "firstperson_righthand": {
                    "rotation": [0, -90, 25],
                    "translation": [1.13, 3.2, 1.13],
                    "scale": [0.68, 0.68, 0.68],
                },
                "gui": {
                    "rotation": [0, 0, 0],
                    "translation": [0, 0, 0],
                    "scale": [1.0, 1.0, 1.0],
                },
            },
        }
        with io.open(os.path.join(MODELS, name + ".json"), "w", encoding="utf-8") as out:
            json.dump(model, out, ensure_ascii=False, indent=2)

        # The item model definition: what the server names when it sets the item_model component.
        # Naming beats numbering - a new gun cannot renumber the ones already made.
        definition = {"model": {"type": "minecraft:model", "model": "asuracraft:item/" + name}}
        with io.open(os.path.join(ITEMS, name + ".json"), "w", encoding="utf-8") as out:
            json.dump(definition, out, ensure_ascii=False, indent=2)

    print("guns   ", len(GUNS), "->", ", ".join(GUNS))


if __name__ == "__main__":
    main()
