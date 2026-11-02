# virtual-whistle

A physical model of a penny whistle, played from a WARBL, tuned against measurements of a real instrument. First step toward a virtual Renaissance recorder.

- Project context and rules: [CLAUDE.md](CLAUDE.md)
- How to measure a real whistle: [docs/measuring.md](docs/measuring.md)
- Design decisions: [docs/decisions.md](docs/decisions.md)
- Roadmap: [docs/roadmap.md](docs/roadmap.md)

Status: phase 3 (real-time model) started; latest: [octave break from steady breath](docs/results/2026-11-01-octave-break.md). Render with `python -m render.synth scale`. Play in a browser: `python web/build.py`, then open `web/play.html` (touch, or a WARBL via Web MIDI). Tools ready: pitch analysis (`python -m analysis.pitch file.wav`), impedance model, design fit. Latest results: [model vs real Generation D](docs/results/2026-11-01-generation-d-vs-model.md). Tests: `python -m pytest`.
