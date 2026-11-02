# Design decisions

One line each: date, decision, reason.

- 2026-11-01: Start with a penny whistle before recorders. Simple, well-understood bore; proves the pipeline end to end.
- 2026-11-01: Real measured whistle is ground truth. Claude can't hear; every tuning claim must cite measured numbers.
- 2026-11-01: Two-stage tuning: fast impedance model for design and optimization, then calibrate the time-domain synth against its own measured pitch.
- 2026-11-01: DSP core in portable C++17 with no platform code, so the same source runs offline and on the Daisy Seed3.
- 2026-11-01: Repo is the source of truth for project context; the Claude Hub row in Notion tracks status only.
- 2026-11-01: License GPL-3.0 (was GPL-2.0-only) so WARBL2 (GPL-3) code can be reused, e.g. in the iPad app.
- 2026-11-01: Standard D whistle chart from the Woodwind Fingering Guide (sounding pitch); half-holes as the primary chromatic fingerings.
- 2026-11-01: Playing pitch = minima of the impedance seen at the window (window inertance + bore input impedance); jet pitch shift left to calibration.
- 2026-11-01: Design fit pulls hole diameters weakly toward 6.5 mm (5 cents/mm): position and diameter trade off, and real makers pick finger-sized holes.
- 2026-11-01: Half-hole rows are judged by the coverage needed to reach the target, not by a fixed 50%; players shade until it sounds right.
- 2026-11-01: Calibrate with two numbers (acoustic top of bore, window inertance scale) at 30 °C breath temperature; per-note fudge factors are not allowed.
- 2026-11-01: Real-time model at 96 kHz with 3rd-order Lagrange fractional delays; geometry taken from the impedance-model calibration, not refit to recordings.
- 2026-11-01: STK-style jet as the default for now (reliable first register); physical deflection/tanh jet kept as an experimental option until it starts on long fingerings.
