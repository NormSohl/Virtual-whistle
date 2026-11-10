# virtual-whistle

A physical model of a penny whistle, played from a WARBL, tuned against measurements of a real instrument. First step toward a virtual Renaissance recorder.

**Read the preview, with a video of it being played:** [A virtual penny whistle, played from a WARBL](https://www.sohl.com/2026/11/07/virtual-whistle-preview/) (sohl.com, 2026-11-07).

- Project context and rules: [CLAUDE.md](CLAUDE.md)
- How to measure a real whistle: [docs/measuring.md](docs/measuring.md)
- Design decisions: [docs/decisions.md](docs/decisions.md)
- Roadmap: [docs/roadmap.md](docs/roadmap.md)

Status: phase 6. The model plays live in a browser from a WARBL running the raw-stream firmware fork ([docs/warbl-raw-stream.md](docs/warbl-raw-stream.md)); the C++ engine matches the browser engine, including wall losses, and is ready for the Daisy port. Latest: [code review and breath-rise re-measurement](docs/results/2026-11-09-review.md). Render with `python -m render.synth scale`. Play in a browser: `python web/build.py`, then open `web/play.html` (touch, or a WARBL via Web MIDI). Tools ready: pitch analysis (`python -m analysis.pitch file.wav`), impedance model, design fit. Latest results: [model vs real Generation D](docs/results/2026-11-01-generation-d-vs-model.md). Setup: `pip install -r requirements.txt`, plus g++, node and ffmpeg. Tests: `python -m pytest`.
