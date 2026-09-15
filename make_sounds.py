# -*- coding: utf-8 -*-
"""Builds the WarZ sound set from scratch, so every sound in it is ours.

The first version of this file cut clips out of a public-domain recording, because there was no audio
encoder on the machine. There is one now, and cutting was always the weaker idea: one recording trimmed
to five lengths gives five versions of the same bang, and a shotgun that sounds like a pistol played
slowly is the thing that makes a gun server feel cheap.

So nothing is sampled here. A gunshot is built the way a game's sound designer layers one:

  crack   two milliseconds of full-band noise - the supersonic snap, and the part the ear uses to judge
          how close it was
  body    filtered noise under a fast exponential decay - the muzzle blast itself, darker and longer on
          a big cartridge, bright and short on a small one
  thump   a sine falling from a hundred-odd hertz to forty - the chest pressure, and what separates a
          shotgun from a pistol more than anything else
  tail    a few slapback echoes and a long, quiet, low-passed decay, which is the ground and the trees
          answering back; a sniper gets a long one, a submachine gun almost none

The mechanical sounds are the same trick with different numbers: a magazine release is a small bright
click and a metal ring, a magazine seating is a click with a low thud under it, a bolt is two clicks a
few hundredths of a second apart. Tearing a bandage is noise under a slow envelope. None of it is
recorded, so none of it can be anybody else's.

Everything is written as mono. That is not laziness: Minecraft plays a stereo file flat in both ears
with no position at all, so a stereo gunshot comes from everywhere at once - useless in a game whose
whole point is working out which direction it came from.
"""
import io
import json
import os
import subprocess
import sys
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = os.path.join(HERE, "pack")
SOUNDS = os.path.join(PACK, "assets", "asuracraft", "sounds")
RATE = 44100

FFMPEG = "ffmpeg"
for candidate in (
    r"C:\Users\dc2\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe",
):
    if os.path.exists(candidate):
        FFMPEG = candidate


# ---------------------------------------------------------------- the pieces a sound is made of
def seconds(length):
    return np.arange(int(length * RATE)) / float(RATE)


def noise(length, seed):
    return np.random.default_rng(seed).standard_normal(int(length * RATE))


def decay(length, tau, shape=1.0):
    """An exponential fall. `shape` below one holds the level up before letting it go."""
    t = seconds(length)
    return np.exp(-(t / tau) ** shape)


def lowpass(signal, cutoff):
    """One pole, run forwards. Crude, and exactly the right amount of crude for this."""
    alpha = 1.0 - np.exp(-2.0 * np.pi * cutoff / RATE)
    out = np.empty_like(signal)
    running = 0.0
    for index, value in enumerate(signal):
        running += alpha * (value - running)
        out[index] = running
    return out


def highpass(signal, cutoff):
    return signal - lowpass(signal, cutoff)


def ring(length, frequency, tau, seed=0):
    """A struck piece of metal: a damped sine, detuned a little so it is not a test tone."""
    t = seconds(length)
    wobble = 1.0 + 0.004 * np.sin(2 * np.pi * 7.3 * t)
    return np.sin(2 * np.pi * frequency * wobble * t) * np.exp(-t / tau)


def sweep(length, start, end, tau):
    """A sine falling from one frequency to another - the pressure wave of a muzzle blast."""
    t = seconds(length)
    frequency = end + (start - end) * np.exp(-t / (length * 0.35))
    phase = 2 * np.pi * np.cumsum(frequency) / RATE
    return np.sin(phase) * np.exp(-t / tau)


def place(target, piece, at, gain=1.0):
    start = int(at * RATE)
    end = min(len(target), start + len(piece))
    target[start:end] += piece[:end - start] * gain
    return target


def normalise(signal, peak=0.92):
    signal = np.tanh(signal * 1.25)                 # soft clip, so the transient stays loud but clean
    top = float(np.max(np.abs(signal))) or 1.0
    return signal * (peak / top)


# ---------------------------------------------------------------- the sounds themselves
def gunshot(seed, length, body_tau, body_cut, thump_from, thump_tau, tail, slaps, crack=1.0):
    out = np.zeros(int(length * RATE))

    # The snap. Two milliseconds, full band, and the loudest thing in the file.
    out = place(out, highpass(noise(0.004, seed) * decay(0.004, 0.0012), 1800.0), 0.0, 1.4 * crack)

    # The blast. Noise, darkened to taste, under a fast decay.
    body = lowpass(noise(length * 0.6, seed + 1), body_cut) * decay(length * 0.6, body_tau, 0.85)
    out = place(out, body, 0.001, 1.0)

    # The pressure. What a big round has and a small one does not.
    out = place(out, sweep(min(length, 0.4), thump_from, 42.0, thump_tau), 0.0, 0.85)

    # The ground answering. A few discrete slaps, then a long quiet wash.
    for index, (delay, gain) in enumerate(slaps):
        echo = lowpass(noise(0.10, seed + 10 + index) * decay(0.10, 0.030), 2200.0)
        out = place(out, echo, delay, gain)
    if tail > 0:
        wash = lowpass(noise(length * 0.9, seed + 30) * decay(length * 0.9, tail, 0.8), 900.0)
        out = place(out, wash, 0.02, 0.30)
    return normalise(out)


def click(seed, brightness, tau=0.004, gain=1.0):
    return highpass(noise(0.02, seed) * decay(0.02, tau), brightness) * gain


def magazine_out(seed=70):
    """A catch releasing, then a magazine falling away and knocking about on the way."""
    out = np.zeros(int(0.55 * RATE))
    out = place(out, click(seed, 2600.0, 0.003), 0.00, 1.0)
    out = place(out, ring(0.25, 1180.0, 0.055, seed), 0.005, 0.30)
    out = place(out, ring(0.25, 2360.0, 0.030, seed), 0.005, 0.16)
    out = place(out, click(seed + 1, 1800.0, 0.006), 0.13, 0.55)   # it clears the well
    out = place(out, click(seed + 2, 1400.0, 0.008), 0.29, 0.40)   # and hits the floor
    out = place(out, ring(0.20, 640.0, 0.045, seed + 2), 0.29, 0.22)
    return normalise(out, 0.72)


def magazine_in(seed=80):
    """Pushed up the well - a scrape - and seated, which is a click with weight under it."""
    out = np.zeros(int(0.45 * RATE))
    scrape = lowpass(noise(0.09, seed), 3200.0) * decay(0.09, 0.045, 0.6)
    out = place(out, scrape, 0.0, 0.30)
    out = place(out, click(seed + 1, 2200.0, 0.004), 0.10, 1.0)
    out = place(out, sweep(0.12, 190.0, 70.0, 0.030), 0.10, 0.55)
    out = place(out, ring(0.15, 880.0, 0.022, seed + 1), 0.10, 0.18)
    return normalise(out, 0.78)


def bolt(seed=90):
    """Drawn back and let go: two hard clicks with a short metallic slide between them."""
    out = np.zeros(int(0.40 * RATE))
    out = place(out, click(seed, 2400.0, 0.004), 0.00, 0.9)
    slide = lowpass(noise(0.07, seed + 1), 4000.0) * decay(0.07, 0.035, 0.7)
    out = place(out, slide, 0.01, 0.22)
    out = place(out, click(seed + 2, 2000.0, 0.005), 0.12, 1.0)
    out = place(out, ring(0.12, 1500.0, 0.020, seed + 2), 0.12, 0.20)
    return normalise(out, 0.80)


def pump(seed=100):
    """A shotgun's forend: forward and back, heavier and slower than a rifle bolt."""
    out = np.zeros(int(0.55 * RATE))
    for at, gain, cut in ((0.00, 0.9, 1600.0), (0.20, 1.0, 1300.0)):
        out = place(out, click(seed + int(at * 100), cut, 0.007), at, gain)
        out = place(out, ring(0.18, 520.0, 0.035, seed), at, 0.24)
        out = place(out, lowpass(noise(0.10, seed + 5) * decay(0.10, 0.045, 0.7), 2600.0), at + 0.01, 0.22)
    return normalise(out, 0.80)


def shell(seed=110):
    """Brass on concrete. Small, bright, and the detail everybody notices."""
    out = np.zeros(int(0.5 * RATE))
    for index, (at, gain) in enumerate(((0.00, 1.0), (0.11, 0.6), (0.19, 0.35), (0.26, 0.2))):
        out = place(out, ring(0.12, 2400.0 + index * 260, 0.018, seed + index), at, gain)
        out = place(out, click(seed + 20 + index, 3400.0, 0.002), at, gain * 0.5)
    return normalise(out, 0.55)


def dry_fire(seed=120):
    """The hammer falling on nothing, which is how a player learns the magazine is empty."""
    out = np.zeros(int(0.15 * RATE))
    out = place(out, click(seed, 2800.0, 0.003), 0.0, 1.0)
    out = place(out, ring(0.08, 1900.0, 0.012, seed), 0.0, 0.25)
    return normalise(out, 0.6)


def bandage(seed=130):
    """Cloth torn, then wound - a long breathy rustle rather than anything percussive."""
    out = np.zeros(int(1.30 * RATE))
    tear = highpass(noise(0.35, seed), 900.0) * (decay(0.35, 0.22, 1.6) * (1 - decay(0.35, 0.02)))
    out = place(out, tear, 0.0, 0.8)
    for index, at in enumerate((0.45, 0.72, 0.99)):
        wrap = lowpass(noise(0.22, seed + index + 1), 5200.0) * decay(0.22, 0.060, 1.4)
        out = place(out, wrap, at, 0.55 - index * 0.08)
    return normalise(out, 0.55)


def pills(seed=140):
    """A bottle shaken, a lid, and a swallow."""
    out = np.zeros(int(1.10 * RATE))
    for index, at in enumerate((0.00, 0.07, 0.13, 0.20)):
        out = place(out, ring(0.06, 3200.0 + index * 400, 0.008, seed + index), at, 0.5)
    out = place(out, click(seed + 9, 2400.0, 0.004), 0.34, 0.7)
    gulp = lowpass(noise(0.30, seed + 10), 700.0) * decay(0.30, 0.10, 1.5)
    out = place(out, gulp, 0.55, 0.9)
    out = place(out, sweep(0.25, 300.0, 120.0, 0.09), 0.55, 0.35)
    return normalise(out, 0.55)


def injector(seed=150):
    """A hiss and a click: the first-aid kit, and anything else that goes in rather than on."""
    out = np.zeros(int(0.9 * RATE))
    hiss = highpass(noise(0.45, seed), 2400.0) * decay(0.45, 0.20, 1.2)
    out = place(out, hiss, 0.05, 0.45)
    out = place(out, click(seed + 1, 3000.0, 0.003), 0.00, 0.9)
    out = place(out, click(seed + 2, 2200.0, 0.004), 0.52, 0.7)
    return normalise(out, 0.6)


def drink(seed=160):
    """A can opening and three swallows - the energy drink."""
    out = np.zeros(int(1.5 * RATE))
    out = place(out, click(seed, 3200.0, 0.003), 0.0, 1.0)
    fizz = highpass(noise(0.9, seed + 1), 3600.0) * decay(0.9, 0.45, 1.1)
    out = place(out, fizz, 0.02, 0.22)
    for index, at in enumerate((0.30, 0.62, 0.94)):
        swallow = lowpass(noise(0.22, seed + 5 + index), 620.0) * decay(0.22, 0.075, 1.5)
        out = place(out, swallow, at, 0.8)
        out = place(out, sweep(0.18, 260.0 - index * 30, 110.0, 0.07), at, 0.3)
    return normalise(out, 0.55)


def zombie(seed, low, length, growl):
    """A throat rather than a voice: a rough low tone, breath over it, no words in it anywhere."""
    t = seconds(length)
    rasp = np.sin(2 * np.pi * low * (1 + 0.22 * np.sin(2 * np.pi * growl * t)) * t)
    rasp = np.sign(rasp) * np.abs(rasp) ** 0.6                 # squared off, so it snarls
    envelope = np.exp(-((t - length * 0.35) / (length * 0.40)) ** 2)
    breath = lowpass(noise(length, seed), 1500.0) * envelope
    return normalise(rasp * envelope * 0.7 + breath * 0.5, 0.7)


def bunker(seed=200):
    """Something heavy being dropped and settling - a wall going up."""
    out = np.zeros(int(1.0 * RATE))
    out = place(out, sweep(0.5, 150.0, 45.0, 0.16), 0.0, 1.0)
    out = place(out, lowpass(noise(0.35, seed) * decay(0.35, 0.09, 0.9), 1400.0), 0.0, 0.7)
    out = place(out, click(seed + 1, 1200.0, 0.010), 0.26, 0.5)
    out = place(out, ring(0.30, 320.0, 0.070, seed + 1), 0.26, 0.25)
    return normalise(out, 0.85)


# Each gun gets its own numbers rather than its own recording, which is what makes them tell apart.
GUNS = {
    #            seed  len   bodyτ  cut     thump  thumpτ tail   slapbacks
    "pistol":  (11,   0.42, 0.016, 5200.0, 150.0, 0.045, 0.16, ((0.055, 0.22), (0.105, 0.12))),
    "smg":     (21,   0.34, 0.012, 6000.0, 135.0, 0.034, 0.10, ((0.045, 0.18), (0.085, 0.09))),
    "rifle":   (31,   0.60, 0.022, 4200.0, 175.0, 0.060, 0.26, ((0.070, 0.28), (0.135, 0.16),
                                                                (0.210, 0.09))),
    "sniper":  (41,   0.95, 0.034, 3000.0, 210.0, 0.090, 0.45, ((0.090, 0.34), (0.175, 0.22),
                                                                (0.280, 0.14), (0.400, 0.08))),
    "shotgun": (51,   0.72, 0.040, 2200.0, 230.0, 0.075, 0.30, ((0.080, 0.30), (0.155, 0.18),
                                                                (0.240, 0.10))),
}


def write(name, samples):
    """One sound, as a wav, then handed to ffmpeg to become the ogg the game reads."""
    path = os.path.join(SOUNDS, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    raw = np.clip(samples, -1.0, 1.0)
    # A two millisecond fade at each end. Without it the file starts and stops on a step, and a step is
    # a click the player hears on every single shot.
    edge = int(0.002 * RATE)
    if len(raw) > 2 * edge:
        raw[:edge] *= np.linspace(0, 1, edge)
        raw[-edge:] *= np.linspace(1, 0, edge)
    with wave.open(path + ".wav", "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes((raw * 32767).astype("<i2").tobytes())
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", path + ".wav",
                    "-c:a", "libvorbis", "-q:a", "5", "-ac", "1", path + ".ogg"], check=True)
    os.remove(path + ".wav")
    return os.path.getsize(path + ".ogg")


def main():
    if not os.path.exists(FFMPEG) and FFMPEG == "ffmpeg":
        try:
            subprocess.run([FFMPEG, "-version"], capture_output=True, check=True)
        except Exception:
            sys.exit("ffmpeg not found - install it or fix the path at the top of this file")

    made = {}
    for name, (seed, length, tau, cut, thump, thump_tau, tail, slaps) in GUNS.items():
        made["gun/" + name] = gunshot(seed, length, tau, cut, thump, thump_tau, tail, slaps)
        # A second, quieter, duller copy of the same shot: what the gun sounds like from far off, played
        # to distant players instead of the near one so a firefight can be located across a valley.
        made["gun/" + name + "_far"] = normalise(
            lowpass(made["gun/" + name], 700.0) * 1.6, 0.55)

    made["gun/mag_out"] = magazine_out()
    made["gun/mag_in"] = magazine_in()
    made["gun/bolt"] = bolt()
    made["gun/pump"] = pump()
    made["gun/shell"] = shell()
    made["gun/dry"] = dry_fire()

    made["item/bandage"] = bandage()
    made["item/pills"] = pills()
    made["item/injector"] = injector()
    made["item/drink"] = drink()
    made["build/bunker"] = bunker()

    made["zombie/idle"] = zombie(300, 96.0, 1.6, 3.1)
    made["zombie/hurt"] = zombie(310, 138.0, 0.7, 7.0)
    made["zombie/death"] = zombie(320, 78.0, 1.9, 2.2)
    made["zombie/chase"] = zombie(330, 118.0, 1.1, 5.4)

    total = 0
    for name, samples in sorted(made.items()):
        size = write(name, samples)
        total += size
        print("  %-22s %6.2fs %7d bytes" % (name, len(samples) / float(RATE), size))

    # What the server asks for by name.
    definitions = {}
    for name in made:
        # No subtitle key. A subtitle names a translation entry, and a name with nothing behind it is
        # printed raw on the screen of every player who has subtitles switched on.
        definitions[name.replace("/", ".")] = {
            "category": "player",
            "sounds": [{"name": "asuracraft:" + name, "stream": False}],
        }
    with io.open(os.path.join(PACK, "assets", "asuracraft", "sounds.json"), "w",
                 encoding="utf-8") as out:
        json.dump(definitions, out, ensure_ascii=False, indent=2)

    credits = (
        "AsuraCraft resource pack - sound credits\n\n"
        "Every sound in assets/asuracraft/sounds is synthesised by make_sounds.py in this repository.\n"
        "Nothing is sampled, recorded or taken from another work, so there is nothing to attribute and\n"
        "nothing to licence. Re-run make_sounds.py to rebuild the whole set.\n"
    )
    with io.open(os.path.join(HERE, "CREDITS.txt"), "w", encoding="utf-8") as out:
        out.write(credits)
    print("sounds  %d files, %.1f KB, all synthesised" % (len(made), total / 1024.0))


if __name__ == "__main__":
    main()
