"""Whistle geometry (millimetres), fingering charts, pitch prediction and fitting.

Geometry convention follows docs/measuring.md: positions are measured from the
top of the bore (the block face at the window), holes are numbered 1-6 from
the mouthpiece end.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np

from . import tmm

MM = 1e-3


@dataclass
class HoleMM:
    position: float      # mm from top of bore
    diameter: float      # mm
    chimney: float       # mm (wall thickness)


@dataclass
class WhistleMM:
    bore_length: float                 # mm, top of bore (window) to foot
    bore_diameter: float               # mm (cylindrical bore)
    holes: list[HoleMM]
    window_length: float = 6.0         # mm along the axis
    window_width: float = 9.0          # mm across
    window_wall: float = 1.5           # mm
    window_corr_scale: float = 1.0     # calibration factor
    temp_c: float = 25.0

    def to_model(self):
        bore = tmm.Bore(self.bore_length * MM, [(0.0, self.bore_diameter / 2 * MM)])
        holes = [tmm.Hole(h.position * MM, h.diameter / 2 * MM, h.chimney * MM) for h in self.holes]
        window = tmm.Window(self.window_length * MM, self.window_width * MM, self.window_wall * MM,
                            self.window_corr_scale)
        return bore, holes, window, tmm.Air(self.temp_c)


@dataclass
class ChartRow:
    note: str
    midi: int
    register: int
    pattern: str
    primary: bool
    notes: str = ""


def load_chart(path: str | Path) -> list[ChartRow]:
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            rows.append(ChartRow(r["note"], int(r["midi"]), int(r["register"]), r["pattern"],
                                 r["primary"].strip().lower() == "yes", r.get("notes", "")))
    return rows


def openness(pattern: str) -> list[float]:
    """'x' closed -> 0, 'o' open -> 1, 'h' half -> 0.5. Pattern is hole 1..6."""
    table = {"x": 0.0, "o": 1.0, "h": 0.5}
    return [table[c] for c in pattern]


def midi_to_hz(m: float, a4: float = 440.0) -> float:
    return a4 * 2 ** ((m - 69) / 12)


def cents(f: float, ref: float) -> float:
    return 1200 * np.log2(f / ref)


def predict(w: WhistleMM, pattern: str, register: int, fmax: float = 5000.0) -> float:
    """Predicted playing frequency (Hz) for a fingering in a given register."""
    bore, holes, window, air = w.to_model()
    fs = tmm.playing_frequencies(bore, holes, openness(pattern), window, air,
                                 fmin=200.0, fmax=fmax, n_registers=register, df=3.0)
    return fs[register - 1] if len(fs) >= register else float("nan")


@dataclass
class Prediction:
    row: ChartRow
    hz: float
    target_hz: float

    @property
    def cents_error(self) -> float:
        return cents(self.hz, self.target_hz)


def predict_chart(w: WhistleMM, chart: list[ChartRow], a4: float = 440.0) -> list[Prediction]:
    cache: dict[tuple[str, int], float] = {}
    out = []
    for r in chart:
        key = (r.pattern, r.register)
        if key not in cache:
            cache[key] = predict(w, r.pattern, r.register)
        out.append(Prediction(r, cache[key], midi_to_hz(r.midi, a4)))
    return out


# ---------------------------------------------------------------- design fit

def fit_holes(start: WhistleMM, chart: list[ChartRow], fit_rows=None, a4: float = 440.0,
              diameter_bounds=(3.0, 9.0), fit_length: bool = True, verbose: bool = False,
              diameter_prior: float | None = 6.5, prior_cents_per_mm: float = 5.0):
    """Adjust bore length, hole positions and hole diameters to minimise cents error.

    fit_rows: predicate choosing which chart rows drive the fit (default: primary
    rows with no half-holes). Returns (fitted WhistleMM, scipy result).
    """
    from scipy.optimize import least_squares

    if fit_rows is None:
        fit_rows = lambda r: r.primary and "h" not in r.pattern
    rows = [r for r in chart if fit_rows(r)]
    n = len(start.holes)

    def unpack(p):
        L = p[0] if fit_length else start.bore_length
        pos = p[1:1 + n]
        dia = p[1 + n:1 + 2 * n]
        holes = [HoleMM(float(pos[i]), float(dia[i]), start.holes[i].chimney) for i in range(n)]
        return replace(start, bore_length=float(L), holes=holes)

    def resid(p):
        w = unpack(p)
        if any(h.position >= w.bore_length - 2 for h in w.holes):
            return np.full(len(rows), 500.0)
        preds = predict_chart(w, rows, a4)
        e = np.nan_to_num(np.array([p.cents_error for p in preds]), nan=500.0)
        if diameter_prior is not None:
            e = np.r_[e, prior_cents_per_mm * (np.array([h.diameter for h in w.holes]) - diameter_prior)]
        return e

    p0 = np.array([start.bore_length] + [h.position for h in start.holes] + [h.diameter for h in start.holes])
    lo = np.array([start.bore_length * 0.8] + [start.bore_length * 0.3] * n + [diameter_bounds[0]] * n)
    hi = np.array([start.bore_length * 1.2] + [start.bore_length * 1.1] * n + [diameter_bounds[1]] * n)
    res = least_squares(resid, p0, bounds=(lo, hi), x_scale=np.r_[10.0, [5.0] * n, [0.5] * n],
                        diff_step=1e-4, verbose=2 if verbose else 0)
    return unpack(res.x), res


def openness_for_target(w: WhistleMM, pattern: str, register: int, target_hz: float,
                        hole_index: int | None = None) -> float:
    """Openness (0-1) of the half-holed hole that puts the note on target.

    A player shades a half-hole until it sounds right, so the meaningful check
    is whether some coverage reaches the target, and how much. Returns nan if
    the target is outside the closed..open range.
    """
    from scipy.optimize import brentq

    if hole_index is None:
        hole_index = pattern.index("h")
    base = openness(pattern)

    def f_at(s):
        o = list(base)
        o[hole_index] = s
        bore, holes, window, air = w.to_model()
        fs = tmm.playing_frequencies(bore, holes, o, window, air, fmin=200.0, fmax=5000.0,
                                     n_registers=register, df=3.0)
        return fs[register - 1] if len(fs) >= register else float("nan")

    lo, hi = 1e-3, 1.0
    g = lambda s: cents(f_at(s), target_hz)
    glo, ghi = g(lo), g(hi)
    if not (np.isfinite(glo) and np.isfinite(ghi)) or glo * ghi > 0:
        return float("nan")
    return float(brentq(g, lo, hi, xtol=1e-3))
