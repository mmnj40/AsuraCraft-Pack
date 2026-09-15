# -*- coding: utf-8 -*-
"""Cuts gun sounds out of a public-domain recording, without an audio encoder anywhere in sight.

There is no ffmpeg on this machine and no Vorbis encoder in Python, so re-encoding audio is off the
table. Cutting it is not: an Ogg stream is a chain of pages, each stamped with how many samples have
been played by its end, and a shorter file is simply the header pages followed by however many audio
pages reach the length wanted - with the end-of-stream flag moved onto the last one kept and its
checksum recomputed. No samples are decoded, so nothing is re-encoded and nothing is degraded.

The source is "Gunshots 8.ogg" from Wikimedia Commons, public domain, mono, 44.1 kHz. Mono matters more
than it sounds: Minecraft plays a stereo file flat in both ears with no position at all, so a stereo
gunshot would come from everywhere at once - useless in a game where the whole point is working out
which direction it came from.

The guns are then told apart by pitch at playback rather than by separate files, which is what the
pitch argument on playSound has always been for.
"""
import io
import json
import os
import struct
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
SOUNDS = os.path.join(PACK, "assets", "asuracraft", "sounds", "gun")

SOURCE = "https://upload.wikimedia.org/wikipedia/commons/e/ee/Gunshots_8.ogg"
AGENT = {"User-Agent": "AsuraCraftPack/1.0 (Minecraft resource pack)"}

# Ogg's checksum: the usual CRC-32 polynomial, but with no reflection and no final inversion, which is
# why a stock crc32 gives the wrong answer and the page is rejected as corrupt.
def crc_table():
    table = []
    for index in range(256):
        value = index << 24
        for _ in range(8):
            value = ((value << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if value & 0x80000000 \
                else (value << 1) & 0xFFFFFFFF
        table.append(value)
    return table


TABLE = crc_table()


def crc(data):
    value = 0
    for byte in data:
        value = ((value << 8) & 0xFFFFFFFF) ^ TABLE[((value >> 24) & 0xFF) ^ byte]
    return value


def pages(data):
    """Every Ogg page in the file, as (start, end, header_type, granule)."""
    out = []
    at = 0
    while True:
        at = data.find(b"OggS", at)
        if at < 0:
            return out
        header_type = data[at + 5]
        granule = struct.unpack("<q", data[at + 6:at + 14])[0]
        segments = data[at + 26]
        table = data[at + 27:at + 27 + segments]
        end = at + 27 + segments + sum(table)
        out.append((at, end, header_type, granule))
        at = end


def trim(data, seconds, rate=44100):
    """The same stream, stopped early: header pages, then audio pages up to the length wanted."""
    target = int(seconds * rate)
    kept = []
    for start, end, header_type, granule in pages(data):
        kept.append((start, end, header_type, granule))
        if granule > target:
            break

    out = bytearray()
    for index, (start, end, header_type, granule) in enumerate(kept):
        page = bytearray(data[start:end])
        if index == len(kept) - 1:
            page[5] = header_type | 0x04          # end of stream
            page[22:26] = b"\x00\x00\x00\x00"     # the checksum is computed over a zeroed field
            page[22:26] = struct.pack("<I", crc(bytes(page)))
        out += page
    return bytes(out)


def main():
    os.makedirs(SOUNDS, exist_ok=True)
    request = urllib.request.Request(SOURCE, headers=AGENT)
    original = urllib.request.urlopen(request, timeout=60).read()

    # One shot, and a shorter, drier crack for the pistol. Trimming to different lengths from the same
    # recording is the only editing available here, and it is enough for two distinct reports.
    cuts = {"shot": 0.75, "shot_short": 0.45}
    for name, seconds in cuts.items():
        path = os.path.join(SOUNDS, name + ".ogg")
        with io.open(path, "wb") as out:
            out.write(trim(original, seconds))
        print("  %-12s %.2fs  %6d bytes" % (name, seconds, os.path.getsize(path)))

    # What the server asks for by name. Each entry is one file; the guns are told apart by the pitch
    # they are played at, which costs nothing and needs no second recording.
    definitions = {
        "gun.shot": {
            "category": "player",
            "sounds": [{"name": "asuracraft:gun/shot", "stream": False}],
        },
        "gun.shot_short": {
            "category": "player",
            "sounds": [{"name": "asuracraft:gun/shot_short", "stream": False}],
        },
    }
    path = os.path.join(PACK, "assets", "asuracraft", "sounds.json")
    with io.open(path, "w", encoding="utf-8") as out:
        json.dump(definitions, out, ensure_ascii=False, indent=2)

    # Who it came from, kept with the pack rather than in somebody's memory.
    credits = (
        "AsuraCraft resource pack - sound credits\n\n"
        "gun/shot.ogg, gun/shot_short.ogg\n"
        "  cut from \"Gunshots 8.ogg\" by aradlaw, via Wikimedia Commons\n"
        "  https://commons.wikimedia.org/wiki/File:Gunshots_8.ogg\n"
        "  Public domain (from PDSounds.org). No attribution required; recorded here anyway.\n"
    )
    with io.open(os.path.join(HERE, "CREDITS.txt"), "w", encoding="utf-8") as out:
        out.write(credits)
    print("sounds  2 files + sounds.json + CREDITS.txt")


if __name__ == "__main__":
    main()
