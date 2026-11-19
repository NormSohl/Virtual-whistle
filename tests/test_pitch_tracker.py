"""MIDI-out pitch tracker (web/pitch-tracker.js) on the page engine's two-octave scale: pitch against offline
YIN, one note per tongued note, one note for the whole slurred scale, note-off soon after the breath stops."""
import json
import math
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pytest

from analysis.pitch import yin_frame

ROOT = Path(__file__).resolve().parent.parent
SR = 48000


def run(mode: str, tmp: str):
    subprocess.run(["node", str(ROOT / "web/track-node.js"), str(ROOT), mode, tmp], check=True)
    x = np.fromfile(f"{tmp}/scale_{mode}.f32", dtype=np.float32).astype(np.float64)
    seg = json.loads(Path(f"{tmp}/scale_{mode}.json").read_text())
    log = np.genfromtxt(f"{tmp}/scale_{mode}.csv", delimiter=",", names=True, dtype=None, encoding=None)
    return x, seg, log


@pytest.mark.parametrize("mode", ["tongued", "slur"])
def test_tracker(mode):
    with tempfile.TemporaryDirectory() as tmp:
        x, seg, log = run(mode, tmp)
    t, gate, f = log["t"], log["gate"], log["f"]
    for i, s in enumerate(seg):
        a, b = s["t1"] - 0.3, s["t1"] - 0.02
        ref, _ = yin_frame(x[int(a * SR):int(b * SR)], SR, 400, 4000)
        held = f[(t > a) & (t < b) & (gate > 0)]
        assert len(held), s["name"]
        assert abs(1200 * math.log2(np.median(held) / ref)) < 1.0, s["name"]
        assert 1200 * math.log2(held.max() / held.min()) < 3.0, s["name"]
        if mode == "tongued":
            nxt = seg[i + 1]["t0"] if i + 1 < len(seg) else t[-1]
            off = t[(t >= s["t1"]) & (t < nxt) & (gate == 0)]
            assert len(off) and off[0] - s["t1"] < 0.025, s["name"]   # note-off within 25 ms of the breath stopping
    ons = int(np.sum(np.diff(gate) > 0))
    assert ons == (len(seg) if mode == "tongued" else 1)
