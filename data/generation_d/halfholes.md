# Half-holes (2026-11-01, `2026-11-01_halfholes.m4a`)

Norm played slow glissandi from each closed-hole note to the next, pausing at a "half-hole" position (narration in the transcript alongside). Pitches from `analysis.pitch`, first register.

Where the held half-hole positions landed, as a fraction of the interval between the closed and open notes (in cents):

| Hole shaded | Closed note | Open note | Interval | Held half-hole | Fraction of interval |
|---|---|---|---|---|---|
| 6 (D to E) | 594.8 Hz | 666.7 Hz | 197 c | 646.7-655.1 Hz | 74-85 % |
| 5 (E to F#) | 668 Hz | 740 Hz | 177 c | 713 Hz | 63 % |
| 4 (F# to G) | 750 Hz | 800 Hz | 112 c | 781.9 Hz | 64 % |
| 3 (G to A) | 803 Hz | 901 Hz | 199 c | 853-875 Hz | 53-75 % |
| 2 (A to B) | 901 Hz | 1030 Hz | 232 c | 962-996 Hz | 49-74 % |
| 1 (B to C#) | 1030 Hz | 1148 Hz | 188 c | 1112-1120 Hz | 70-76 % |

## What this does and doesn't test
- Pitch moves smoothly and continuously with shading on every hole: good news for continuous WARBL control.
- The model can't be checked quantitatively here, because how much of each hole was uncovered is unknown. The model says 50 % open area gives ~85 % of the interval; Norm's half-hole positions sit at ~50-85 %, which fits covering a bit more than half, but proves nothing either way.
- A controlled check would be masking tape covering a known fraction of one hole (e.g. half its diameter), recorded against the open and closed notes.
