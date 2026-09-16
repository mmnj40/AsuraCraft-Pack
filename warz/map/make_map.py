# -*- coding: utf-8 -*-
"""The plan for the map: what is where, and why it is there.

Six thousand blocks on a side, and every one of the places on it is put where it is for a reason that
comes out of how survival maps are actually played rather than out of what looks tidy on a grid.

The shape is borrowed from the map that got this right first. Chernarus puts its players on a coast,
its towns inland, and its military bases at the far end - so a run from where you wake up to the gun
you want is a journey across the whole map that gets more dangerous the further you go, and everybody
on the server is moving in roughly the same direction as everybody else. That is what makes a map feel
like a place instead of a menu of buildings.

So: the south coast is where people arrive, and it is poor. The middle of the map is a city, which is
where the good civilian gear is and where most people die. The north is the army, which is where the
rifles are and where the fights are. The east is industry and the port; the west is the things nobody
wants near a town - a prison, a quarry, a laboratory.

Every place also has to be findable without a map screen, so the big ones are landmarks in their own
right: a tower block visible from a mile away, a radio mast on a hill, a stadium, a dam.
"""
import io
import json
import math
import os
import random

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
FULL = 6000
HALF = FULL // 2

# name, kind, x, z, radius, loot tier, infected level
PLACES = [
    # ---------------------------------------------------------------- the coast: where people wake up
    ("ท่าเรือประมง", "safe", 120, 2600, 110, 0, 0),
    ("หมู่บ้านชายหาด", "village", -620, 2500, 130, 1, 1),
    ("โมเต็ลริมทาง", "motel", 700, 2380, 110, 1, 1),
    ("ท่าจอดเรือ", "marina", 1420, 2560, 120, 1, 1),
    ("บ้านประมงเก่า", "village", -1500, 2620, 110, 1, 1),
    ("ปั๊มชายฝั่ง", "petrol", -120, 2180, 80, 1, 1),
    ("ถนนเลียบหาด", "village", 2000, 2400, 120, 1, 2),

    # ---------------------------------------------------------------- inland: farms and dormitories
    ("หมู่บ้านสวนยาง", "village", -1900, 1700, 130, 1, 2),
    ("ฟาร์มโคนม", "farm", -900, 1500, 150, 1, 2),
    ("ไร่ข้าวโพด", "farm", 600, 1560, 160, 1, 2),
    ("โรงสีข้าว", "industry", 1500, 1500, 120, 2, 2),
    ("โรงเรียนบ้านหนองแค", "school", -200, 1240, 120, 2, 2),
    ("สถานีรถไฟใต้", "station", 1100, 1080, 130, 2, 2),
    ("ปั๊มสี่แยก", "petrol", -1250, 1120, 80, 1, 2),
    ("หมู่บ้านจัดสรร", "suburb", 1900, 1150, 150, 2, 2),
    ("วัดร้าง", "church", -2350, 1250, 100, 1, 2),
    ("จุดพักรถ", "safe", -1800, 400, 100, 0, 0),

    # ---------------------------------------------------------------- the city
    ("ดาวน์ทาวน์", "downtown", 0, 0, 260, 3, 4),
    ("ห้างสรรพสินค้า", "mall", 520, 330, 180, 3, 4),
    ("โรงพยาบาลกลาง", "hospital", -480, 260, 170, 3, 3),
    ("กองบัญชาการตำรวจ", "police", 340, -320, 150, 3, 3),
    ("อาคารจอดรถ", "garage", -260, -300, 130, 2, 3),
    ("สถานีดับเพลิง", "fire", 780, -120, 110, 2, 2),
    ("ธนาคารกลาง", "bank", -760, -140, 120, 3, 3),
    ("อพาร์ตเมนต์เหนือ", "apartments", -140, -700, 160, 2, 3),
    ("อพาร์ตเมนต์ใต้", "apartments", 260, 760, 160, 2, 3),
    ("สนามกีฬา", "stadium", 1150, -520, 180, 2, 3),
    ("ตลาดสด", "market", -1050, 620, 130, 2, 3),
    ("โรงแรมเมือง", "motel", 900, 620, 120, 2, 3),

    # ---------------------------------------------------------------- east: the port and the works
    ("ท่าเรือสินค้า", "port", 2300, 300, 220, 3, 3),
    ("โรงงานเหล็ก", "industry", 1750, -180, 180, 2, 3),
    ("คลังสินค้าตะวันออก", "warehouse", 2450, 900, 150, 2, 2),
    ("โรงไฟฟ้า", "power", 2600, -600, 170, 3, 3),
    ("ลานรถไฟ", "station", 1600, 760, 150, 2, 2),
    ("คลังน้ำมัน", "warehouse", 2750, 1500, 140, 2, 2),

    # ---------------------------------------------------------------- west: what nobody wants nearby
    ("เรือนจำกลาง", "prison", -2400, -300, 200, 3, 4),
    ("เหมืองหิน", "quarry", -1750, -900, 180, 2, 3),
    ("เขื่อน", "dam", -2700, 500, 170, 2, 2),
    ("แคมป์ตัดไม้", "logging", -1500, -1600, 130, 1, 2),
    ("สถานีวิจัย", "lab", -2600, -1500, 160, 3, 5),
    ("ด่านตะวันตก", "checkpoint", -1200, -600, 90, 2, 3),

    # ---------------------------------------------------------------- north: the army
    ("ด่านเหนือ", "checkpoint", 200, -1400, 90, 2, 3),
    ("ค่ายทหาร", "barracks", -500, -1900, 190, 3, 4),
    ("สนามบินทหาร", "airfield", 800, -2200, 260, 3, 4),
    ("คลังอาวุธ", "armoury", -1400, -2400, 150, 3, 5),
    ("สถานีเรดาร์", "radar", 1700, -2600, 130, 3, 4),
    ("ฐานบัญชาการเหนือ", "barracks", -200, -2700, 170, 3, 5),
    ("จุดส่งกำลังบำรุง", "warehouse", 1300, -1700, 130, 2, 3),
    ("แคมป์ผู้รอดชีวิต", "safe", 2300, -1200, 100, 0, 0),
]

# The roads. Each is a list of points the road runs through, and the network is what ties the map into
# one place rather than fifty - people navigate by junctions long before they know any building.
ROADS = [
    [(-2000, 2600), (0, 2450), (2100, 2450)],                 # the coast road
    [(120, 2600), (0, 1800), (0, 700), (0, 0)],               # south highway into the city
    [(0, 0), (0, -1400), (-500, -1900), (-200, -2700)],       # the north highway
    [(0, 0), (1600, 100), (2300, 300)],                       # the port road
    [(0, 0), (-1200, -600), (-2400, -300)],                   # the west road
    [(-900, 1500), (-200, 1240), (600, 1560), (1500, 1500)],  # the farm loop
    [(800, -2200), (200, -1400)],                             # the airfield spur
    [(1150, -520), (1750, -180), (2600, -600)],               # the industrial belt
    [(-1800, 400), (-1050, 620), (0, 700)],                   # the western approach
]


def colour_for(kind):
    return {
        "safe": (86, 176, 106),
        "downtown": (232, 226, 210),
        "mall": (214, 176, 108),
        "hospital": (236, 236, 244),
        "police": (96, 132, 220),
        "apartments": (184, 176, 166),
        "garage": (150, 146, 142),
        "fire": (208, 96, 74),
        "bank": (206, 190, 132),
        "market": (196, 164, 116),
        "stadium": (150, 190, 130),
        "village": (168, 150, 120),
        "suburb": (176, 164, 132),
        "motel": (196, 156, 128),
        "marina": (120, 168, 196),
        "petrol": (222, 178, 70),
        "farm": (162, 188, 108),
        "church": (198, 186, 162),
        "school": (188, 172, 118),
        "station": (140, 134, 128),
        "port": (110, 146, 178),
        "industry": (138, 128, 118),
        "warehouse": (150, 142, 128),
        "power": (168, 140, 96),
        "prison": (128, 122, 130),
        "quarry": (152, 140, 118),
        "dam": (126, 156, 176),
        "logging": (128, 148, 100),
        "lab": (170, 120, 190),
        "checkpoint": (150, 160, 120),
        "barracks": (110, 132, 88),
        "airfield": (120, 128, 108),
        "armoury": (150, 108, 84),
        "radar": (128, 150, 158),
    }.get(kind, (170, 170, 170))


def preview(path):
    """A picture of the plan, at one pixel to four blocks."""
    scale = 4
    size = FULL // scale
    image = Image.new("RGB", (size, size), (28, 32, 30))
    pen = ImageDraw.Draw(image)
    rng = random.Random(11)

    # Ground: a dry green with patches, so the roads and towns have something to sit on.
    for _ in range(26000):
        x = rng.randrange(size)
        y = rng.randrange(size)
        shade = rng.randrange(-12, 13)
        pen.point((x, y), fill=(34 + shade, 44 + shade, 34 + shade))

    def to_pixel(x, z):
        return ((x + HALF) // scale, (z + HALF) // scale)

    for road in ROADS:
        points = [to_pixel(x, z) for x, z in road]
        pen.line(points, fill=(74, 70, 64), width=3)

    for name, kind, x, z, radius, loot, zombies in PLACES:
        px, py = to_pixel(x, z)
        r = max(3, radius // scale)
        pen.ellipse((px - r, py - r, px + r, py + r), fill=colour_for(kind))
        if loot >= 3:
            pen.ellipse((px - r - 2, py - r - 2, px + r + 2, py + r + 2),
                        outline=(214, 92, 72), width=1)

    # The border of the playable area.
    pen.rectangle((1, 1, size - 2, size - 2), outline=(96, 86, 70), width=2)
    image = image.resize((size * 2, size * 2), Image.NEAREST)
    image.save(path)


def main():
    places = []
    for name, kind, x, z, radius, loot, zombies in PLACES:
        places.append({"name": name, "kind": kind, "x": x, "z": z, "radius": radius,
                       "loot": loot, "zombies": zombies, "open": True})
    data = {"full": FULL, "open": FULL, "places": places,
            "roads": [[{"x": x, "z": z} for x, z in road] for road in ROADS]}

    with io.open(os.path.join(HERE, "map.json"), "w", encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=1)
    target = os.path.join(HERE, "..", "..", "..", "Minecraft_Server_Develop",
                          "Folia_Plugin_Develop", "warz", "src", "main", "resources", "map.json")
    target = os.path.normpath(target)
    with io.open(target, "w", encoding="utf-8") as out:
        json.dump(data, out, ensure_ascii=False, indent=1)

    preview(os.path.join(HERE, "map.png"))
    tiers = {}
    for place in places:
        tiers[place["loot"]] = tiers.get(place["loot"], 0) + 1
    print("map    ", len(places), "places over", FULL, "blocks;",
          len(ROADS), "roads; loot tiers", dict(sorted(tiers.items())))
    print("wrote  ", target)


if __name__ == "__main__":
    main()
