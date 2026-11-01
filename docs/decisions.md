# Design decisions

One line each: date, decision, reason.

- 2026-11-01: Start with a penny whistle before recorders. Simple, well-understood bore; proves the pipeline end to end.
- 2026-11-01: Real measured whistle is ground truth. Claude can't hear; every tuning claim must cite measured numbers.
- 2026-11-01: Two-stage tuning: fast impedance model for design and optimization, then calibrate the time-domain synth against its own measured pitch.
- 2026-11-01: DSP core in portable C++17 with no platform code, so the same source runs offline and on the Daisy Seed3.
- 2026-11-01: Repo is the source of truth for project context; the Claude Hub row in Notion tracks status only.
