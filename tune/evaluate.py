"""Score a VwWhistle settings set (JS model) the way Generation D was calibrated, plus breath and release.

Scale: render/synth.scale_rows (two octaves, per-note BREATH table) vs the mean of Norm's two
diatonic takes (data/generation_d/pitches_measured.csv). Breath sweeps: D and G held while breath
rises slowly, vs data/generation_d/breath_sweeps.md (D rises ~10 cents, G ~18, before the octave).
Release: fade rate in the 30-120 ms after breath stops on D, G and B, vs ~290 dB/s measured on the
real whistle (docs/results/2026-11-07-release-tail.md).

python -m tune.evaluate '{"wallLoss":1}'      -> prints a report and the cost
"""
from __future__ import annotations
import csv, json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from render import synth
from analysis import pitch

SR = 96000


def references() -> dict[tuple[str, int], float]:
    acc: dict[tuple[str, int], list[float]] = {}
    with open(ROOT / "data/generation_d/pitches_measured.csv") as f:
        for r in csv.DictReader(f):
            if r["measured_hz"]:
                acc.setdefault((r["pattern"], int(r["register"])), []).append(float(r["measured_hz"]))
    return {k: float(np.mean(v)) for k, v in acc.items()}


# Relative loudness of each scale note in Norm's two takes (dB below the loudest), measured 0.15-0.55 s
# into each note at the starts in pitches_measured.csv. Order as in synth.scale_rows.
REAL_LEVEL = [-10.4, -7.1, -3.6, -3.7, -1.4, -2.8, -3.9, 0.0, -0.7, -0.5, -0.2, -2.5, -2.8, -3.3]


def render(settings: dict, rows: list[list[float]], tmp: Path, name: str) -> np.ndarray:
    c, s, o = tmp / f"{name}.csv", tmp / f"{name}.json", tmp / f"{name}.raw"
    synth.write_control(rows, c)
    s.write_text(json.dumps(settings))
    subprocess.run(["node", str(ROOT / "web/render-node.js"), str(c), str(o), "-", str(s)], check=True)
    return np.fromfile(o, dtype=np.float32).astype(np.float64)


def env_db(x: np.ndarray, win: float = 0.005) -> np.ndarray:
    n = int(win * SR)
    return 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(n) / n, "same")) + 1e-12)


def scale(settings: dict, tmp: Path) -> list[dict]:
    rows, labels = synth.scale_rows()
    x = render(settings, rows, tmp, "scale")
    x = x / (np.max(np.abs(x)) + 1e-30)
    ref = references()
    e = env_db(x)
    out = []
    for label, pattern, t0, t1 in labels:
        reg = 2 if label.endswith("'") else 1
        key = ("oxxxxx", 2) if label == "D'" else (pattern, reg)
        a, b = t0 + 0.35, t0 + 0.95       # settled part of the 1 s hold
        tr = pitch.pitch_track(x[int(a * SR):int(b * SR)], SR, fmin=300, fmax=5000)
        hz = float(np.nanmedian(tr.freqs)) if np.isfinite(tr.freqs).any() else float("nan")
        target = ref[key]
        # register: nearest of target * (1/2, 1, 2, 3/2...) by octave count
        cents = 1200 * np.log2(hz / target) if np.isfinite(hz) else float("nan")
        level = float(np.median(e[int(a * SR):int(b * SR)]))
        # release: breath reaches 0 at t0 + hold + release (1.0 + 0.03)
        r0 = t0 + 1.03
        seg = e[int((r0 + 0.03) * SR):int((r0 + 0.12) * SR)]
        rate = -np.polyfit(np.arange(len(seg)) / SR, seg, 1)[0]
        out.append(dict(label=label, hz=hz, target=target, cents=cents, level=level, release=rate))
    return out


def sweep(settings: dict, pattern: str, tmp: Path, name: str) -> list[tuple[float, float, float]]:
    o = synth.openness(pattern)
    rows = [[0.0] + o + [0.0], [0.05] + o + [0.03], [8.0] + o + [0.6], [8.05] + o + [0.0], [8.2] + o + [0.0]]
    x = render(settings, rows, tmp, name)
    e = env_db(x)
    out = []
    for t in np.arange(0.4, 7.9, 0.15):
        tr = pitch.pitch_track(x[int(t * SR):int((t + 0.06) * SR)], SR, fmin=300, fmax=5000)
        hz = float(np.nanmedian(tr.freqs)) if np.isfinite(tr.freqs).any() else float("nan")
        b = 0.03 + (0.6 - 0.03) * (t + 0.03 - 0.05) / 7.95
        out.append((b, hz, float(np.median(e[int(t * SR):int((t + 0.06) * SR)]))))
    return out


ONSET_NOTES = [("D", "xxxxxx", 1), ("E", "xxxxxo", 1), ("G", "xxxooo", 1), ("A", "xxoooo", 1), ("B", "xooooo", 1),
               ("C#", "oooooo", 1), ("E'", "xxxxxo", 2), ("G'", "xxxooo", 2)]
ONSET_SCALE = (0.75, 1.0, 1.4, 1.8, 2.4)   # above 1.4x the note may be in either register, but must sound


def onsets(settings: dict, tmp: Path) -> list[dict]:
    """Tongued starts from silence at soft / scale / strong breath for each note: does it speak, in the right
    register, and how loud (dB re the loudest start in this test)?"""
    ref = references()
    out = []
    for label, pattern, reg in ONSET_NOTES:
        target = ref[(pattern, reg)]
        base = synth.BREATH[label]
        o = synth.openness(pattern)
        for k in ONSET_SCALE:
            b = base * k
            rows = [[0.0] + o + [0.0], [0.008] + o + [b], [0.6] + o + [b], [0.63] + o + [0.0], [0.7] + o + [0.0]]
            x = render(settings, rows, tmp, "onset")
            seg = x[int(0.3 * SR):int(0.58 * SR)]
            lv = 20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-12)
            tr = pitch.pitch_track(seg, SR, fmin=300, fmax=5000)
            hz = float(np.nanmedian(tr.freqs)) if np.isfinite(tr.freqs).any() else float("nan")
            cents = 1200 * np.log2(hz / target) if np.isfinite(hz) else float("nan")
            out.append(dict(label=label, k=k, breath=b, level=lv, hz=hz, cents=cents))
    top = max(r["level"] for r in out)
    for r in out:
        r["rel"] = r["level"] - top
        c = r["cents"]
        if r["k"] > 1.45 and np.isfinite(c):   # strong breath: any register (x1, x1.5, x2, x3 of the target) as long as it sounds
            c = min(abs(c - 1200 * np.log2(m)) for m in (1, 1.5, 2, 3))
        r["ok"] = bool(np.isfinite(c) and abs(c) < 100 and r["rel"] > -35)
    return out


def sweep_summary(sw, f1: float) -> dict:
    """First-register span (cents, from where it speaks to just before the octave) and break breath."""
    loud = max(l for _, _, l in sw)
    first = [(b, hz) for b, hz, l in sw if l > loud - 30 and np.isfinite(hz) and abs(1200 * np.log2(hz / f1)) < 300]
    second = [b for b, hz, l in sw if l > loud - 30 and np.isfinite(hz) and abs(1200 * np.log2(hz / (2 * f1))) < 300]
    if not first:
        return dict(span=float("nan"), start=float("nan"), brk=float("nan"))
    brk = min([b for b in second if b > first[0][0]], default=float("nan"))
    f = [hz for b, hz in first if not np.isfinite(brk) or b < brk]
    return dict(span=1200 * np.log2(max(f) / min(f)), start=first[0][0], brk=brk)


def evaluate(settings: dict, verbose: bool = False) -> tuple[float, dict]:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        sc = scale(settings, tmp)
        ref = references()
        swD = sweep_summary(sweep(settings, "xxxxxx", tmp, "swD"), ref[("xxxxxx", 1)])
        swG = sweep_summary(sweep(settings, "xxxooo", tmp, "swG"), ref[("xxxooo", 1)])
        ons = onsets(settings, tmp)
    cents = np.array([r["cents"] for r in sc])
    wrong = int(np.sum(~np.isfinite(cents) | (np.abs(cents) > 300)))
    ok = cents[np.isfinite(cents) & (np.abs(cents) <= 300)]
    rel = np.array([r["release"] for r in sc if r["label"] in ("D", "G", "B")])
    lv = np.array([r["level"] for r in sc])
    cost = (200 * wrong + float(np.sqrt(np.mean(ok ** 2))) if len(ok) else 1e4)
    for sw, target, played in ((swD, 10.0, synth.BREATH["D"]), (swG, 18.0, synth.BREATH["G"])):
        cost += 0.5 * (abs(sw["span"] - target) if np.isfinite(sw["span"]) else 200)
        # the first register must hold at least 0.05 beyond the breath the scale plays it at
        need = played + 0.05
        if not np.isfinite(sw["brk"]) or sw["brk"] < need:
            cost += 400 * max(0.0, need - (sw["brk"] if np.isfinite(sw["brk"]) else 0.0))
    cost += 0.05 * float(np.mean(np.abs(np.log2(np.maximum(rel, 1) / 290)) * 100))   # ~cents-like scale
    fails = [r for r in ons if not r["ok"]]
    cost += 15.0 * len(fails)
    rl = lv - lv.max()
    level_err = float(np.sqrt(np.mean((rl - np.array(REAL_LEVEL)) ** 2)))
    cost += 1.0 * level_err
    rep = dict(scale=sc, wrong=wrong, rms_cents=float(np.sqrt(np.mean(ok ** 2))) if len(ok) else float("nan"),
               mean_cents=float(np.mean(ok)) if len(ok) else float("nan"), max_cents=float(np.max(np.abs(ok))) if len(ok) else float("nan"),
               swD=swD, swG=swG, release=rel.tolist(), level_spread=float(lv.max() - lv.min()), level_err=level_err, onsets=ons, onset_fails=len(fails), cost=cost)
    if verbose:
        print(f"{'note':5} {'model Hz':>9} {'takes Hz':>9} {'cents':>7} {'level dB':>9} {'release dB/s':>13}")
        for r in sc:
            print(f"{r['label']:5} {r['hz']:9.1f} {r['target']:9.1f} {r['cents']:+7.1f} {r['level']:9.1f} {r['release']:13.0f}")
        print(f"wrong register {wrong}/14; in register: mean {rep['mean_cents']:+.1f}, rms {rep['rms_cents']:.1f}, max {rep['max_cents']:.1f} cents; level spread {rep['level_spread']:.0f} dB, rms vs real balance {level_err:.1f} dB (real spread 10 dB)")
        print(f"breath sweep D: speaks at {swD['start']:.2f}, first register spans {swD['span']:.0f} cents, octave at {swD['brk']:.2f}   (real ~10 cents)")
        print(f"breath sweep G: speaks at {swG['start']:.2f}, first register spans {swG['span']:.0f} cents, octave at {swG['brk']:.2f}   (real ~18 cents)")
        print(f"release D/G/B: {', '.join(f'{v:.0f}' for v in rel)} dB/s   (real ~290)")
        print(f"tongued starts that fail (silent, wrong register, or >35 dB below the loudest): {len(fails)}/{len(ons)}")
        for r in ons:
            print(f"   {r['label']:3} x{r['k']:.2f} breath {r['breath']:.3f}: " + (f"{r['hz']:7.1f} Hz {r['cents']:+6.0f} c {r['rel']:6.1f} dB" if np.isfinite(r['hz']) else f"silent {r['rel']:6.1f} dB") + ("" if r['ok'] else "   FAIL"))
        print(f"cost {cost:.1f}")
    return cost, rep


if __name__ == "__main__":
    evaluate(json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}, verbose=True)
