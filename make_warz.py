# -*- coding: utf-8 -*-
"""Everything the WarZ server needs from the pack that is not a gun: items, the HUD, and the sights.

Three jobs.

The items are pixel art, drawn here rather than by hand, because there are two dozen of them and they
only have to be legible at sixteen pixels in a hotbar slot - a silhouette, an outline, and one spot of
colour that says what it is. A bandage is white with a red cross, painkillers are a yellow bottle, rifle
rounds are taller and thinner than pistol rounds. Nobody will study them; everybody has to recognise
them at a glance while being chased.

The HUD is a font. Minecraft draws a bitmap glyph at a fixed width, which is the only way to get a bar
on screen that does not jump about as the number behind it changes - and the action bar is the one line
a server can write on every frame without opening a window. Thirteen glyphs per bar, one per step.

The sights are the two textures the client already draws for itself: the crosshair, which becomes the
red dot every gun without a scope aims down, and the spyglass overlay, which becomes the scope picture
for four times and eight times. Replacing those two costs nothing at runtime and is always perfectly
centred, which no message-based reticle ever is.
"""
import io
import json
import os

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
ASURA = os.path.join(PACK, "assets", "asuracraft")
VANILLA = os.path.join(PACK, "assets", "minecraft")
ITEMS = os.path.join(ASURA, "items")
MODELS = os.path.join(ASURA, "models", "item")
TEXTURES = os.path.join(ASURA, "textures", "item")
FONT_TEX = os.path.join(ASURA, "textures", "font", "warz")
FONT_DEF = os.path.join(ASURA, "font")

CLEAR = (0, 0, 0, 0)
OUTLINE = (18, 18, 22, 255)


def blank(size=16):
    return Image.new("RGBA", (size, size), CLEAR)


def shade(colour, factor):
    return tuple(min(255, max(0, int(c * factor))) for c in colour[:3]) + (colour[3],)


def slab(pen, box, colour, lit=1.22, dark=0.66):
    """A rectangle with a lit top edge, a dark bottom edge and an outline - the whole art style."""
    x0, y0, x1, y1 = box
    pen.rectangle([x0, y0, x1, y1], fill=colour, outline=OUTLINE)
    pen.line([x0 + 1, y0 + 1, x1 - 1, y0 + 1], fill=shade(colour, lit))
    pen.line([x0 + 1, y1 - 1, x1 - 1, y1 - 1], fill=shade(colour, dark))


# ---------------------------------------------------------------- the items
def bandage():
    image = blank()
    pen = ImageDraw.Draw(image)
    slab(pen, (2, 5, 13, 10), (232, 230, 224, 255))
    pen.rectangle([6, 3, 9, 12], fill=(244, 242, 238, 255), outline=OUTLINE)
    pen.rectangle([7, 6, 8, 9], fill=(196, 52, 48, 255))
    pen.rectangle([6, 7, 9, 8], fill=(196, 52, 48, 255))
    return image


def painkillers():
    image = blank()
    pen = ImageDraw.Draw(image)
    slab(pen, (4, 5, 11, 13), (226, 190, 62, 255))
    pen.rectangle([5, 2, 10, 5], fill=(238, 238, 234, 255), outline=OUTLINE)
    pen.rectangle([6, 8, 9, 10], fill=(250, 240, 190, 255))
    return image


def firstaid():
    image = blank()
    pen = ImageDraw.Draw(image)
    slab(pen, (2, 4, 13, 13), (186, 48, 44, 255))
    pen.rectangle([7, 6, 8, 11], fill=(244, 244, 240, 255))
    pen.rectangle([5, 8, 10, 9], fill=(244, 244, 240, 255))
    pen.rectangle([6, 2, 9, 4], fill=(120, 30, 28, 255), outline=OUTLINE)
    return image


def antibiotics():
    image = blank()
    pen = ImageDraw.Draw(image)
    slab(pen, (4, 5, 11, 13), (74, 170, 96, 255))
    pen.rectangle([5, 2, 10, 5], fill=(238, 238, 234, 255), outline=OUTLINE)
    pen.rectangle([6, 8, 9, 9], fill=(236, 250, 236, 255))
    return image


def energy():
    image = blank()
    pen = ImageDraw.Draw(image)
    slab(pen, (5, 3, 10, 13), (214, 148, 46, 255))
    pen.rectangle([5, 3, 10, 4], fill=(150, 152, 158, 255))
    pen.polygon([(7, 6), (9, 6), (7, 9), (9, 9), (6, 12), (7, 9), (6, 9)],
                fill=(250, 232, 140, 255))
    return image


def water():
    image = blank()
    pen = ImageDraw.Draw(image)
    slab(pen, (5, 4, 10, 13), (86, 156, 206, 255))
    pen.rectangle([6, 1, 9, 4], fill=(150, 152, 158, 255), outline=OUTLINE)
    pen.rectangle([6, 8, 9, 12], fill=(126, 196, 236, 255))
    return image


def rations():
    image = blank()
    pen = ImageDraw.Draw(image)
    slab(pen, (4, 4, 11, 13), (150, 146, 134, 255))
    pen.rectangle([4, 6, 11, 9], fill=(178, 120, 62, 255), outline=None)
    pen.line([4, 5, 11, 5], fill=(198, 196, 190, 255))
    return image


def rounds(colour, tall, wide, count):
    """A little group of cartridges. Rifle rounds are taller, shotgun shells are fatter and red."""
    image = blank()
    pen = ImageDraw.Draw(image)
    start = 8 - (count * (wide + 1)) // 2
    for index in range(count):
        x = start + index * (wide + 1)
        top = 13 - tall
        pen.rectangle([x, top + 2, x + wide - 1, 13], fill=colour, outline=OUTLINE)
        pen.rectangle([x, top, x + wide - 1, top + 2], fill=(206, 166, 76, 255), outline=OUTLINE)
        pen.line([x + 1, top + 3, x + 1, 12], fill=shade(colour, 1.35))
    return image


def gear_helmet(shell, visor=None, goggles=False):
    """A dome with a brim. Drawn row by row - an ellipse at sixteen pixels reads as a rounded box."""
    image = blank()
    pen = ImageDraw.Draw(image)
    dome = [(3, 5, 12), (4, 4, 11), (5, 3, 12), (6, 2, 13), (7, 2, 13), (8, 2, 13), (9, 2, 13)]
    for y, x0, x1 in dome:
        pen.line([x0, y, x1, y], fill=shell)
    pen.line([1, 10, 14, 10], fill=shade(shell, 0.78))       # the brim
    pen.line([1, 11, 14, 11], fill=shade(shell, 0.58))
    pen.line([5, 3, 11, 3], fill=shade(shell, 1.45))          # where the light lands
    pen.line([4, 4, 6, 4], fill=shade(shell, 1.30))
    # Outline, traced round the silhouette rather than drawn as a box.
    pen.line([4, 2, 11, 2], fill=OUTLINE)
    pen.line([3, 3, 3, 4], fill=OUTLINE)
    pen.line([12, 3, 12, 4], fill=OUTLINE)
    pen.line([1, 9, 1, 12], fill=OUTLINE)
    pen.line([14, 9, 14, 12], fill=OUTLINE)
    pen.line([1, 12, 14, 12], fill=OUTLINE)
    if visor:
        pen.rectangle([3, 7, 12, 10], fill=visor)
        pen.line([3, 7, 12, 7], fill=(206, 236, 252, 190))
    if goggles:
        pen.rectangle([3, 6, 6, 10], fill=(40, 42, 46, 255), outline=OUTLINE)
        pen.rectangle([9, 6, 12, 10], fill=(40, 42, 46, 255), outline=OUTLINE)
        pen.rectangle([4, 7, 5, 9], fill=(94, 214, 122, 255))
        pen.rectangle([10, 7, 11, 9], fill=(94, 214, 122, 255))
        pen.line([6, 8, 9, 8], fill=(28, 30, 34, 255))
    return image


def gear_vest(body, plate=None):
    """Shoulders, a torso, and a gap at the neck - the three things that say vest and not box."""
    image = blank()
    pen = ImageDraw.Draw(image)
    pen.rectangle([3, 5, 12, 14], fill=body, outline=OUTLINE)     # torso
    pen.rectangle([4, 1, 6, 5], fill=shade(body, 0.84), outline=OUTLINE)   # shoulder straps
    pen.rectangle([9, 1, 11, 5], fill=shade(body, 0.84), outline=OUTLINE)
    pen.line([4, 6, 11, 6], fill=shade(body, 1.32))               # lit top edge
    pen.line([4, 13, 11, 13], fill=shade(body, 0.66))
    pen.line([3, 9, 12, 9], fill=shade(body, 0.72))               # webbing across the chest
    pen.rectangle([2, 6, 3, 11], fill=shade(body, 0.78), outline=OUTLINE)  # side panels
    pen.rectangle([12, 6, 13, 11], fill=shade(body, 0.78), outline=OUTLINE)
    if plate:
        pen.rectangle([5, 7, 10, 12], fill=plate, outline=OUTLINE)
        pen.line([6, 8, 9, 8], fill=shade(plate, 1.45))
    else:
        pen.rectangle([5, 10, 7, 12], fill=shade(body, 1.14), outline=OUTLINE)  # a pouch
    return image


def scope(zoom):
    image = blank()
    pen = ImageDraw.Draw(image)
    body = (52, 56, 64, 255)
    pen.rectangle([2, 6, 13, 10], fill=body, outline=OUTLINE)
    pen.rectangle([1, 5, 4, 11], fill=shade(body, 0.85), outline=OUTLINE)
    pen.rectangle([11, 5, 14, 11], fill=shade(body, 0.85), outline=OUTLINE)
    pen.line([3, 7, 12, 7], fill=shade(body, 1.5))
    lens = {1: (206, 72, 66, 255), 2: (120, 196, 236, 255),
            4: (140, 208, 160, 255), 8: (236, 196, 108, 255)}[zoom]
    pen.rectangle([12, 6, 13, 10], fill=lens)
    pen.rectangle([2, 6, 3, 10], fill=shade(lens, 0.7))
    # Turret, so the bigger scopes read as bigger.
    if zoom >= 4:
        pen.rectangle([6, 3, 9, 6], fill=body, outline=OUTLINE)
    return image


def bunker_kit():
    image = blank()
    pen = ImageDraw.Draw(image)
    slab(pen, (2, 6, 13, 13), (92, 96, 104, 255))
    pen.rectangle([6, 9, 9, 13], fill=(38, 40, 46, 255), outline=OUTLINE)
    pen.polygon([(2, 6), (8, 2), (14, 6)], fill=(112, 116, 126, 255), outline=OUTLINE)
    pen.line([3, 8, 12, 8], fill=(140, 146, 156, 255))
    return image


def magazine():
    image = blank()
    pen = ImageDraw.Draw(image)
    slab(pen, (6, 3, 10, 13), (58, 62, 70, 255))
    for y in range(5, 12, 2):
        pen.line([6, y, 10, y], fill=(40, 43, 49, 255))
    pen.rectangle([6, 2, 10, 3], fill=(96, 102, 112, 255), outline=OUTLINE)
    return image


SPRITES = {
    "bandage": bandage(),
    "painkillers": painkillers(),
    "firstaid": firstaid(),
    "antibiotics": antibiotics(),
    "energy": energy(),
    "water": water(),
    "rations": rations(),
    "ammo_pistol": rounds((178, 142, 66, 255), 7, 3, 3),
    "ammo_rifle": rounds((176, 150, 84, 255), 11, 3, 3),
    "ammo_shotgun": rounds((174, 54, 48, 255), 8, 4, 2),
    "ammo_sniper": rounds((198, 168, 92, 255), 13, 4, 2),
    "gear_cap": gear_helmet((106, 104, 92, 255)),
    "gear_riot_helmet": gear_helmet((64, 68, 78, 255), visor=(150, 200, 226, 140)),
    "gear_military_helmet": gear_helmet((78, 88, 64, 255)),
    "gear_nvg_helmet": gear_helmet((58, 66, 52, 255), goggles=True),
    "gear_light_vest": gear_vest((96, 92, 80, 255)),
    "gear_military_vest": gear_vest((74, 86, 62, 255), plate=(52, 60, 46, 255)),
    "gear_heavy_vest": gear_vest((70, 74, 84, 255), plate=(150, 156, 168, 255)),
    "scope_x1": scope(1),
    "scope_x2": scope(2),
    "scope_x4": scope(4),
    "scope_x8": scope(8),
    "bunker_kit": bunker_kit(),
    "magazine": magazine(),
}


# ---------------------------------------------------------------- the HUD font
BAR_STEPS = 12
BAR_WIDTH, BAR_HEIGHT = 50, 9


def bar(fill, empty, steps, edge=(24, 26, 32, 255)):
    """One bar at one fill level, drawn as segments so the eye can count them without reading."""
    image = Image.new("RGBA", (BAR_WIDTH, BAR_HEIGHT), CLEAR)
    pen = ImageDraw.Draw(image)
    pen.rectangle([0, 1, BAR_WIDTH - 1, BAR_HEIGHT - 2], fill=empty, outline=edge)
    width = (BAR_WIDTH - 4) / float(BAR_STEPS)
    for index in range(steps):
        x0 = 2 + index * width
        pen.rectangle([x0, 3, x0 + width - 1.2, BAR_HEIGHT - 4], fill=fill)
        pen.line([x0, 3, x0 + width - 1.2, 3], fill=shade(fill, 1.35))
    return image


def icon_bullet():
    image = Image.new("RGBA", (7, 9), CLEAR)
    pen = ImageDraw.Draw(image)
    pen.rectangle([2, 3, 4, 8], fill=(178, 142, 66, 255), outline=OUTLINE)
    pen.polygon([(2, 3), (3, 0), (4, 3)], fill=(206, 176, 96, 255))
    return image


def icon_drop(colour):
    image = Image.new("RGBA", (7, 9), CLEAR)
    pen = ImageDraw.Draw(image)
    pen.polygon([(3, 0), (6, 6), (3, 8), (0, 6)], fill=colour, outline=OUTLINE)
    return image


def icon_virus():
    image = Image.new("RGBA", (9, 9), CLEAR)
    pen = ImageDraw.Draw(image)
    pen.ellipse([2, 2, 6, 6], fill=(74, 150, 82, 255), outline=OUTLINE)
    for point in ((4, 0), (4, 8), (0, 4), (8, 4)):
        pen.point(point, fill=(74, 150, 82, 255))
    return image


# ---------------------------------------------------------------- the sights
def crosshair():
    """The red dot every unscoped gun aims down. Always centred, because the client centres it."""
    image = Image.new("RGBA", (15, 15), CLEAR)
    pen = ImageDraw.Draw(image)
    dot = (228, 62, 54, 255)
    ring = (18, 18, 20, 120)
    pen.rectangle([6, 6, 8, 8], fill=ring)
    pen.rectangle([7, 7, 7, 7], fill=dot)
    for x0, y0, x1, y1 in ((7, 0, 7, 2), (7, 12, 7, 14), (0, 7, 2, 7), (12, 7, 14, 7)):
        pen.rectangle([x0, y0, x1, y1], fill=(236, 236, 240, 190))
    return image


def spyglass_scope():
    """The sight picture for four times and eight times: a black surround and a mil-dot reticle."""
    size = 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    pen = ImageDraw.Draw(image)
    centre = size / 2
    radius = size * 0.46
    pen.ellipse([centre - radius, centre - radius, centre + radius, centre + radius],
                fill=(0, 0, 0, 0))
    # A soft inner edge, so the circle does not look like a hole cut with scissors.
    for step in range(9):
        alpha = int(170 * (step / 8.0) ** 2)
        r = radius + step
        pen.ellipse([centre - r, centre - r, centre + r, centre + r],
                    outline=(0, 0, 0, alpha), width=2)

    line = (16, 18, 20, 235)
    pen.line([centre, centre - radius * 0.92, centre, centre + radius * 0.92], fill=line, width=2)
    pen.line([centre - radius * 0.92, centre, centre + radius * 0.92, centre], fill=line, width=2)
    # Mil dots down the lower post and out along the arms - what a real reticle uses for holdover.
    for step in range(1, 5):
        offset = radius * 0.17 * step
        pen.ellipse([centre - 2, centre + offset - 2, centre + 2, centre + offset + 2], fill=line)
        pen.line([centre - offset, centre - 4, centre - offset, centre + 4], fill=line, width=2)
        pen.line([centre + offset, centre - 4, centre + offset, centre + 4], fill=line, width=2)
    pen.ellipse([centre - 2, centre - 2, centre + 2, centre + 2], fill=(206, 54, 48, 255))
    return image


# ---------------------------------------------------------------- writing it all out
def write_item(name, image):
    image.save(os.path.join(TEXTURES, name + ".png"))
    with io.open(os.path.join(MODELS, name + ".json"), "w", encoding="utf-8") as out:
        json.dump({"parent": "minecraft:item/generated",
                   "textures": {"layer0": "asuracraft:item/" + name}}, out, indent=1)
    with io.open(os.path.join(ITEMS, name + ".json"), "w", encoding="utf-8") as out:
        json.dump({"model": {"type": "minecraft:model",
                             "model": "asuracraft:item/" + name}}, out, indent=1)


def main():
    for folder in (ITEMS, MODELS, TEXTURES, FONT_TEX, FONT_DEF,
                   os.path.join(VANILLA, "textures", "gui", "sprites", "hud"),
                   os.path.join(VANILLA, "textures", "misc")):
        os.makedirs(folder, exist_ok=True)

    for name, image in SPRITES.items():
        write_item(name, image)
    print("items  ", len(SPRITES))

    providers = []
    for step in range(BAR_STEPS + 1):
        health = bar((202, 54, 46, 255), (44, 22, 24, 255), step)
        thirst = bar((72, 148, 206, 255), (20, 32, 44, 255), step)
        health.save(os.path.join(FONT_TEX, "hp_%02d.png" % step))
        thirst.save(os.path.join(FONT_TEX, "water_%02d.png" % step))
        providers.append({"type": "bitmap", "file": "asuracraft:font/warz/hp_%02d.png" % step,
                          "ascent": 8, "height": 9, "chars": [chr(0xE200 + step)]})
        providers.append({"type": "bitmap", "file": "asuracraft:font/warz/water_%02d.png" % step,
                          "ascent": 8, "height": 9, "chars": [chr(0xE210 + step)]})

    icon_bullet().save(os.path.join(FONT_TEX, "bullet.png"))
    icon_drop((186, 40, 36, 255)).save(os.path.join(FONT_TEX, "bleed.png"))
    icon_virus().save(os.path.join(FONT_TEX, "virus.png"))
    providers.append({"type": "bitmap", "file": "asuracraft:font/warz/bullet.png",
                      "ascent": 8, "height": 9, "chars": [""]})
    providers.append({"type": "bitmap", "file": "asuracraft:font/warz/bleed.png",
                      "ascent": 8, "height": 9, "chars": [""]})
    providers.append({"type": "bitmap", "file": "asuracraft:font/warz/virus.png",
                      "ascent": 8, "height": 9, "chars": [""]})

    with io.open(os.path.join(FONT_DEF, "hud.json"), "w", encoding="utf-8") as out:
        json.dump({"providers": providers}, out, ensure_ascii=False, indent=1)
    print("hud    ", len(providers), "glyphs")

    crosshair().save(os.path.join(VANILLA, "textures", "gui", "sprites", "hud", "crosshair.png"))
    spyglass_scope().save(os.path.join(VANILLA, "textures", "misc", "spyglass_scope.png"))
    print("sights  crosshair + spyglass overlay")


if __name__ == "__main__":
    main()
