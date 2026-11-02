# virtual-whistle

A physical model of a penny whistle, played from a WARBL, tuned against measurements of a real instrument. First step toward a virtual Renaissance recorder.

- Project context and rules: [CLAUDE.md](CLAUDE.md)
- How to measure a real whistle: [docs/measuring.md](docs/measuring.md)
- Design decisions: [docs/decisions.md](docs/decisions.md)

Status: phase 1 (measuring a real whistle). Tools ready: pitch analysis (`python -m analysis.pitch file.wav`), impedance model, design fit. Latest results: [docs/results/2026-11-01-generic-d.md](docs/results/2026-11-01-generic-d.md). Tests: `python -m pytest`.
