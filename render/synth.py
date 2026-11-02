"""Python driver for the C++ renderer.

Builds the renderer config for Norm's Generation D (from the calibrated
impedance-model geometry), writes control scripts, renders WAVs, and
measures the result with analysis.pitch.

    python -m render.synth scale            # two-octave scale -> out/scale.wav + pitch table
    python -m render.synth sweep D          # breath sweep on one fingering
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "build/render"
OUT = ROOT / "out"

FINGERINGS = {  # standard D whistle, first-register names
    "D": "xxxxxx", "E": "xxxxxo", "F#": "xxxxoo", "G": "xxxooo",
    "A": "xxoooo", "B": "xooooo", "C#": "oooooo", "C": "oxxooo", "D2": "oxxxxx",
}


def build() -> None:
    src = ROOT / "render/render.cpp"
    hdr = ROOT / "dsp/whistle.hpp"
    if not BIN.exists() or BIN.stat().st_mtime < max(src.stat().st_mtime, hdr.stat().st_mtime):
        BIN.parent.mkdir(exist_ok=True)
        subprocess.run(["g++", "-std=c++17", "-O2", "-o", str(BIN), str(src)], check=True)


def generation_d_config(**overrides) -> dict:
    """Geometry from the calibrated impedance model (acoustics.calibrate_generation_d)."""
    from acoustics.calibrate_generation_d import BORE, DIA, EDGE, WINDOW, make

    top_from_foot, window_scale = 263.4, 0.92   # calibration from both diatonic takes
    w = make(top_from_foot, window_scale)
    cfg = {
        "sample_rate": 96000, "temp_c": 30.0, "bore_diameter": BORE, "length": w.bore_length,
        "window_length": WINDOW[0], "window_width": WINDOW[1], "window_wall": 2.0,
        "window_scale": window_scale,
    }
    for i, h in enumerate(w.holes, 1):
        cfg[f"hole{i}_pos"] = h.position
        cfg[f"hole{i}_dia"] = h.diameter
        cfg[f"hole{i}_wall"] = h.chimney
    cfg.update(overrides)
    return cfg


def write_config(cfg: dict, path: Path) -> None:
    path.write_text("".join(f"{k} = {v}\n" for k, v in cfg.items()))


def openness(pattern: str) -> list[float]:
    return [{"x": 0.0, "o": 1.0, "h": 0.5}[c] for c in pattern]


def note_rows(t0: float, pattern: str, breath: float, hold: float, attack: float = 0.04,
              gap: float = 0.25, overshoot: float = 1.0) -> tuple[list[list[float]], float]:
    """One tongued note. `overshoot` > 1 adds a brief breath spike at the attack,
    the way players kick the second octave in."""
    o = openness(pattern)
    rows = [[t0] + o + [0.0], [t0 + attack] + o + [breath * overshoot],
            [t0 + attack + 0.03] + o + [breath], [t0 + hold] + o + [breath],
            [t0 + hold + attack] + o + [0.0], [t0 + hold + gap] + o + [0.0]]
    return rows, t0 + hold + gap


def write_control(rows: list[list[float]], path: Path) -> None:
    lines = ["t,o1,o2,o3,o4,o5,o6,breath"] + [",".join(f"{v:.5f}" for v in r) for r in rows]
    path.write_text("\n".join(lines) + "\n")


def render(cfg: dict, rows: list[list[float]], name: str) -> Path:
    build()
    OUT.mkdir(exist_ok=True)
    c, k, w = OUT / f"{name}.cfg", OUT / f"{name}.csv", OUT / f"{name}.wav"
    write_config(cfg, c)
    write_control(rows, k)
    r = subprocess.run([str(BIN), str(c), str(k), str(w)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr)
    return w


# Breath (fraction of 1500 Pa) at the middle of each fingering's register range,
# from the register map in docs/results/2026-11-01-octave-break.md. Like a real
# whistle, shorter fingerings and the second octave need more breath.
BREATH = {"D": 0.10, "E": 0.17, "F#": 0.25, "G": 0.28, "A": 0.35, "B": 0.47, "C#": 0.55,
          "D'": 0.45, "E'": 0.50, "F#'": 0.75, "G'": 0.85, "A'": 0.90, "B'": 1.00, "C#'": 1.10}


def scale_rows(breath1: float | None = None, breath2: float | None = None, hold: float = 1.0, kick: float = 1.0):
    """Two-octave scale. With breath1/breath2 None, each note uses its BREATH entry."""
    rows, t = [], 0.0
    first = ("D", "E", "F#", "G", "A", "B", "C#")
    plan = [(FINGERINGS[n], breath1 if breath1 is not None else BREATH[n], n, 1.0) for n in first]
    plan += [(FINGERINGS["D2"], breath2 if breath2 is not None else BREATH["D'"], "D'", kick)] + \
            [(FINGERINGS[n], breath2 if breath2 is not None else BREATH[n + "'"], n + "'", kick) for n in first[1:]]
    labels = []
    for pattern, b, label, ov in plan:
        r, t1 = note_rows(t, pattern, b, hold, overshoot=ov)
        labels.append((label, pattern, t, t1))
        rows += r
        t = t1
    return rows, labels


def main() -> None:
    from analysis.pitch import held_notes, load_audio, pitch_track

    p = argparse.ArgumentParser()
    p.add_argument("what", choices=["scale", "sweep"])
    p.add_argument("note", nargs="?", default="D")
    p.add_argument("--breath1", type=float, default=None, help="fixed first-octave breath (default: per-note table)")
    p.add_argument("--breath2", type=float, default=None, help="fixed second-octave breath (default: per-note table)")
    p.add_argument("--kick", type=float, default=1.0, help="second-octave attack overshoot (1 = none)")
    p.add_argument("--set", nargs="*", default=[], help="config overrides key=value")
    a = p.parse_args()
    overrides = {k: float(v) for k, v in (s.split("=") for s in a.set)}
    cfg = generation_d_config(**overrides)

    if a.what == "scale":
        rows, labels = scale_rows(a.breath1, a.breath2, kick=a.kick)
        wav = render(cfg, rows, "scale")
    else:
        pat = FINGERINGS[a.note]
        o = openness(pat)
        rows = [[0.0] + o + [0.0], [0.05] + o + [0.08], [6.0] + o + [1.0], [6.05] + o + [0.0], [6.3] + o + [0.0]]
        wav = render(cfg, rows, f"sweep_{a.note}")
    x, sr = load_audio(str(wav))
    print(f"# {wav.name}")
    for h in held_notes(pitch_track(x, sr, fmin=300, fmax=5000), min_dur=0.2):
        print(f"{h.start:6.2f}-{h.end:6.2f}  {h.hz:8.1f} Hz  {h.nearest:>4} {h.cents_off:+6.1f}")


if __name__ == "__main__":
    main()
