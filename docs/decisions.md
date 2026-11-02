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
- 2026-11-01: Physical flue jet (deflection by window flow, convective delay, tanh labium split, dipole source, Strouhal-limited band) replaces the STK-style jet as default; second octave comes from steady breath, no attack kick.
- 2026-11-01: Target is a better-sounding instrument than Norm's Generation, not an imitation of its flaws; the measured Generation is the calibration reference only.
- 2026-11-01: Open holes and window radiate through end-correction mass in parallel with rho c / S (radiation resistance), not a pure inertance; jet input is DC-blocked and the window leaks static pressure.
- 2026-11-01: Tongued attacks 8 ms: slow breath ramps start second-octave notes in the first register.
- 2026-11-01: Fingering changes ramp over ~20 ms (real fingers aren't instantaneous; instantaneous filter switches click).
- 2026-11-01: Browser version: web/whistle-model.js is a line-for-line JS port of dsp/whistle.hpp (renders the test scale identically: 0.0 cents, 0.0 dB per note); web/play.html runs it in an AudioWorklet at 2x oversampling (96 kHz model on 48 kHz devices) with 15 ms finger and 8 ms breath ramps.
