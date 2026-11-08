# Refitting the jet for a bore with wall losses (2026-11-07): not playable yet

Norm liked "release only" but asked for a fair comparison: refit the model with wall losses, without losing Generation D. Generation D's settings are untouched; the fit is a separate preset (`VW_PRESETS.generationDWall` in `web/whistle-model.js`, `tune/presets/`).

## Score (`python -m tune.evaluate '<settings json>'`)
Same scale test as Generation D (two octaves, per-note breath from `render/synth.py`, vs the mean of Norm's two diatonic takes), plus:
- breath sweeps on D and G: pitch rise across the first register (real ~10 and ~18 cents, `breath_sweeps.md`); penalty if the note breaks to the second register below its scale breath + 0.05;
- release: fade rate 30-120 ms after breath stops on D, G, B (real ~290 dB/s);
- note balance: relative level per scale note vs Norm's takes (real spread 10 dB, low D quietest).

## Fits (`python -m tune.fit_wall`, CMA-ES over dispersion, jetRatio, jetGain, jetOffset, jetStrouhal, wallLoss)
| | Scale rms / max (cents) | D / G breath rise (cents) | Release D/G/B (dB/s) | Balance rms (dB) | Cost |
|---|---|---|---|---|---|
| Generation D | 10.3 / 23.0 | 12 / 34 | 26 / 54 / 116 | 8.0 | 39.4 |
| wall 1, jet unchanged | 11.6 / 27.0 | 69 / 208 | 264 / 397 / 555 | - | - |
| run 2 | 11.5 / 33.6 | 38 / 90 | 215 / 326 / 465 | - | - |
| run 4 (best) | 10.2 / 26.0 | 11 / 31 | 220 / 332 / 472 | 14.4 | 33.8 |

Run 4 (`tune/presets/generation_d_wall_fit.json`): dispersion 0.9938, jetRatio 0.874, jetGain -5.09, jetOffset 0.597, jetStrouhal 0.115, wallLoss 0.805. jetGain, jetOffset and wallLoss sit at the edges of their ranges.

## Why it is not on the page
On the score it beats Generation D, but it plays badly outside the scale test. Tongued notes from silence at breath 0.08-0.45 (level in dBFS after the preset's +44 dB output gain, or silent):

| | 0.08 | 0.12 | 0.20 | 0.30 | 0.45 |
|---|---|---|---|---|---|
| Generation D, D | -28 | -30 | -20 (oct) | -15 (oct) | -17 (oct) |
| run 4, D | -54 | -70 | silent | silent | silent |
| Generation D, G | -33 | -22 | -21 | -20 (oct) | -10 (oct) |
| run 4, G | silent | -30 | -24 | silent | -19 (oct) |

The fit found the small breath-driven pitch rise by turning the jet gain down to its limit, where the oscillation is barely above threshold: notes start only for the exact attacks and breaths in the test. In this jet model, a strong oscillation and a small pitch rise with breath pull against each other once the bore has realistic losses (real whistle: both).

## Next
1. Add playability to the score: tongued starts from silence across each note's breath range must speak in the right register at a sensible level.
2. If that cannot be met, the jet model needs work (how the jet's phase follows breath, its saturation) rather than more fitting.
Meanwhile the page offers Off and Release only.
