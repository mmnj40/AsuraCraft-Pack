# -*- coding: utf-8 -*-
"""Draws the damage numbers as pictures, with a real outline.

Minecraft's text shadow is a single dark copy one pixel down and to the right - good enough for chat,
but on a number flying over a monster it reads as a smudge on two sides rather than an edge on four.
A drawn glyph can have a proper outline all the way round, which is what every RPG's floating damage
looks like, and it costs the server nothing: the picture is chosen by the client from the pack, and the
server still just sends a short string.

Two sets are built, because the first attempt did not look right and the reason was the source, not the
outline:

  MC    the game's own digits, lifted out of the client's font sheet. They were drawn on a five-by-seven
        pixel grid to begin with, so every stem is one pixel and every curve lands on a whole pixel.
  KANIT the Kanit typeface rendered at thirteen pixels and forced hard. Kanit is a typeface for print;
        squeezed onto a grid this small its stems come out uneven and its curves lumpy.

Colour has to be baked in either way: a bitmap glyph ignores the colour the server asks for, so there is
one set per colour - white for an ordinary hit, gold and bigger for a critical.
"""
import io
import json
import os
import zipfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
TEXTURES = os.path.join(PACK, "assets", "asuracraft", "textures", "font")
FONTS = os.path.join(PACK, "assets", "asuracraft", "font")
TTF = os.path.join(PACK, "assets", "minecraft", "font", "thai.ttf")
CLIENT = os.path.join(os.environ["APPDATA"], ".minecraft", "versions", "26.2", "26.2.jar")

GLYPHS = "0123456789.,KM+"
OUTLINE = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)
GOLD = (255, 198, 64, 255)

# where each set starts in the private use area
STARTS = {("mc", "white"): 0xE100, ("mc", "crit"): 0xE120,
          ("kanit", "white"): 0xE140, ("kanit", "crit"): 0xE160}


def ink_from_client(character):
    """Cuts one character out of the game's own font sheet, as a solid mask."""
    with zipfile.ZipFile(CLIENT) as jar:
        with jar.open("assets/minecraft/textures/font/ascii.png") as file:
            sheet = Image.open(io.BytesIO(file.read())).convert("RGBA")
    cell = sheet.width // 16                      # the sheet is sixteen characters across
    code = ord(character)
    box = ((code % 16) * cell, (code // 16) * cell)
    tile = sheet.crop((box[0], box[1], box[0] + cell, box[1] + cell))
    mask = tile.split()[3].point(lambda level: 255 if level > 80 else 0)
    return mask.crop(mask.getbbox()) if mask.getbbox() else mask


def ink_from_kanit(character, size):
    font = ImageFont.truetype(TTF, size)
    box = font.getbbox(character)
    mask = Image.new("L", (max(1, box[2] - box[0]) + 2, size + 2), 0)
    ImageDraw.Draw(mask).text((1 - box[0], 1 - box[1]), character, font=font, fill=255)
    mask = mask.point(lambda level: 255 if level > 110 else 0)
    return mask.crop(mask.getbbox()) if mask.getbbox() else mask


def glyph(mask, scale, fill):
    """Scales the ink by a whole number, then rings it in black."""
    if scale != 1:
        mask = mask.resize((mask.width * scale, mask.height * scale), Image.NEAREST)
    pad = 2
    canvas = Image.new("L", (mask.width + pad * 2, mask.height + pad * 2), 0)
    canvas.paste(mask, (pad, pad))
    ring = canvas.filter(ImageFilter.MaxFilter(3))
    image = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    image.paste(OUTLINE, mask=ring)
    image.paste(fill, mask=canvas)
    return image


def main():
    path = os.path.join(FONTS, "ui.json")
    existing = json.load(io.open(path, encoding="utf-8"))["providers"]
    providers = [p for p in existing if p["type"] != "bitmap" or "num_" not in p.get("file", "")]

    for (family, tone), first in STARTS.items():
        crit = tone == "crit"
        for index, character in enumerate(GLYPHS):
            if family == "mc":
                mask = ink_from_client(character)
                picture = glyph(mask, 2 if crit else 1, GOLD if crit else WHITE)
            else:
                mask = ink_from_kanit(character, 19 if crit else 13)
                picture = glyph(mask, 1, GOLD if crit else WHITE)
            file = "num_%s_%s_%02d.png" % (family, tone, index)
            picture.save(os.path.join(TEXTURES, file))
            providers.append({
                "type": "bitmap",
                "file": "asuracraft:font/" + file,
                "ascent": picture.height - 2,
                "height": picture.height,
                "chars": [chr(first + index)],
            })

    with io.open(path, "w", encoding="utf-8") as out:
        json.dump({"providers": providers}, out, ensure_ascii=False, indent=2)

    zip_path = os.path.join(HERE, "AsuraCraft-Thai.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as pack:
        for folder, _, files in os.walk(PACK):
            for name in files:
                full = os.path.join(folder, name)
                pack.write(full, os.path.relpath(full, PACK).replace(os.sep, "/"))
    print("digits", len(GLYPHS) * len(STARTS), "glyphs |", ", ".join(
        "%s/%s at U+%04X" % (f, t, c) for (f, t), c in STARTS.items()))


if __name__ == "__main__":
    main()
