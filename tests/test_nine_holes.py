"""The real-time model with more than six holes (up to the WARBL's nine).

Checks that (1) extra holes kept closed and tiny leave the Generation D's pitch
alone, (2) the C++ engine and the JS port agree on a nine-hole instrument, and
(3) the renderer refuses a control file whose hole count doesn't match.
"""
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from analysis.pitch import cents, load_audio, pitch_track
from render import synth

ROOT = Path(__file__).resolve().parent.parent
PATTERNS = ["xxxxxx", "xxxooo", "xooooo", "oxxxxx"]   # D, G, B, D' fingerings
BREATHS = [0.10, 0.17, 0.30, 0.42]


def nine_hole_config(extra_dia: float = 1.0) -> dict:
    """Generation D plus a thumb-side vent above hole 1 and two holes below hole 6.
    Positions in mm from the window, bore order: vent, holes 1-6, R4, extra."""
    base = synth.generation_d_config()
    six = [(base[f"hole{i}_pos"], base[f"hole{i}_dia"], base[f"hole{i}_wall"]) for i in range(1, 7)]
    holes = [(80.0, extra_dia, 2.0)] + six + [(240.0, extra_dia, 0.4), (252.0, extra_dia, 0.4)]
    cfg = {k: v for k, v in base.items() if not k.startswith("hole")}
    cfg["num_holes"] = len(holes)
    for i, (p, d, w) in enumerate(holes, 1):
        cfg[f"hole{i}_pos"], cfg[f"hole{i}_dia"], cfg[f"hole{i}_wall"] = p, d, w
    return cfg


def rows_for(patterns, extra_open=(0.0, 0.0, 0.0)):
    """Note rows; for nine holes the openness vector is [vent, h1..h6, R4, extra]."""
    rows, spans, t = [], [], 0.0
    for pat, b in zip(patterns, BREATHS):
        r, t1 = synth.note_rows(t, pat, b, hold=0.8)
        if extra_open is not None:
            r = [[x[0], extra_open[0]] + x[1:7] + list(extra_open[1:]) + [x[7]] for x in r]
        rows += r
        spans.append((t + 0.35, t + 0.75))
        t = t1
    return rows, spans


def median_pitches(wav_or_raw: Path, spans, raw=False):
    if raw:
        x, sr = np.fromfile(wav_or_raw, dtype=np.float32), 96000
    else:
        x, sr = load_audio(str(wav_or_raw))
    tr = pitch_track(x, sr, fmin=400, fmax=4000)
    out = []
    for a, b in spans:
        m = (tr.times >= a) & (tr.times <= b) & ~np.isnan(tr.freqs)
        out.append(float(np.median(tr.freqs[m])))
    return out


def cpp(cfg, rows, name):
    return synth.render(cfg, rows, name)


def js(cfg, rows, tmp: Path):
    mm = 1e-3
    n = cfg["num_holes"]
    g = {
        "boreRadius": cfg["bore_diameter"] / 2 * mm, "length": cfg["length"] * mm,
        "holePos": [cfg[f"hole{i}_pos"] * mm for i in range(1, n + 1)],
        "holeRadius": [cfg[f"hole{i}_dia"] / 2 * mm for i in range(1, n + 1)],
        "chimney": [cfg[f"hole{i}_wall"] * mm for i in range(1, n + 1)],
        "windowLength": cfg["window_length"] * mm, "windowWidth": cfg["window_width"] * mm,
        "windowWall": cfg["window_wall"] * mm, "windowScale": cfg["window_scale"],
    }
    (tmp / "g.json").write_text(json.dumps(g))
    synth.write_control(rows, tmp / "c.csv")
    subprocess.run(["node", str(ROOT / "web/render-node.js"), str(tmp / "c.csv"), str(tmp / "o.raw"),
                    str(tmp / "g.json")], check=True)
    return tmp / "o.raw"


def test_closed_extra_holes_leave_pitch_within_3_cents():
    six_rows, spans = rows_for(PATTERNS, extra_open=None)
    nine_rows, _ = rows_for(PATTERNS)
    f6 = median_pitches(cpp(synth.generation_d_config(), six_rows, "t_six"), spans)
    f9 = median_pitches(cpp(nine_hole_config(), nine_rows, "t_nine"), spans)
    errs = [cents(b, a) for a, b in zip(f6, f9)]
    assert all(abs(e) < 3 for e in errs), errs


def test_cpp_and_js_agree_on_nine_holes_with_vent_open():
    rows, spans = rows_for(PATTERNS, extra_open=(1.0, 1.0, 0.0))
    cfg = nine_hole_config(extra_dia=3.0)
    fc = median_pitches(cpp(cfg, rows, "t_nine_vent"), spans)
    with tempfile.TemporaryDirectory() as d:
        fj = median_pitches(js(cfg, rows, Path(d)), spans, raw=True)
    errs = [cents(b, a) for a, b in zip(fc, fj)]
    assert all(abs(e) < 0.1 for e in errs), errs


def test_renderer_rejects_hole_count_mismatch():
    rows, _ = rows_for(PATTERNS[:1], extra_open=None)   # six hole columns
    synth.build()
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        synth.write_config(nine_hole_config(), d / "c.cfg")
        synth.write_control(rows, d / "c.csv")
        r = subprocess.run([str(synth.BIN), str(d / "c.cfg"), str(d / "c.csv"), str(d / "o.wav")],
                           capture_output=True, text=True)
    assert r.returncode == 2 and "num_holes" in r.stderr
