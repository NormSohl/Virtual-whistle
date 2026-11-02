"""Regression check: the saved generic D design still plays its diatonic notes in tune.

The geometry comes from `python -m acoustics.demo_generic_d` (a model-designed
instrument, not a measured one). Re-run the demo after changing the acoustics,
then re-run this test.
"""
import json
from pathlib import Path

from acoustics.whistle import HoleMM, WhistleMM, load_chart, predict_chart

ROOT = Path(__file__).resolve().parent.parent


def load_fitted() -> WhistleMM:
    d = json.loads((ROOT / "data/generic_d/geometry_fitted.json").read_text())
    d["holes"] = [HoleMM(**h) for h in d["holes"]]
    return WhistleMM(**d)


def test_diatonic_notes_within_8_cents_both_registers():
    w = load_fitted()
    chart = [r for r in load_chart(ROOT / "data/charts/d_whistle_standard.csv")
             if r.primary and "h" not in r.pattern]
    errors = {f"{p.row.note}/{p.row.register}": p.cents_error for p in predict_chart(w, chart)}
    assert all(abs(e) < 8 for e in errors.values()), errors


def test_cross_fingered_c_natural_is_sharp_on_cylindrical_bore():
    """oxxooo C natural plays well sharp on a cylindrical-bore whistle; players report the same."""
    w = load_fitted()
    chart = [r for r in load_chart(ROOT / "data/charts/d_whistle_standard.csv") if r.pattern == "oxxooo"]
    (p,) = predict_chart(w, chart)
    assert p.cents_error > 20
