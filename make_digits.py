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

GLYPHS = "0123456789.,KM+!"
OUTLINE = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)
GOLD = (255, 198, 64, 255)

# Four families to choose between, each with a plain and a critical set. Everything but "mc" is a
# pixel typeface - drawn on a grid to begin with, so it survives being shrunk to a few pixels tall,
# which is exactly what Kanit could not do.
def pixel(name, size, crit=None):
    """A typeface from the fonts folder, rendered at a size that lands on the pixel grid."""
    return {"source": os.path.join(HERE, "fonts", name), "size": size,
            "scale": 1, "crit_scale": 1, "crit_size": crit or round(size * 1.25)}


# The families to choose between. All but "mc" are pixel typefaces - drawn on a grid to begin with, so
# they survive being rendered a few pixels tall. Typefaces built from curves do not: Kanit, Russo One,
# Orbitron, Bungee and Teko were all tried here and every one of them came out of the threshold with
# uneven stems and lumpy bowls, because at eight pixels there is nowhere for a curve to go.
#
# A critical is bigger, but only a little: at double size it stopped reading as the same number in a
# louder voice and started reading as a different kind of thing altogether. A quarter up in point size
# lands about a fifth taller on the grid, which is enough to notice and not enough to shout.
FAMILIES = {
    "mc":       {"source": "client", "size": 0, "scale": 1, "crit_scale": 2},
    "silk":     pixel("Silkscreen-Bold.ttf", 8, 10),
    "arcade":   pixel("PressStart2P-Regular.ttf", 8, 10),
    "jersey":   pixel("Jersey10-Regular.ttf", 14),
    "jersey15": pixel("Jersey15.ttf", 14),
    "pixelify": pixel("PixelifySans.ttf", 14),
    "tiny5":    pixel("Tiny5.ttf", 12),
    "micro5":   pixel("Micro5.ttf", 16),
    "dot":      pixel("DotGothic16.ttf", 10),
    "doto":     pixel("Doto.ttf", 12),
    "handjet":  pixel("Handjet.ttf", 12),
    "terminal": pixel("VT323-Regular.ttf", 12),
}
# Every family gets every one of these. A bitmap cannot be tinted by the server - the picture carries
# its own colour - so each one is baked, and a colour that is not baked cannot be asked for later.
#
# A pair of colours means a gradient down the glyph, which is the one thing a drawn number can do that
# coloured text cannot: real damage numbers in action games are almost never flat.
TONES = {
    "white":   (255, 255, 255, 255),
    "gold":    (255, 198, 64, 255),
    "orange":  (255, 122, 41, 255),
    "magenta": (255, 79, 216, 255),
    "cyan":    (110, 231, 255, 255),
    "violet":  (176, 132, 255, 255),
    "hurt":    (255, 86, 86, 255),
    "heal":    (126, 240, 130, 255),
    "fire":    ((255, 236, 120, 255), (255, 72, 32, 255)),
    "ice":     ((255, 255, 255, 255), (64, 158, 255, 255)),
}
BASE = 0xE100          # families and tones are laid out 32 codepoints apart from here


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


def ink_from_ttf(path, character, size):
    font = ImageFont.truetype(path, size)
    box = font.getbbox(character)
    mask = Image.new("L", (max(1, box[2] - box[0]) + 2, size + 2), 0)
    ImageDraw.Draw(mask).text((1 - box[0], 1 - box[1]), character, font=font, fill=255)
    mask = mask.point(lambda level: 255 if level > 110 else 0)
    return mask.crop(mask.getbbox()) if mask.getbbox() else mask


def shade(size, fill):
    """A flat colour, or a top-to-bottom gradient when two are given."""
    if not isinstance(fill[0], tuple):
        return Image.new("RGBA", size, fill)
    top, bottom = fill
    band = Image.new("RGBA", size)
    pixels = band.load()
    for row in range(size[1]):
        share = row / max(1, size[1] - 1)
        pixels[0, row] = tuple(round(top[part] + (bottom[part] - top[part]) * share) for part in range(4))
    for column in range(1, size[0]):
        for row in range(size[1]):
            pixels[column, row] = pixels[0, row]
    return band


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
    image.paste(shade(canvas.size, fill), mask=canvas)
    return image


# Each tone gets a block of 32 codepoints and each family gets one block per tone. The stride is
# computed rather than written down: it was a fixed 128 while there were four tones, and a fifth tone
# would have quietly walked the next family's glyphs over the last one's.
STRIDE = 32
FAMILY_STRIDE = STRIDE * len(TONES)


def start_of(family, tone):
    """Where a family and tone begin in the private use area."""
    return BASE + list(FAMILIES).index(family) * FAMILY_STRIDE + list(TONES).index(tone) * STRIDE


def main():
    path = os.path.join(FONTS, "ui.json")
    existing = json.load(io.open(path, encoding="utf-8"))["providers"]
    providers = [p for p in existing if p["type"] != "bitmap" or "num_" not in p.get("file", "")]

    # Sweep out the pictures of families that have since been dropped. Leaving them behind only puts
    # dead weight in the download and glyphs in the atlas that nothing points at any more.
    for stale in os.listdir(TEXTURES):
        if stale.startswith("num_"):
            os.remove(os.path.join(TEXTURES, stale))

    for family, spec in FAMILIES.items():
        for tone, colour in TONES.items():
            crit = tone == "crit"
            first = start_of(family, tone)
            for index, character in enumerate(GLYPHS):
                if spec["source"] == "client":
                    mask = ink_from_client(character)
                else:
                    size = spec.get("crit_size", spec["size"]) if crit else spec["size"]
                    mask = ink_from_ttf(spec["source"], character, size)
                picture = glyph(mask, spec["crit_scale"] if crit else spec["scale"], colour)
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
    print("digits", len(GLYPHS) * len(FAMILIES) * len(TONES), "glyphs,",
          len(FAMILIES), "families x", len(TONES), "tones")
    for family in FAMILIES:
        print("  %-9s U+%04X .. U+%04X" % (
            family, start_of(family, list(TONES)[0]),
            start_of(family, list(TONES)[-1]) + len(GLYPHS) - 1))
    print("  stride: %d per family" % FAMILY_STRIDE)


if __name__ == "__main__":
    main()
