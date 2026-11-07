# The "ping" on low notes: a click when a hole closes (2026-11-07)

First live session with the raw-stream WARBL (502 frames/s). Norm: "really close to real whistle performance; there is a pinging sound in the lowest notes." Take: `data/takes/vw-take-20261107-143317-raw-sp-48000.{wav,csv}` (13.8 s, page ScriptProcessor engine, 48 kHz).

## What it was
- High-frequency bursts (above 10 kHz, -9 to -26 dB peak) 7-17 ms after each finger change, loudest on changes into E and low D. None on held notes.
- Zoomed in: a one-sample spike (up to -0.6 full scale) at the exact sample a hole's openness reaches 0, then a short ring. It sits at the end of the 15 ms finger ramp.
- Cause: the hole filter switched from its open form (second order) to a separate first-order closed form at o <= 1e-4, keeping the filter state. Near closing, the open form has a slow pole almost on its zero at s = 0 (time constant 2 t1 / A, hundreds of ms); its state, ~1e3 in bore-pressure units, was dumped into the output in one sample at the switch.

## What did not work (replays of the take through the JS model)
| Change | Loudest click (dB, >10 kHz) | Held-note pitch |
|---|---|---|
| none | -4.4 | reference |
| hole never fully closes, o >= 1e-3 | -13.7 | low D +72 cents |
| drop the once-added state term at the switch | -4.2 | same |
| update holes every sample, keep the switch | -7.9 | same |
| no switch (exact o -> 0 limit), 32-sample steps | -17.7 | same |
| no switch + every sample | -39.0 | same |

## Fix
1. One filter form from open to closed. Below the leak level the slow pole stops at s = -1 rad/s (stable in float32) and a zero moves from s = 0 to meet it; fully closed, they cancel and the response is the old closed response 1 / (1 + s tauC / 2), with DC passing as before. (A plain floor on the pole without the zero blocked DC at closed holes and moved the nine-hole low D by 3 cents.)
2. Hole openness ramps every model sample in the page and both renderers; breath stays at block rate.

## Results
- Take replayed through the fixed JS engine: closing clicks -37 to -53 dB (were -9 to -26 dB in the recording); held notes in the take have -52 to -65 dB in the same band.
- C++ renderer, same take: peak before normalising 1.6e3 before the fix (the clicks), 303 after (the notes).
- Pitch of held notes in the take (G, soft low D, low D): within 0.2 cents of before.
- Tests: 22 pass; C++ and JS agree within 0.005 cents on the nine-hole vent-open test; nine-hole low D 909.7 Hz (was 910.0).
- Float32 stability: 2 minutes of closed low D in the C++ engine, level and pitch identical at 1, 60 and 118 s (605.636 Hz); silence afterwards falls to -220 dB, no DC.

Next: Norm plays the fixed page and records again; the remaining transient at closing should be judged by ear and by the same measurement.
