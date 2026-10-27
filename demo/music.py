"""An upbeat, bright background track, generated rather than downloaded, so it carries no licence.

    python3 music.py 300 bed.wav        # seconds, output

124 BPM in D major, I–V–vi–IV (D → A → Bm → G), one chord a bar. Four-on-the-floor kick with a
light sidechain pump on the chords, claps on two and four, open hi-hats on the off-beats and a
sixteenth-note shaker; an octave-bouncing bass, off-beat chord stabs and a marimba-like hook that
plays every other eight bars. Each eight bars ends with a short snare fill into a crash. Opens with
stabs and hook only, the beat drops in after four bars, and it fades out. Mixed to sit under
narration (the voice ducks it further). Needs numpy.
"""

from __future__ import annotations

import sys
import wave

import numpy as np

RATE = 44100
BPM = 124
BEAT = 60 / BPM
BAR = 4 * BEAT
CHORDS = [  # MIDI: bass root, chord tones
    (38, [62, 66, 69, 74]),   # D
    (45, [61, 64, 69, 73]),   # A
    (47, [62, 66, 71, 74]),   # Bm
    (43, [62, 67, 71, 74]),   # G
]
# The hook: (beat within a two-bar phrase, semitones above D5, length in beats), D major pentatonic.
HOOK = [(0, 0, .5), (.5, 4, .5), (1, 7, .75), (2, 9, .5), (2.5, 7, .5), (3, 4, 1),
        (4, 2, .5), (4.5, 4, .5), (5, 7, .5), (5.5, 9, .5), (6, 12, .75), (7, 9, 1)]
rng = np.random.default_rng(7)


def hz(note: float) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def place(out: np.ndarray, at: float, sound: np.ndarray) -> None:
    s = int(at * RATE)
    if s >= len(out):
        return
    n = min(len(sound), len(out) - s)
    out[s:s + n] += sound[:n]


def env(n: int, attack: float, decay: float) -> np.ndarray:
    t = np.arange(n) / RATE
    return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t * decay)


def stab(notes: list[int], length: float = 0.22) -> np.ndarray:
    """A short, bright chord: detuned saw-ish partials, quick decay."""
    n = int(length * RATE)
    t = np.arange(n) / RATE
    out = np.zeros(n)
    for note in notes:
        for d in (-0.08, 0.08):
            f = hz(note + d)
            out += sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 6))
    return out * env(n, 0.003, 11) / (len(notes) * 4)


def marimba(note: float, length: float) -> np.ndarray:
    n = int(max(length, 0.3) * RATE)
    t = np.arange(n) / RATE
    f = hz(note)
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t * 30)
    return tone * env(n, 0.002, 6)


def bass(note: float, length: float) -> np.ndarray:
    n = int(length * RATE)
    t = np.arange(n) / RATE
    f = hz(note)
    tone = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)
    return tone * env(n, 0.005, 5) * np.clip((length - t) / 0.02, 0, 1)


def pad(notes: list[int], length: float) -> np.ndarray:
    n = int(length * RATE)
    t = np.arange(n) / RATE
    out = sum(np.sin(2 * np.pi * hz(note - 12 + d) * t) for note in notes for d in (-0.06, 0.06))
    return out * np.clip(t / 0.2, 0, 1) * np.clip((length - t) / 0.3, 0, 1) / (len(notes) * 2)


def kick() -> np.ndarray:
    n = int(0.3 * RATE)
    t = np.arange(n) / RATE
    freq = 48 + 110 * np.exp(-t * 35)
    return np.sin(2 * np.pi * np.cumsum(freq) / RATE) * np.exp(-t * 10)


def noise_hit(length: float, decay: float, bright: int) -> np.ndarray:
    n = int(length * RATE)
    x = rng.standard_normal(n)
    x = x - np.convolve(x, np.ones(bright) / bright, mode="same")
    return x * env(n, 0.001, decay)


def bed(seconds: float) -> np.ndarray:
    total = int(seconds * RATE)
    music, drums, low = np.zeros(total), np.zeros(total), np.zeros(total)
    k, clap, ohat, shaker = kick(), noise_hit(.2, 20, 6) * .55, noise_hit(.18, 18, 2) * .22, noise_hit(.04, 90, 2) * .12
    snare, crash = noise_hit(.15, 28, 4) * .35, noise_hit(1.6, 2.2, 2) * .18
    pump = np.ones(total)
    bars = int(np.ceil(seconds / BAR))
    for b in range(bars):
        start = b * BAR
        root, notes = CHORDS[b % len(CHORDS)]
        beat_in = b >= 4
        place(music, start, pad(notes, BAR + 0.1) * 0.5)
        for i in range(4):  # off-beat stabs
            place(music, start + (i + 0.5) * BEAT, stab(notes))
        if (b // 8) % 2 == 1 or b < 4:  # the hook, every other eight bars (and in the intro)
            phrase = (b % 2) * 4
            for at, step, length in HOOK:
                if phrase <= at < phrase + 4:
                    place(music, start + (at - phrase) * BEAT, marimba(74 + step, length * BEAT) * 0.45)
        if beat_in:
            for i in range(8):  # bass bounces between root and octave on eighths
                place(low, start + i * BEAT / 2, bass(root + (12 if i % 2 else 0), BEAT * 0.45) * (1 if i % 2 == 0 else .7))
            for i in range(4):
                at = start + i * BEAT
                place(drums, at, k)
                place(drums, at + BEAT / 2, ohat)
                if i in (1, 3):
                    place(drums, at, clap)
                s = int(at * RATE)  # the chords duck under each kick
                n = min(int(BEAT * RATE), total - s)
                if n > 0:
                    pump[s:s + n] = np.minimum(pump[s:s + n], 0.55 + 0.45 * np.clip(np.arange(n) / (0.6 * BEAT * RATE), 0, 1))
            for i in range(16):
                place(drums, start + i * BEAT / 4, shaker * (1 if i % 2 else .6))
            if b % 8 == 7:  # a fill into the next section
                for i in range(4):
                    place(drums, start + 3 * BEAT + i * BEAT / 4, snare * (0.6 + 0.15 * i))
            if b % 8 == 0:
                place(drums, start, crash)
        elif b == 3:  # the drop: a rising fill into bar five
            for i in range(8):
                place(drums, start + 2 * BEAT + i * BEAT / 4, snare * (0.3 + 0.1 * i))
    mix = 0.55 * music * pump + 0.6 * low + 0.5 * drums
    d = int(BEAT * 0.75 * RATE)  # dotted-eighth echo on the melodic parts only
    echo = np.zeros(total)
    echo[d:] = (music * pump)[:-d] * 0.15
    mix += echo
    fade_in, fade_out = int(1.0 * RATE), int(4 * RATE)
    mix[:fade_in] *= np.linspace(0, 1, fade_in)
    mix[-fade_out:] *= np.linspace(1, 0, fade_out)
    mix /= np.max(np.abs(mix)) + 1e-9
    shift = int(0.012 * RATE)
    right = np.concatenate([np.zeros(shift), mix[:-shift]])
    return np.stack([mix, 0.9 * right + 0.1 * mix], axis=1) * 0.85


def write(path: str, audio: np.ndarray) -> None:
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    write(sys.argv[2], bed(float(sys.argv[1])))
