# -*- coding: utf-8 -*-
"""The sounds that are not gunfire: medicine, building, and the infected.

These are still synthesised, for the honest reason that there is no public-domain recording of a
bandage being wrapped or of a thing that does not exist. The weapons are a different matter and are
built from real recordings by make_sounds.py; nothing in this file pretends otherwise.

A note on the infected, which are the weakest sounds here and are known to be: a throat is far harder
to fake than a click, and a growl built from a squared-off sine reads as a machine rather than as an
animal. They are next in line to be replaced with recorded material.
"""
import io
import os
import subprocess
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SOUNDS = os.path.join(HERE, "pack", "assets", "asuracraft", "sounds")
RATE = 44100

FFMPEG = "ffmpeg"
for candidate in (
    r"C:\Users\dc2\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe",
):
    if os.path.exists(candidate):
        FFMPEG = candidate


def seconds(length):
    return np.arange(int(length * RATE)) / float(RATE)


def noise(length, seed):
    return np.random.default_rng(seed).standard_normal(int(length * RATE))


def decay(length, tau, shape=1.0):
    return np.exp(-(seconds(length) / tau) ** shape)


def lowpass(signal, cutoff):
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
    t = seconds(length)
    wobble = 1.0 + 0.004 * np.sin(2 * np.pi * 7.3 * t)
    return np.sin(2 * np.pi * frequency * wobble * t) * np.exp(-t / tau)


def sweep(length, start, end, tau):
    t = seconds(length)
    frequency = end + (start - end) * np.exp(-t / (length * 0.35))
    return np.sin(2 * np.pi * np.cumsum(frequency) / RATE) * np.exp(-t / tau)


def place(target, piece, at, gain=1.0):
    start = int(at * RATE)
    end = min(len(target), start + len(piece))
    target[start:end] += piece[:end - start] * gain
    return target


def normalise(signal, peak=0.88):
    signal = np.tanh(signal * 1.25)
    top = float(np.max(np.abs(signal))) or 1.0
    return signal * (peak / top)


def click(seed, brightness, tau=0.004, gain=1.0):
    return highpass(noise(0.02, seed) * decay(0.02, tau), brightness) * gain


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
    out = place(out, lowpass(noise(0.30, seed + 10), 700.0) * decay(0.30, 0.10, 1.5), 0.55, 0.9)
    out = place(out, sweep(0.25, 300.0, 120.0, 0.09), 0.55, 0.35)
    return normalise(out, 0.55)


def injector(seed=150):
    """A hiss and a click: the first-aid kit, and anything else that goes in rather than on."""
    out = np.zeros(int(0.9 * RATE))
    out = place(out, highpass(noise(0.45, seed), 2400.0) * decay(0.45, 0.20, 1.2), 0.05, 0.45)
    out = place(out, click(seed + 1, 3000.0, 0.003), 0.00, 0.9)
    out = place(out, click(seed + 2, 2200.0, 0.004), 0.52, 0.7)
    return normalise(out, 0.6)


def drink(seed=160):
    """A can opening and three swallows - the energy drink."""
    out = np.zeros(int(1.5 * RATE))
    out = place(out, click(seed, 3200.0, 0.003), 0.0, 1.0)
    out = place(out, highpass(noise(0.9, seed + 1), 3600.0) * decay(0.9, 0.45, 1.1), 0.02, 0.22)
    for index, at in enumerate((0.30, 0.62, 0.94)):
        out = place(out, lowpass(noise(0.22, seed + 5 + index), 620.0) * decay(0.22, 0.075, 1.5),
                    at, 0.8)
        out = place(out, sweep(0.18, 260.0 - index * 30, 110.0, 0.07), at, 0.3)
    return normalise(out, 0.55)


def bunker(seed=200):
    """Something heavy being dropped and settling - a wall going up."""
    out = np.zeros(int(1.0 * RATE))
    out = place(out, sweep(0.5, 150.0, 45.0, 0.16), 0.0, 1.0)
    out = place(out, lowpass(noise(0.35, seed) * decay(0.35, 0.09, 0.9), 1400.0), 0.0, 0.7)
    out = place(out, click(seed + 1, 1200.0, 0.010), 0.26, 0.5)
    out = place(out, ring(0.30, 320.0, 0.070, seed + 1), 0.26, 0.25)
    return normalise(out, 0.85)


def zombie(seed, low, length, growl):
    """A throat rather than a voice: a rough low tone, breath over it, no words in it anywhere."""
    t = seconds(length)
    rasp = np.sin(2 * np.pi * low * (1 + 0.22 * np.sin(2 * np.pi * growl * t)) * t)
    rasp = np.sign(rasp) * np.abs(rasp) ** 0.6
    envelope = np.exp(-((t - length * 0.35) / (length * 0.40)) ** 2)
    breath = lowpass(noise(length, seed), 1500.0) * envelope
    return normalise(rasp * envelope * 0.7 + breath * 0.5, 0.7)


def write(name, samples):
    path = os.path.join(SOUNDS, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    raw = np.clip(samples, -1.0, 1.0)
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
    made = {
        "item/bandage": bandage(),
        "item/pills": pills(),
        "item/injector": injector(),
        "item/drink": drink(),
        "build/bunker": bunker(),
        "zombie/idle": zombie(300, 96.0, 1.6, 3.1),
        "zombie/hurt": zombie(310, 138.0, 0.7, 7.0),
        "zombie/death": zombie(320, 78.0, 1.9, 2.2),
        "zombie/chase": zombie(330, 118.0, 1.1, 5.4),
    }
    for name, samples in sorted(made.items()):
        print("  %-20s %7d bytes" % (name, write(name, samples)))
    print("extra   %d files (run make_sounds.py afterwards to rewrite sounds.json)" % len(made))


if __name__ == "__main__":
    main()
