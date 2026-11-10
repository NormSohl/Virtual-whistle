"""C++ engine (dsp/whistle.hpp) vs the JS port (web/whistle-model.js) beyond the default settings,
the geometry checks both engines share, and a pin on the Generation D scale tuning.
"""
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pytest

from acoustics import tmm
from acoustics.whistle import HoleMM, WhistleMM, predict
from analysis.pitch import cents, load_audio, pitch_track
from render import synth
from tune.evaluate import references

ROOT = Path(__file__).resolve().parent.parent
PATTERNS = ["xxxxxx", "xxxooo", "xooooo", "oxxxxx"]   # D, G, B, D'
BREATHS = [0.10, 0.17, 0.30, 0.42]
KEYS = {"dispersion": "dispersion", "jetRatio": "jet_ratio", "jetGain": "jet_gain", "jetOffset": "jet_offset",
        "jetStrouhal": "jet_strouhal", "wallLoss": "wall_loss", "wallReleaseOnly": "wall_release_only"}


def rows_and_spans():
    rows, spans, t = [], [], 0.0
    for pat, b in zip(PATTERNS, BREATHS):
        r, t1 = synth.note_rows(t, pat, b, hold=0.8)
        rows += r
        spans.append((t + 0.35, t + 0.75))
        t = t1
    return rows, spans


def medians(x, sr, spans):
    tr = pitch_track(x, sr, fmin=400, fmax=4000)
    return [float(np.median(tr.freqs[(tr.times >= a) & (tr.times <= b) & ~np.isnan(tr.freqs)])) for a, b in spans]


def render_both(js_settings: dict, name: str):
    rows, spans = rows_and_spans()
    cfg = synth.generation_d_config(**{KEYS[k]: float(v) for k, v in js_settings.items()})
    x, sr = load_audio(str(synth.render(cfg, rows, name)))
    fc = medians(x, sr, spans)
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        synth.write_control(rows, d / "c.csv")
        (d / "s.json").write_text(json.dumps(js_settings))
        subprocess.run(["node", str(ROOT / "web/render-node.js"), str(d / "c.csv"), str(d / "o.raw"), "-",
                        str(d / "s.json")], check=True)
        fj = medians(np.fromfile(d / "o.raw", dtype=np.float32), 96000, spans)
    return fc, fj


def test_cpp_and_js_agree_with_wall_loss_preset():
    """The "Wall losses (retuned)" preset on the play page must sound the same from the C++ engine."""
    preset = json.loads((ROOT / "tune/presets/generation_d_wall_fit_run6.json").read_text())
    fc, fj = render_both(preset, "t_parity_wall")
    errs = [cents(a, b) for a, b in zip(fc, fj)]
    assert all(abs(e) < 0.5 for e in errs), errs


def test_cpp_and_js_agree_with_release_only_losses():
    fc, fj = render_both({"wallLoss": 1.0, "wallReleaseOnly": True}, "t_parity_release")
    errs = [cents(a, b) for a, b in zip(fc, fj)]
    assert all(abs(e) < 0.5 for e in errs), errs


def test_generation_d_scale_tuning_is_pinned():
    """C++ engine, default settings, two-octave scale vs Norm's takes: 10.3 cents rms, 23.0 max on
    2026-11-09. Fails if a change to the engine moves the calibrated instrument."""
    rows, labels = synth.scale_rows()
    x, sr = load_audio(str(synth.render(synth.generation_d_config(), rows, "t_scale_pin")))
    ref = references()
    errs = {}
    for label, pattern, t0, _ in labels:
        key = ("oxxxxx", 2) if label == "D'" else (pattern, 2 if label.endswith("'") else 1)
        tr = pitch_track(x[int((t0 + 0.35) * sr):int((t0 + 0.95) * sr)], sr, fmin=300, fmax=5000)
        errs[label] = cents(float(np.nanmedian(tr.freqs)), ref[key])
    e = np.array(list(errs.values()))
    assert np.sqrt(np.mean(e ** 2)) < 12 and np.max(np.abs(e)) < 25, errs


def close_holes_config() -> dict:
    cfg = synth.generation_d_config()
    cfg["hole2_pos"] = cfg["hole1_pos"] + 3.0     # 3 mm from hole 1: under 2 samples of travel at 96 kHz
    return cfg


def test_cpp_renderer_rejects_holes_too_close_together():
    rows, _ = rows_and_spans()
    synth.build()
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        synth.write_config(close_holes_config(), d / "c.cfg")
        synth.write_control(rows, d / "c.csv")
        r = subprocess.run([str(synth.BIN), str(d / "c.cfg"), str(d / "c.csv"), str(d / "o.wav")],
                           capture_output=True, text=True)
    assert r.returncode == 2 and "can't be modelled" in r.stderr


def test_js_model_rejects_holes_too_close_together():
    js = ("const {VwWhistle, vwGenerationD} = require(%s); const g = vwGenerationD();"
          "g.holePos[1] = g.holePos[0] + 0.003; try { new VwWhistle(g); console.log('built'); }"
          "catch (e) { console.log('rejected'); }") % json.dumps(str(ROOT / "web/whistle-model.js"))
    r = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True)
    assert r.stdout.strip() == "rejected"


def test_impedance_model_rejects_two_holes_at_one_position():
    bore, window = tmm.Bore(0.30, [(0.0, 0.006)]), tmm.Window(0.006, 0.009, 0.002)
    holes = [tmm.Hole(0.12, 0.003, 0.001), tmm.Hole(0.12, 0.002, 0.001)]
    with pytest.raises(ValueError, match="same position"):
        tmm.playing_frequencies(bore, holes, [1.0, 0.0], window, n_registers=1)


def test_long_bore_first_register_is_found_below_200_hz():
    """A metre-long bore (bass recorder size) has its first register near c / 2L, about 165 Hz."""
    w = WhistleMM(1000.0, 30.0, [HoleMM(900.0, 12.0, 4.0)], window_length=10.0, window_width=20.0)
    f = predict(w, "x", 1)
    assert 130 < f < 180, f
