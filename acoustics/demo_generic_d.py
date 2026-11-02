"""Demo: design a generic D whistle with the impedance model.

Starts from a rough tube (NOT a measured instrument), fits bore length, hole
positions and hole diameters so the standard D chart's primary non-half-hole
fingerings play in tune in both registers, then reports predicted cents error
for every row of the chart, including half-holes and cross fingerings that
were not part of the fit.

Run:  python -m acoustics.demo_generic_d
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .whistle import HoleMM, WhistleMM, fit_holes, load_chart, openness_for_target, predict_chart

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    chart = load_chart(ROOT / "data/charts/d_whistle_standard.csv")
    start = WhistleMM(
        bore_length=270.0, bore_diameter=12.5,
        holes=[HoleMM(p, 6.0, 0.6) for p in (120, 145, 170, 195, 215, 235)],
        window_length=6.0, window_width=9.0, window_wall=1.5, temp_c=25.0,
    )
    fitted, res = fit_holes(start, chart)
    out = ROOT / "data/generic_d/geometry_fitted.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(asdict(fitted), indent=2) + "\n")

    print("Fitted generic D whistle (mm, from top of bore):")
    print(f"  bore length {fitted.bore_length:.1f}, bore diameter {fitted.bore_diameter:.1f}")
    for i, h in enumerate(fitted.holes, 1):
        print(f"  hole {i}: position {h.position:6.1f}  diameter {h.diameter:4.2f}")
    print(f"  fit: {res.nfev} model evaluations")
    print()
    print(f"{'note':<5} {'reg':>3} {'pattern':<8} {'fit':>4} {'pred Hz':>8} {'target':>8} {'cents':>7}  notes")
    for p in predict_chart(fitted, chart):
        r = p.row
        in_fit = "yes" if (r.primary and "h" not in r.pattern) else ""
        extra = r.notes
        if "h" in r.pattern:
            s = openness_for_target(fitted, r.pattern, r.register, p.target_hz)
            extra = (f"in tune at {s * 100:.0f}% open" if s == s else "target out of reach") + \
                    (f"; {r.notes}" if r.notes else "")
        print(f"{r.note:<5} {r.register:>3} {r.pattern:<8} {in_fit:>4} {p.hz:8.1f} {p.target_hz:8.1f} "
              f"{p.cents_error:+7.1f}  {extra}")
    print()
    print("cents = prediction vs 12-TET target (A4 = 440 Hz). Half-hole rows are predicted at 50% open;")
    print("the note column says how far the hole must be uncovered to land in tune.")


if __name__ == "__main__":
    main()
