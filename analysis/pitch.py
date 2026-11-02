"""Pitch analysis for whistle recordings.

Finds steadily held notes in a recording and reports their frequency and
cents offset from 12-TET (A4 = 440 Hz by default).

Usage:
    python -m analysis.pitch recording.wav [--a4 440] [--min-dur 0.4]

Recordings in formats soundfile can't read (m4a, mp3, ...) are converted
with ffmpeg first.
"""
from __future__ import annotations

import argparse
import math
import os
import subprocess
import tempfile
from dataclasses import dataclass

import numpy as np

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


# ---------------------------------------------------------------- utilities

def hz_to_midi(f: float, a4: float = 440.0) -> float:
    return 69.0 + 12.0 * math.log2(f / a4)


def midi_to_hz(m: float, a4: float = 440.0) -> float:
    return a4 * 2.0 ** ((m - 69.0) / 12.0)


def midi_name(m: int) -> str:
    return f"{NOTE_NAMES[m % 12]}{m // 12 - 1}"


def cents(f: float, ref: float) -> float:
    return 1200.0 * math.log2(f / ref)


def load_audio(path: str) -> tuple[np.ndarray, int]:
    """Load a recording as mono float64."""
    import soundfile as sf

    try:
        data, sr = sf.read(path, always_2d=True)
    except Exception:
        with tempfile.TemporaryDirectory() as tmp:
            wav = os.path.join(tmp, "converted.wav")
            subprocess.run(
                ["ffmpeg", "-loglevel", "error", "-y", "-i", path, wav],
                check=True,
            )
            data, sr = sf.read(wav, always_2d=True)
    return data.mean(axis=1).astype(np.float64), int(sr)


# ---------------------------------------------------------------- YIN

def yin_frame(frame: np.ndarray, sr: int, fmin: float, fmax: float,
              threshold: float = 0.1) -> tuple[float, float]:
    """Return (frequency Hz, aperiodicity 0..1) for one frame using YIN.

    Frequency is nan when no period is found.
    """
    n = len(frame)
    tau_min = max(2, int(sr / fmax))
    tau_max = min(n // 2, int(sr / fmin) + 1)
    if tau_max <= tau_min + 2:
        return float("nan"), 1.0

    # Difference function via FFT autocorrelation.
    x = frame - frame.mean()
    size = 1 << (2 * n - 1).bit_length()
    spec = np.fft.rfft(x, size)
    acf = np.fft.irfft(spec * np.conj(spec), size)[:tau_max + 1]
    energy = np.concatenate(([0.0], np.cumsum(x * x)))
    # d(tau) = sum_{j<n-tau} (x_j - x_{j+tau})^2
    taus = np.arange(tau_max + 1)
    e1 = energy[n - taus]                      # sum x_j^2, j < n - tau
    e2 = energy[n] - energy[taus]              # sum x_{j+tau}^2
    d = e1 + e2 - 2.0 * acf
    d[0] = 0.0

    # Cumulative mean normalized difference.
    cmnd = np.ones_like(d)
    running = np.cumsum(d[1:])
    with np.errstate(divide="ignore", invalid="ignore"):
        cmnd[1:] = d[1:] * np.arange(1, tau_max + 1) / np.where(running > 0, running, np.inf)

    # First dip below threshold, then walk to its local minimum.
    tau = -1
    for t in range(tau_min, tau_max):
        if cmnd[t] < threshold:
            while t + 1 < tau_max and cmnd[t + 1] < cmnd[t]:
                t += 1
            tau = t
            break
    if tau < 0:
        t = tau_min + int(np.argmin(cmnd[tau_min:tau_max]))
        if cmnd[t] > 0.35:
            return float("nan"), float(cmnd[t])
        tau = t

    # Parabolic interpolation on the difference function for sub-sample period.
    if 1 <= tau < tau_max:
        a, b, c = cmnd[tau - 1], cmnd[tau], cmnd[tau + 1]
        denom = a - 2 * b + c
        shift = 0.5 * (a - c) / denom if denom != 0 else 0.0
    else:
        shift = 0.0
    period = tau + float(np.clip(shift, -1, 1))
    return sr / period, float(cmnd[tau])


@dataclass
class Track:
    times: np.ndarray       # frame centre times, s
    freqs: np.ndarray       # Hz, nan where unvoiced
    levels: np.ndarray      # RMS, dBFS


def pitch_track(x: np.ndarray, sr: int, fmin: float = 400.0, fmax: float = 4000.0,
                frame_s: float = 0.04, hop_s: float = 0.01) -> Track:
    n = int(frame_s * sr)
    hop = int(hop_s * sr)
    times, freqs, levels = [], [], []
    for start in range(0, max(1, len(x) - n), hop):
        frame = x[start:start + n]
        rms = math.sqrt(float(np.mean(frame * frame)) + 1e-20)
        level = 20 * math.log10(rms)
        f, _ = yin_frame(frame, sr, fmin, fmax) if level > -60 else (float("nan"), 1.0)
        times.append((start + n / 2) / sr)
        freqs.append(f)
        levels.append(level)
    return Track(np.array(times), np.array(freqs), np.array(levels))


# ---------------------------------------------------------------- held notes

@dataclass
class HeldNote:
    start: float
    end: float
    hz: float
    nearest: str
    nearest_midi: int
    cents_off: float
    spread_cents: float      # interquartile range of pitch within the note
    level_db: float


def held_notes(track: Track, a4: float = 440.0, min_dur: float = 0.4,
               tolerance_cents: float = 30.0, level_floor_db: float = -45.0,
               trim_s: float = 0.1) -> list[HeldNote]:
    """Group frames into steady notes and summarize each one.

    A held note is a run of voiced frames that stays within `tolerance_cents`
    of the run's running median for at least `min_dur` seconds. `trim_s` is
    dropped from each end so attacks and releases don't bias the result.
    """
    hop = float(np.median(np.diff(track.times))) if len(track.times) > 1 else 0.01
    voiced = np.isfinite(track.freqs) & (track.levels > level_floor_db)
    midi = np.full_like(track.freqs, np.nan)
    midi[voiced] = 69 + 12 * np.log2(track.freqs[voiced] / a4)

    notes: list[HeldNote] = []
    i, n = 0, len(midi)
    while i < n:
        if not voiced[i]:
            i += 1
            continue
        j = i
        run = [midi[i]]
        while j + 1 < n and voiced[j + 1] and abs(midi[j + 1] - np.median(run)) * 100 < tolerance_cents:
            j += 1
            run.append(midi[j])
        dur = (j - i + 1) * hop
        if dur >= min_dur:
            k = int(round(trim_s / hop))
            lo, hi = i + k, j - k
            seg = midi[lo:hi + 1] if hi > lo else midi[i:j + 1]
            m = float(np.median(seg))
            hz = a4 * 2 ** ((m - 69) / 12)
            nearest = int(round(m))
            q75, q25 = np.percentile(seg, [75, 25])
            notes.append(HeldNote(
                start=float(track.times[i]), end=float(track.times[j]), hz=hz,
                nearest=midi_name(nearest), nearest_midi=nearest,
                cents_off=(m - nearest) * 100, spread_cents=float(q75 - q25) * 100,
                level_db=float(np.median(track.levels[i:j + 1])),
            ))
        i = j + 1
    return notes


def analyze_file(path: str, a4: float = 440.0, min_dur: float = 0.4,
                 fmin: float = 400.0, fmax: float = 4000.0) -> list[HeldNote]:
    x, sr = load_audio(path)
    return held_notes(pitch_track(x, sr, fmin, fmax), a4=a4, min_dur=min_dur)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("files", nargs="+")
    p.add_argument("--a4", type=float, default=440.0)
    p.add_argument("--min-dur", type=float, default=0.4)
    p.add_argument("--fmin", type=float, default=400.0)
    p.add_argument("--fmax", type=float, default=4000.0)
    args = p.parse_args()
    for path in args.files:
        print(f"# {path}")
        print(f"{'start':>7} {'end':>7} {'Hz':>9} {'note':>5} {'cents':>7} {'spread':>7} {'dB':>6}")
        for h in analyze_file(path, args.a4, args.min_dur, args.fmin, args.fmax):
            print(f"{h.start:7.2f} {h.end:7.2f} {h.hz:9.2f} {h.nearest:>5} {h.cents_off:+7.1f} "
                  f"{h.spread_cents:7.1f} {h.level_db:6.1f}")


if __name__ == "__main__":
    main()
