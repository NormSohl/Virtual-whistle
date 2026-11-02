# Generation D (brass, red head) — Norm's whistle

## Photos (2026-11-01)
`photos/`: angled overview, top view, window close-up, foot end looking into the bore, head side profile.

## Measurements so far
- Overall length 11 5/8 in = 295.3 mm (Norm).
- Bore 11.8 mm (Norm, calipers).
- Everything else in `geometry_photo_estimate.csv` is **estimated from the top-view photo**, scaled to the 295.3 mm overall length: hole positions ±2 mm, hole diameters ±0.7 mm, window size rough. Hole 4 looks smallest, holes 5-6 largest.

## What the photo estimate says (impedance model, A4 = 440 Hz, 25 °C)
With the photo geometry the model's diatonic notes scatter by ±35 cents (sd), and no single window calibration fixes it: F# lands flat and C# sharp. Hole position errors of 2 mm and diameter errors of 0.7 mm are enough to cause this, so the photo estimate can't separate model error from measurement error. **Caliper measurements are needed** before calibrating.

Consistency check: the photo gives a bore length (window centre to foot) of ~266 mm; the model's independently designed generic D whistle came out at 268 mm.

## Caliper measurements, first pass (2026-11-01)
In `geometry_measured.csv`. Hole diameters 4.45-6.0 mm; hole 1 and hole 4 smallest.

Model check (window position still taken from the photo, A4 = 440, 25 °C, nominal 12-TET targets, no recordings yet): diatonic notes scatter by about ±20 cents (sd); top notes B and C# come out ~30-35 cents sharp, F# ~20 flat. Hole 4 as measured puts G ~23 cents flat; at the photo's even-spaced position G goes ~20 sharp, so hole 4's position needs rechecking. Fitting the unknown window position and window correction as free parameters only gets to ~16-19 cents sd. Not conclusive until: hole 4 rechecked, window position measured, and recordings show how this whistle actually plays.

## Window position measured (2026-11-01)
Labium edge 263.5 mm from the foot (10 3/8 in ±1/32). Window 5.0 x 7.7 mm.

Model check with all measured geometry (A4 = 440, 25 °C, no recordings yet):
- Reference at the labium: mean +16 cents, sd 24. Reference at the window centre: mean -5, sd 21. The model's acoustic top of the bore sits somewhere in the window; calibration against recordings will pin it.
- Hole 4 as measured (73.75 mm): F# and G come out equally flat (-13, -15 at the labium reference), which looks self-consistent; the even-spaced alternative puts G ~45 cents above F#. Leaning toward the measured value.
- Remaining outlier: B and C# (top two holes open) sit ~45-60 cents above the rest in both octaves. Either this whistle really plays its top notes sharp, holes 1-2 positions/sizes are off, or the head piece's inner bore differs from the brass. Recordings decide.
