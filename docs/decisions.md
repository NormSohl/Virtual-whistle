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
- 2026-11-01: Jet delay lengthens at a limited rate (0.003 samples/sample): releases stop the note instead of sweeping it through the lower register.
- 2026-11-01: WARBL raw stream: CC 106 = 79/80/81 on channel 7, 27-byte SysEx frames every main-loop pass with unfiltered hole readings and pressure; calibration frame carries full-cover readings and ambient. Firmware fork based on upstream main 4.8 (runtime BMP/Honeywell detection).
- 2026-11-01: Two kinds of model: character models match real instruments (Generation D stays unchanged); an ideal whistle uses the same physics with geometry optimized for playability, and drives CV/MPE output.
- 2026-11-01: Ideal whistle fingering: thumb hole is an acoustic register vent (open = second octave at the same breath, vent chosen per fingering like keywork); R4 pinky closes a seventh hole for a whole tone below the tonic.
- 2026-11-01: Model holds up to nine holes in fixed storage (no heap), numHoles per instrument, holes in bore order; which WARBL sensor drives which hole is a control-layer mapping, so a thumb vent can sit anywhere along the bore.
- 2026-11-07: Hole filter keeps one form from open to fully closed. The separate first-order closed form dumped the open form's slow-pole state into the bore as a click every time a hole closed (up to 5x the note peak). Below the leak level the slow pole stops at s = -1 rad/s and a zero meets it, so a closed hole is the old closed response with nothing to switch. See [results/2026-11-07-closing-click.md](results/2026-11-07-closing-click.md).
- 2026-11-07: Hosts ramp hole openness every model sample (page engines, both renderers); breath stays at block rate. The hole filter changes fastest in the last per cent of closing, where 32-sample steps also click. Cost in JS: 15 % of a core with all six holes moving every sample, far less in real playing. On the Daisy, every 4 samples is the fallback if it costs too much.
- 2026-11-07: Play page: Record saves the model's audio (float WAV) and the controls it used (renderer CSV), so live takes can be replayed and measured offline; the stream-health readout counts frames from one MIDI input only.
- 2026-11-07 (experiment, off by default): wall losses in the JS model (`wallLoss`, `wallReleaseOnly`) and a page selector, to judge by ear whether the model's long note tails (Q ~630 vs ~60 real) should be fixed with physical wall losses (needs a jet refit) or a release-only stopgap. Not in the C++ engine yet. See [results/2026-11-07-release-tail.md](results/2026-11-07-release-tail.md).
- 2026-11-07: Wall-loss refit kept as a preset in the repo but not on the page: it matches the scale, breath rise and release better than Generation D but notes fail to start at most breaths (jet gain at its minimum). Page stays Off / Release only. See [results/2026-11-07-wall-loss-refit.md](results/2026-11-07-wall-loss-refit.md).
- 2026-11-07: Fit score gains a tongued-start test (40 starts across each note's breath range). Wall-loss preset run 6 passes it and goes on the page as "Wall losses (retuned)"; its pitch rises 51/84 cents with breath on D/G (Generation D 12/34, real ~10/18).
