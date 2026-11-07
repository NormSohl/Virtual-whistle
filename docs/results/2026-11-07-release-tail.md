# Note tails ring too long: missing wall losses (2026-11-07, experiment)

Norm, playing the fixed page: "a reverb tail at the end of the sound that goes on for too long."

## Measured
- Model (take `data/takes/vw-take-20261107-143317-raw-sp-48000`): breath reaches 0 within 20 ms of release and the jet stops; the bore then rings at the note's pitch, decaying 53 dB/s (G) and 26-28 dB/s (low D): 60 dB takes ~0.9-2.3 s. Same before and after the closing-click fix.
- Real Generation D (`2026-11-01_two_octaves_diatonic*.m4a`, 26 note ends, first 80 ms after the end): median 289 dB/s (60 dB in ~0.2 s, room included). Bore Q ~60 at 600 Hz in the real whistle vs ~630 in the model.
- Cause: the model loses energy only by radiation (holes, window, foot); viscothermal losses along the bore wall are not modelled.

## Experiment: wall losses (JS model only, off by default)
Per bore segment and direction, a first-order filter fitted to exp(-alpha(f) L), alpha = 3e-5 sqrt(f) / a (Fletcher & Rossing); setting `wallLoss` (0 off, 1 physical). The one-pole fit is ~40 % light at 500 Hz and a little strong near 2 kHz.

Replays of the take (JS, page engine):
| Setting | Release (G / low D) | Held pitch G / soft D / D (Hz) | Level (dB) |
|---|---|---|---|
| off (Generation D) | 53 / 28 dB/s | 805.4 / 599.0 / 600.4 | -20 / -31 / -32 |
| wall 1, jet unchanged | 396 / 264 dB/s | 798.7 / 596.3 / 624.3 | -37 / -49 / -59 |
| wall 1, jetGain -300 | 396 / 264 dB/s | 798.7 / 595.7 / 630.4 | -28 / -39 / -48 |
| release only (wall 1 while breath < 0.01) | 396 / 264 dB/s | 805.4 / 599.0 / 600.4 | -20 / -31 / -32 |

- Physical wall losses give the real whistle's release (~290 dB/s) but, with the jet as calibrated for a lossless bore, low D pulls 85-115 cents sharp at normal breath (real: ~10 cents soft to loud, `breath_sweeps.md`) and plays 15-25 dB quieter. jetRatio alone (0.7-1.1) does not fix the pull: 117-389 cents. Keeping full wall losses needs a refit of the jet (and dispersion) against the measured pitches, breath sweeps and release rate together.
- Release only: losses crossfade in over 10 ms once breath is ~0; playing is unchanged (byte-identical while breath > 0.01), tails decay like the real whistle. Not physics; a listening stopgap.
- Off: byte-identical to the engine before this code.

The play page has a "Wall losses" selector (Off / Release only / Full) for Norm to compare by ear. Decision after listening: keep release-only as a stopgap, go for the full refit, or drop.
