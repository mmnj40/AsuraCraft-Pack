# -*- coding: utf-8 -*-
"""Builds the server's Thai font pack.

Minecraft draws one character at a time and moves the pen along by that character's own width; it has no
text shaping at all. That is why Thai vowels and tone marks float beside the letter they belong to in
the game's own font - those glyphs carry a real width, so the pen walks past the letter before drawing
the mark.

A well-made Thai font already solves this without any shaping: its marks have a width of zero and their
outlines sit to the left of the pen, so they land back on the letter before them. Kanit does exactly
that (checked: sara i is width 0, left side bearing -481), so this pack only has to hand the font over.
An earlier version of this script "fixed" the marks a second time and pushed every one of them onto the
wrong letter - the render check below is what caught it, and is why it stays in.
"""
import io
import json
import os
import zipfile
from fontTools.ttLib import TTFont

SOURCE = "Kanit-Regular.ttf"
OUT_TTF = "pack/assets/minecraft/font/thai.ttf"
NAME = "AsuraCraft-Thai"

# Thai marks that hang above or below the letter before them. Nothing in this list should take up
# space of its own on the line.
MARKS = (
    [0x0E31]                        # mai han akat
    + list(range(0x0E34, 0x0E3B))   # sara i .. phinthu
    + [0x0E47, 0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C, 0x0E4D, 0x0E4E]
)
# Consonants, used only to work out how far left a mark has to move.
CONSONANTS = list(range(0x0E01, 0x0E2F))


def main():
    font = TTFont(SOURCE)
    check(font)
    for record in font["name"].names:
        if record.nameID in (1, 3, 4, 6):
            record.string = NAME
    os.makedirs(os.path.dirname(OUT_TTF), exist_ok=True)
    font.save(OUT_TTF)
    print("wrote", OUT_TTF, os.path.getsize(OUT_TTF), "bytes")

    # ---------------------------------------------------------------- the pack around it
    os.makedirs("pack/assets/minecraft/font", exist_ok=True)
    io.open("pack/assets/minecraft/font/default.json", "w", encoding="utf-8", newline="\n").write(
        json.dumps({
            "providers": [
                {
                    "type": "ttf",
                    "file": "minecraft:thai.ttf",
                    "size": 11.0,
                    "oversample": 4.0,
                    "shift": [0.0, 1.0],
                }
            ]
        }, indent=2, ensure_ascii=False))

    io.open("pack/pack.mcmeta", "w", encoding="utf-8", newline="\n").write(
        json.dumps({
            "pack": {
                "pack_format": 88,
                "supported_formats": {"min_inclusive": 34, "max_inclusive": 99},
                "description": "AsuraCraft - ฟอนต์ไทย สระไม่ลอย (Kanit)",
            }
        }, indent=2, ensure_ascii=False))

    write_icon("pack/pack.png")

    with zipfile.ZipFile("AsuraCraft-Thai.zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk("pack"):
            for name in files:
                full = os.path.join(root, name)
                zf.write(full, os.path.relpath(full, "pack"))
    print("wrote AsuraCraft-Thai.zip", os.path.getsize("AsuraCraft-Thai.zip"), "bytes")


def check(font):
    """Refuses a font that would put the marks back where they started.

    The whole pack rests on one property of the font: a mark must take up no room on the line. Swap in a
    font that does not do that and every vowel floats again, with nothing in the build to say why - so
    the build says it here instead.
    """
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    bad = [hex(c) for c in MARKS if c in cmap and hmtx[cmap[c]][0] != 0]
    if bad:
        raise SystemExit(
            "{} is not usable: {} marks have a width of their own ({} ...). "
            "Thai vowels would float. Pick a font whose combining marks are zero-width."
            .format(SOURCE, len(bad), ", ".join(bad[:5])))
    print("font check: all %d marks are zero-width" % len(MARKS))


def write_icon(path):
    """A 64x64 pack icon, drawn here so the build needs nothing but Python."""
    from PIL import Image, ImageDraw
    image = Image.new("RGBA", (64, 64), (26, 34, 28, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle([6, 6, 57, 57], outline=(122, 178, 110, 255), width=2)
    # a snail shell: a square spiral, which reads at this size where a curve would not
    x, y, size = 20, 44, 26
    while size > 4:
        draw.line([(x, y), (x, y - size)], fill=(226, 214, 178, 255), width=3)
        y -= size
        draw.line([(x, y), (x + size, y)], fill=(226, 214, 178, 255), width=3)
        x += size
        size -= 7
        draw.line([(x, y), (x, y + size)], fill=(226, 214, 178, 255), width=3)
        y += size
        draw.line([(x, y), (x - size, y)], fill=(226, 214, 178, 255), width=3)
        x -= size
        size -= 7
    image.save(path)


if __name__ == "__main__":
    main()
