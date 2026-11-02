"""Calibrate the impedance model against Norm's Generation D recordings.

Geometry: data/generation_d/geometry_measured.csv (hard-coded below).
Pitches: data/generation_d/pitches_measured.csv (from analysis.pitch).

Run:  python -m acoustics.calibrate_generation_d
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

from .whistle import HoleMM, WhistleMM, cents, predict

ROOT = Path(__file__).resolve().parent.parent

# Holes 1-6: lower edge to foot (mm), diameter (mm), from geometry_measured.csv.
EDGE = [144.65, 123.6, 100.65, 79.5, 60.15, 35.0]
DIA = [4.45, 5.8, 5.1, 4.75, 6.0, 6.0]
LABIUM_FROM_FOOT = 263.5
BORE = 11.8
WALL = 0.4            # between the 0.32 measured and 0.50 implied by OD/bore
WINDOW = (5.0, 7.7)   # length along axis, width
BREATH_TEMP_C = 30.0


def make(top_from_foot: float, window_scale: float, hole4_edge: float = EDGE[3],
         temp_c: float = BREATH_TEMP_C) -> WhistleMM:
    edges = list(EDGE)
    edges[3] = hole4_edge
    holes = [HoleMM(top_from_foot - (e + d / 2), d, WALL) for e, d in zip(edges, DIA)]
    return WhistleMM(top_from_foot, BORE, holes, WINDOW[0], WINDOW[1], 2.0, window_scale, temp_c)


def load_measured():
    with open(ROOT / "data/generation_d/pitches_measured.csv", newline="") as fh:
        return [r for r in csv.DictReader(fh) if r["measured_hz"]]


def residuals(w: WhistleMM, rows) -> np.ndarray:
    return np.array([cents(predict(w, r["pattern"], int(r["register"])), float(r["measured_hz"]))
                     for r in rows])


def report(title: str, w: WhistleMM, rows) -> np.ndarray:
    e = residuals(w, rows)
    print(f"{title}: mean {e.mean():+.1f}, sd {e.std():.1f}, max |err| {np.abs(e).max():.1f} cents")
    for r, x in zip(rows, e):
        print(f"  {r['intended_note']:<4} reg {r['register']}  {x:+6.1f}")
    return e


def main() -> None:
    rows = load_measured()
    report("Uncalibrated (bore top at labium, 30 °C)", make(LABIUM_FROM_FOOT, 1.0), rows)

    fit2 = minimize(lambda p: np.sum(residuals(make(p[0], p[1]), rows) ** 2), [LABIUM_FROM_FOOT, 1.0],
                    method="Nelder-Mead", options=dict(xatol=0.05, fatol=0.5, maxiter=150))
    L, s = fit2.x
    report(f"\nCalibrated: bore top {L:.1f} mm from foot, window scale {s:.2f}", make(L, s), rows)

    fit3 = minimize(lambda p: np.sum(residuals(make(p[0], p[1], p[2]), rows) ** 2), [L, s, EDGE[3]],
                    method="Nelder-Mead", options=dict(xatol=0.05, fatol=0.5, maxiter=200))
    L3, s3, h4 = fit3.x
    report(f"\nCalibrated + hole 4 position free: bore top {L3:.1f}, window scale {s3:.2f}, "
           f"hole 4 lower edge {h4:.1f} mm (measured {EDGE[3]})", make(L3, s3, h4), rows)


if __name__ == "__main__":
    main()
