# Measuring a real whistle

The measurements and recordings here are the ground truth for the whole project. The impedance model is "right" only when it reproduces these pitches.

## Tools
- Digital calipers (0.01 mm resolution), with depth rod.
- A thin steel rule or a long caliper for overall length.
- Small drill bits or pin gauges (optional) to check hole diameters by fit.
- A quiet room, a decent microphone (an iPad or phone is fine), and a stable breath.
- Masking tape and a fine pen for marking reference points.

## Reference point and conventions
- **Origin (0 mm):** the top end of the whistle body (the mouthpiece end). Measure every position along the body from here.
- **Positions:** to the *centre* of each feature.
- **Diameters:** take two readings at 90° to each other and record both (holes and bores are rarely perfectly round).
- **Units:** millimetres, two decimals where the calipers allow.
- Number the toneholes from the top: hole 1 is nearest the mouthpiece (left-hand index), hole 6 nearest the foot.

## 1. Body and bore
| What | How |
|---|---|
| Total length | Top end to foot end. |
| Bore diameter at the foot | Inside jaws of the calipers, two readings at 90°. |
| Bore diameter at the top (below the fipple head, if removable) | Same. |
| Bore profile (if not obviously cylindrical) | Inside-diameter readings every ~20 mm from the foot as far as you can reach. A cheap tube whistle is usually cylindrical; note any taper or step. |
| Head/body joint | If the head is a separate plastic piece, note where the body tube starts and how far it inserts. |

## 2. Window and windway (the sound-generating end)
| What | How |
|---|---|
| Window length (along the axis) | From the windway exit to the labium edge. |
| Window width | Across the whistle. |
| Windway height at the exit | Depth rod or a feeler gauge; best estimate is fine. |
| Windway width | At the exit. |
| Windway length | From the mouth end to the exit. |
| Position of the labium edge | Distance from the origin. |
| Photos | A close-up straight down onto the window, and one from the side, with a rule in frame. |

## 3. Toneholes (repeat for holes 1-6)
| What | How |
|---|---|
| Position | Origin to the hole centre. |
| Diameter | Two readings at 90°. |
| Wall thickness (chimney height) | At the hole edge, or measure outside diameter of the tube and subtract the bore. |
| Shape notes | Oval, undercut, chamfered, burr? |

## 4. Recordings
Record each item as its own short file, or one long file with a spoken label before each note. WAV or M4A both work.

- **Fingerings:** every fingering you use, in both registers, including half-holes and forked/cross fingerings. Hold each note steadily for 3 seconds.
- **Breath sweep:** for three fingerings (all closed, half open, all open), start very soft and slowly blow harder until the note jumps to the next register, then back down. This shows how pitch moves with breath and where the register breaks are.
- **Label** each fingering as a 6-character pattern from hole 1 to hole 6, `x` closed, `o` open, `h` half, e.g. `xxxooo`.
- Note the room temperature: pitch rises about 3 cents per °C.

## 5. Put it in the repo
- Fill in `data/<whistle-name>/geometry.csv` and `data/<whistle-name>/fingerings.csv` from the templates in `data/template/`.
- Put recordings in `data/<whistle-name>/recordings/`, photos in `data/<whistle-name>/photos/`.
- Or just attach everything in the Claude app and Claude will file it.
