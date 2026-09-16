# -*- coding: utf-8 -*-
"""Builds the WarZ sound set from real firearm recordings.

The version before this one synthesised every sound from noise bursts and sine sweeps. On paper that is
how a game's sound designer builds a gunshot; in practice a synthesised report has no room in it - no
barrel, no air, no ground - and five weapons built from the same maths sound like five settings of one
machine. It was rejected, correctly.

So nothing here is synthesised. Every gunshot is an actual recording of an actual firearm, taken from
BigSoundBank, which releases under CC0 - public domain, no attribution required, commercial use fine.
The credits file names them anyway.

What this script does is the editing a sound designer would do with the same clips:

  trim      to the shot itself, from the onset, with the dead air before it cut away
  pitch     shifted without changing the length, so one 9mm recording can be a pistol and, a little
            brighter and shorter, a submachine gun
  filter    high-passed where a weapon should crack, low-passed where it should thump
  tail      an echo pair on the big weapons, which is the ground answering and the thing that makes a
            rifle sound like it was fired outdoors rather than in a booth
  far       a second copy of every shot, heavily low-passed with a long slap - what the weapon sounds
            like from two hundred blocks away, played to distant players so a firefight can be heard
            and walked towards

Everything is written as mono. That is not laziness: Minecraft plays a stereo file flat in both ears
with no position at all, so a stereo gunshot comes from everywhere at once - useless in a game whose
whole point is working out which direction it came from.
"""
import io
import json
import os
import re
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
SOUNDS = os.path.join(PACK, "assets", "asuracraft", "sounds")
SOURCES = os.path.join(HERE, "sources")
AGENT = {"User-Agent": "Mozilla/5.0 (AsuraCraft resource pack build)"}

FFMPEG = "ffmpeg"
for candidate in (
    r"C:\Users\dc2\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe",
):
    if os.path.exists(candidate):
        FFMPEG = candidate

# The recordings, by BigSoundBank id. All CC0.
SOURCE_FILES = {
    "0437": "Beretta M12, 9mm, one shot",
    "0438": ".357 Magnum, one shot",
    "0397": "Winchester Magnum XTR, one shot",
    "2853": "rifle, one shot",
    "2854": "rifle, one shot, second take",
    "0532": "shotgun, five shots",
    "1984": "pistol cocking, slow, two movements",
    "1985": "pistol cocking, fast",
    "1986": "pistol cocking, fast, second take",
    "1988": "magazine seated",
    "1990": "magazine seated, heavier",
    "1357": "9mm case falling on concrete",
}


def fetch():
    os.makedirs(SOURCES, exist_ok=True)
    for sid in SOURCE_FILES:
        path = os.path.join(SOURCES, sid + ".mp3")
        if os.path.exists(path):
            continue
        url = "https://bigsoundbank.com/UPLOAD/mp3/%s.mp3" % sid
        print("  fetching", sid)
        data = urllib.request.urlopen(
            urllib.request.Request(url, headers=AGENT), timeout=90).read()
        with io.open(path, "wb") as handle:
            handle.write(data)


def loudest(path):
    """The peak level of a file in dB, so the gain needed to normalise it can be worked out."""
    result = subprocess.run([FFMPEG, "-v", "info", "-i", path, "-af", "volumedetect",
                             "-f", "null", "-"], capture_output=True, text=True)
    found = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?) dB", result.stderr)
    return float(found.group(1)) if found else 0.0


def pitch(ratio):
    """Shifts pitch without changing length: resample the samples, then put the tempo back."""
    if abs(ratio - 1.0) < 0.001:
        return []
    # atempo only accepts 0.5 to 2.0, which is far wider than anything used here.
    return ["asetrate=44100*%.4f" % ratio, "aresample=44100", "atempo=%.4f" % (1.0 / ratio)]


def render(name, source, start, length, filters=(), shift=1.0, headroom=1.0):
    """One finished sound: cut, shaped, pitched, normalised, faded and encoded."""
    path = os.path.join(SOUNDS, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    chain = ["atrim=start=%.3f:duration=%.3f" % (start, length), "asetpts=PTS-STARTPTS"]
    chain += pitch(shift)
    chain += list(filters)
    # A fade at each end. Without the tail fade the file stops on a step, and a step is a click the
    # player hears on top of every single shot.
    chain += ["afade=t=in:st=0:d=0.002",
              "afade=t=out:st=%.3f:d=%.3f" % (max(0.0, length - 0.06), 0.06)]

    rough = path + ".tmp.wav"
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i",
                    os.path.join(SOURCES, source + ".mp3"),
                    "-af", ",".join(chain), "-ac", "1", "-ar", "44100", rough], check=True)

    # Normalised on peak rather than loudness. A gunshot is one enormous transient and almost nothing
    # else, and loudness normalisation would turn the quiet part up until the room noise is audible.
    gain = -loudest(rough) - (20.0 * (1.0 - headroom))
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", rough,
                    "-af", "volume=%.2fdB,alimiter=limit=0.90" % (gain - 1.0),
                    "-c:a", "libvorbis", "-q:a", "5", "-ac", "1", path + ".ogg"], check=True)
    os.remove(rough)
    return os.path.getsize(path + ".ogg")


# ---------------------------------------------------------------- what each weapon sounds like
#
# name, source, start, length, filters, pitch, headroom
#
# The pistol and the submachine gun share one 9mm recording and are told apart the way they would be in
# life: the submachine gun is a shorter barrel, so it is brighter, shorter and a touch higher. The rifle
# and the sniper are different recordings because a rifle and a magnum are genuinely different events
# and no amount of filtering makes one into the other.
SHOTS = {
    "gun/pistol":  ("0437", 0.00, 0.90, ("highpass=f=90", "aecho=0.6:0.5:55:0.18"), 1.00, 1.0),
    "gun/smg":     ("0437", 0.00, 0.55, ("highpass=f=170", "aecho=0.5:0.4:28:0.10"), 1.09, 1.0),
    "gun/rifle":   ("2853", 0.04, 1.10, ("highpass=f=70", "aecho=0.7:0.5:75|140:0.26|0.13"), 1.00, 1.0),
    "gun/sniper":  ("0397", 1.00, 1.80, ("lowpass=f=9000", "aecho=0.8:0.6:120|260|420:0.34|0.20|0.11"),
                    0.94, 1.0),
    # Two shotguns, and the server picks between them in its config.
    #
    # A: the shotgun recording itself, cut tight and left alone. The clip was made outdoors and already
    # has its own reverb; the first version added two more echoes on top of that and low-passed it at
    # seven kilohertz, which is why it came out bloated instead of sharp.
    "gun/shotgun":   ("0532", 0.065, 0.80, ("highpass=f=60", "lowpass=f=11000"), 0.97, 1.0),
    # B: the Winchester Magnum, dropped a tone and heavily darkened. Not a shotgun recording, but a
    # much bigger, rounder boom - which is what most people actually expect a game shotgun to sound
    # like. Switch with `sound: "asuracraft:gun.shotgun_b"` under guns.shotgun in the server config.
    "gun/shotgun_b": ("0397", 1.00, 1.30, ("lowpass=f=4200", "aecho=0.8:0.6:110|230:0.30|0.16"),
                      0.86, 1.0),
    # The heavy pistols: a real .357 recording, which is a completely different noise from a 9mm and is
    # the whole reason a revolver is worth carrying. The .50 is the same recording dropped a tone and
    # given more bottom end, which is roughly what the larger case actually does to it.
    "gun/magnum":  ("0438", 0.00, 1.20, ("highpass=f=80", "aecho=0.7:0.5:70|150:0.26|0.13"), 1.00, 1.0),
    "gun/deagle":  ("0438", 0.00, 1.35, ("lowpass=f=8000", "aecho=0.75:0.55:85|175:0.30|0.16"),
                    0.90, 1.0),
    # The second rifle take, so the AK and the M4 are not the same file at a different volume. They
    # were recorded minutes apart and the difference is small, which is exactly right: two rifles are
    # two rifles, not two universes.
    "gun/ak":      ("2854", 0.05, 1.15, ("lowpass=f=9500", "aecho=0.7:0.5:80|150:0.28|0.14"),
                    0.95, 1.0),
}

# The same shots heard from a long way off: almost no high end left, and a long slap off the landscape.
FAR = ("lowpass=f=520", "aecho=0.9:0.7:180|380|620:0.45|0.30|0.18", "volume=3.0")

# The mechanical sounds. Real recordings of a real slide and a real magazine, which is not something
# anybody was ever going to synthesise convincingly.
MECHANICAL = {
    "gun/mag_out": ("1990", 0.40, 0.44, ("highpass=f=200",), 0.92, 0.85),
    "gun/mag_in":  ("1988", 0.30, 0.46, ("highpass=f=160",), 1.00, 0.90),
    "gun/bolt":    ("1985", 0.10, 0.36, ("highpass=f=240",), 1.00, 0.85),
    "gun/pump":    ("1984", 0.11, 1.50, ("highpass=f=180",), 0.95, 0.85),
    "gun/dry":     ("1986", 0.06, 0.16, ("highpass=f=400",), 1.06, 0.70),
    "gun/shell":   ("1357", 0.02, 0.70, ("highpass=f=700",), 1.00, 0.55),
}


def main():
    try:
        subprocess.run([FFMPEG, "-version"], capture_output=True, check=True)
    except Exception:
        sys.exit("ffmpeg not found - install it or fix the path at the top of this file")

    fetch()
    made = []
    total = 0

    for name, (source, start, length, filters, shift, headroom) in SHOTS.items():
        total += render(name, source, start, length, filters, shift, headroom)
        made.append(name)
        # Its distant twin, cut from the same recording so the two are unmistakably the same weapon.
        total += render(name + "_far", source, start, min(2.4, length + 0.9), FAR, shift, 0.8)
        made.append(name + "_far")

    for name, (source, start, length, filters, shift, headroom) in MECHANICAL.items():
        total += render(name, source, start, length, filters, shift, headroom)
        made.append(name)

    for name in sorted(made):
        print("  %-22s %7d bytes" % (name, os.path.getsize(os.path.join(SOUNDS, name + ".ogg"))))

    # Anything already in the sounds folder that this script did not make is left alone: the medicine,
    # the bunker and the infected are still built elsewhere.
    definitions = {}
    for root, ignored, files in os.walk(SOUNDS):
        for filename in files:
            if not filename.endswith(".ogg"):
                continue
            key = os.path.relpath(os.path.join(root, filename), SOUNDS)
            key = key.replace("\\", "/")[:-4]
            definitions[key.replace("/", ".")] = {
                "category": "player",
                "sounds": [{"name": "asuracraft:" + key, "stream": False}],
            }
    with io.open(os.path.join(PACK, "assets", "asuracraft", "sounds.json"), "w",
                 encoding="utf-8") as out:
        json.dump(definitions, out, ensure_ascii=False, indent=2)

    credits = (
        "AsuraCraft resource pack - sound credits\n\n"
        "The gunshots and mechanical weapon sounds in assets/asuracraft/sounds/gun are edited from\n"
        "recordings published by BigSoundBank (https://bigsoundbank.com) under CC0 1.0 Universal\n"
        "(public domain dedication): free for any use, commercial included, no attribution required.\n"
        "Credited here regardless.\n\n"
        + "".join("  %-6s %s\n" % (sid, what) for sid, what in SOURCE_FILES.items())
        + "\nEditing - trimming, pitch shifting, filtering, echo and normalisation - is done by\n"
          "make_sounds.py in this repository with ffmpeg. Re-run it to rebuild the set.\n\n"
          "Everything else under assets/asuracraft/sounds (medicine, building, the infected) is\n"
          "synthesised by make_extra_sounds.py and is not taken from any recording.\n"
    )
    with io.open(os.path.join(HERE, "CREDITS.txt"), "w", encoding="utf-8") as out:
        out.write(credits)

    print("sounds  %d gun files from real recordings, %.1f KB" % (len(made), total / 1024.0))


if __name__ == "__main__":
    main()
