"""Fit a "Generation D + wall losses" preset: jet and tuning settings for a bore with wall losses,
scored by tune.evaluate (same scale test as Generation D, plus breath sweeps and release).
Generation D's own settings are not touched; the result is written to tune/presets/.

python -m tune.fit_wall [generations]
"""
from __future__ import annotations
import json, sys, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
import cma
from tune.evaluate import evaluate

# name, lower, upper, Generation D value
PARAMS = [
    ("dispersion", 0.97, 1.01, 0.991),
    ("jetRatio", 0.25, 1.6, 1.0),
    ("logJetGain", np.log(5), np.log(1500), np.log(100)),
    ("jetOffset", 0.0, 0.6, 0.1),
    ("jetStrouhal", 0.02, 0.5, 0.2),
    ("wallLoss", 0.8, 1.5, 1.0),
]


def to_settings(u: np.ndarray) -> dict:
    s = {}
    for (name, lo, hi, _), v in zip(PARAMS, np.clip(u, 0, 1)):
        x = lo + v * (hi - lo)
        if name == "logJetGain":
            s["jetGain"] = -float(np.exp(x))
        else:
            s[name] = float(x)
    return s


def cost(u) -> float:
    try:
        return evaluate(to_settings(np.asarray(u)))[0]
    except Exception:
        return 1e4


def main() -> None:
    gens = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    x0 = [(g - lo) / (hi - lo) for _, lo, hi, g in PARAMS]
    start = Path(__file__).with_name("presets") / (sys.argv[2] + ".json")
    if len(sys.argv) > 2 and start.exists():
        st = json.loads(start.read_text()); st["logJetGain"] = float(np.log(-st.pop("jetGain")))
        x0 = [(st[n] - lo) / (hi - lo) for n, lo, hi, _ in PARAMS]
    es = cma.CMAEvolutionStrategy(x0, 0.15, {"bounds": [0, 1], "popsize": 8, "seed": 7, "verbose": -9})
    log = Path(__file__).with_name("fit_wall.log")
    t0 = time.time()
    with ProcessPoolExecutor(2) as ex, log.open("w") as f:
        for g in range(gens):
            xs = es.ask()
            cs = list(ex.map(cost, xs))
            es.tell(xs, cs)
            b = es.result
            line = f"gen {g:3d}  best {b.fbest:7.2f}  {json.dumps({k: round(v, 4) for k, v in to_settings(np.asarray(b.xbest)).items()})}  {time.time() - t0:5.0f}s"
            print(line, flush=True); f.write(line + "\n"); f.flush()
    best = to_settings(np.asarray(es.result.xbest))
    out = Path(__file__).with_name("presets"); out.mkdir(exist_ok=True)
    (out / "generation_d_wall_fit.json").write_text(json.dumps(best, indent=2) + "\n")
    print("best", json.dumps(best))


if __name__ == "__main__":
    main()
