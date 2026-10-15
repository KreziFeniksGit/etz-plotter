# Stiffness, sag, backlash and belt review (v2.7, 12 Oct 2026)

Egor asked: check every part for sagging and bending, check backlash, make the belt attachments work with an
open (cut) belt instead of a closed loop, look at ready-made parts, and fix `y_motor_mount` and `x_motor_mount`.

## How it was checked
- **Printed parts under load: FEA** (`tools/fea.py`, results in `out/fea.json`). Each part is meshed with gmsh and solved with
  CalculiX (both come with FreeCAD). What the part holds (motor, idler axle, post) is a rigid body bolted to it; the belt pull
  and the weights act where they really act. PETG E = 1500 MPa (printed, below solid 2000).
  Loads: belt 25 N per strand = 50 N on every pulley and idler, motor weight, 2 m/s2 on the Y carriage.
  Targets: pulley or idler moves < 0.10 mm and tilts < 0.25 deg, magnet moves < 0.2 mm, stress < 8 MPa.
- **Aluminium profiles, tipping, rail loads:** `tools/stability.py` as before.
- **Backlash:** new budget in `tools/stability.py` (`backlash` in `out/stability.json`).

## Results: before (v2.6) and after (v2.7)
| Part | v2.6 move / tilt / stress | v2.7 move / tilt / stress | What changed |
|---|---|---|---|
| x_motor_mount | 0.085 mm / 0.20 deg / 4.4 MPa (borderline; ~0.4 deg after creep) | 0.012 mm / 0.027 deg / 1.2 MPa | 6 mm plate, top and bottom flanges, each arm also bolted to the post's -x face |
| y_motor_mount | 0.029 mm / 0.05 deg / 3.3 MPa, but tension held only by friction of 2 wood screws in slots | 0.011 mm / 0.014 deg / 1.4 MPa | 6 mm plate, base both sides, 4 gussets, 4 fixed screws, no slots |
| x_idler_bracket | **0.133 mm / 0.65 deg / 14.2 MPa: fails** | 0.039 mm / 0.11 deg / 6.5 MPa | 6 mm side plate, slider + M3 push screw (in line with the axle) takes the belt pull |
| y_idler_bracket | 0.047 mm / 0.06 deg / 3.5 MPa | 0.035 mm / 0.03 deg / 3.6 MPa | 6 mm plate, slider + M3 push screw |
| y_carriage (post socket) | magnet moves 0.10 mm | 0.10 mm (unchanged part) | fine as it is |

PETG creeps under a constant load, so expect about twice these numbers after weeks under belt tension. Even doubled,
every part stays inside the targets now. The new X idler bracket is a channel (side plate, top flange, lug, end wall) on a
12 mm end cap; its slider and plate sit above z 155 because the wrist harness passes under them at X 380..410 (the old 4 mm
plate was in its way there too; the 54-pose sweep had no pose at those X values). The worst part was not one in the photos: the X idler bracket's 4 mm side plate
carried the idler on a cantilever and held the belt only by the friction of the axle nut.

## Open belts (not a loop)
Both belts are now open lengths with both ends clamped on the carriage they drive:
- **Y:** `y_belt_clamp` + `y_belt_spacer` run the full carriage width (y 40..70 at park), 3 M3 screws into inserts in the
  carriage. The two ends meet over the middle screw with a 2 mm gap; each end sits in 6 tooth grooves.
- **X:** `x_belt_riser` + `x_belt_clamp` on the wrist carriage are 42 mm long (were 26), 3 M3 screws. Ends meet over the
  middle screw; 9 teeth each.
- Belt to cut: Y about 0.92 m, X about 0.67 m (path length plus a little; trim after the first clamp). 1.6 m total, the BOM's 2 m is enough.

**Tensioning (both axes now work the same way):** the idler sits on a slider, the motor never moves.
1. Clamp one belt end, run the belt round the motor pulley and the idler, pull it hand-tight and clamp the other end.
   The tooth grooves set the length in 2 mm steps.
2. Y: turn the M3 push screw in the lug at the Y idler (`y_idler_bracket`), it pushes the slider and idler toward -y
   (3 mm travel = 6 mm of belt). Lock it with its hex nut.
   X: turn the M3 push screw in the lug at the -x end of the idler side plate (`x_idler_bracket`); it pushes the slider and
   idler toward +x (6 mm of travel). Lock it with its hex nut.
3. Target about 25 N per strand: pluck a free strand and read it with a phone tuner app. f = sqrt(T / m) / (2 L) with
   m about 7.7 g/m for 6 mm GT2: Y: carriage parked, the 390 mm strand from the clamp to the motor pulley rings at about
   70 Hz. X: wrist parked, the 200 mm strand from the clamp to the idler, about 140 Hz. Snug the idler axle nut (do not clamp it hard: the screws hold the tension).
4. Assembly order: the X idler axle head sits between the boom and the idler, so put the idler, axle, slider and nyloc on the
   bracket **before** bolting the bracket to the boom. The Y motor mount's -x screws sit under the motor: screw the mount down
   first, then bolt the motor on from the pulley side.

## Backlash budget (`out/stability.json` -> `backlash`)
Lost motion when an axis reverses at the design acceleration, worst carriage position:

| Axis | Moving mass | Belt stretch | Stepper load angle | Printed mount | Tooth clearance | Total on reversal |
|---|---|---|---|---|---|---|
| Y | 1.48 kg | 0.026 mm | 0.005 mm | 0.001 mm | 0.05 mm | 0.11 mm |
| X | 0.46 kg | 0.006 mm | 0.002 mm | 0.000 mm | 0.05 mm | 0.07 mm |

The placement tolerance is 10 mm, so XY backlash is ~100 times smaller than what matters. What could make it worse, and what
prevents it:
- a pulley slipping on its shaft: use pulleys with two grub screws, one on the shaft flat, a drop of Loctite 243;
- a slack belt: tension as above, re-check after the first hour of running (PETG and the belt settle);
- missed steps (a crash): homing every run, StallGuard can detect it.
The MG996R's gear play (about 1 deg, VERIFY on yours) moves the magnet only up and down by about 1.4 mm; the parallelogram keeps it
level and it lands on the checker anyway. The wrist rotation is direct-drive (NEMA17 pancake on a D-shaft since v2.8; was a NEMA11), no gear play.

## Ready-made parts looked at
| Option | Verdict |
|---|---|
| Stamped steel NEMA17 L-bracket (3 mm steel) for the Y motor | Stiffer than any print and no creep, but its shaft height (about 22-26 mm over the foot) does not match ours (31.5 mm); would need a printed spacer. Kept the printed mount: the FEA says it is now 10x inside the target. Good spare plan. |
| Aluminium 2020 belt tensioner with 20T idler (Ender-3 V2 / S1 X-axis type) | Made for a belt centred on the profile end; ours runs beside the beam (Y) and beside the boom (X), so it does not fit without moving the belt planes. Not used. |
| Aluminium GT2 belt clamp plates (toothed, 2 screws) | Would replace the printed clamps one for one if the printed teeth ever slip. The printed ones have 6-9 teeth per end, which is plenty for 25 N. |
| Spring belt tensioners (wire spring clip) | Not used: the spring lets the carriage move on reversal = backlash. |
| Gates PowerGrip GT2 belt | Recommended (already in the BOM): less stretch than generic fibreglass belts. |
| GT2 20T pulley with two grub screws, toothless idler with bearings | Already in the BOM; buy the two-grub-screw version. |

## Print the load-carrying parts stiffer
`x_motor_mount`, `y_motor_mount`, `x_idler_bracket`, `x_idler_slider`, `y_idler_bracket`, `y_idler_slider`, `y_carriage`:
PETG, 6 walls, 50 % gyroid or more, 0.2 mm layers. The FEA modulus assumes about this.
The idler sliders and the motor mounts print with the load in the layer plane (see `out/printed/`).

## Not changed / limits
- The post-to-boom joint is two cast corner brackets: metal, not checked by FEA; the profile sag is in `stability.py` (0.04 mm).
- The FEA is linear and holds the parts where they are screwed; real joints are a little softer. Numbers are for comparing designs and
  checking the margin, not exact values.
- Belt stiffness EA = 25 kN is a typical figure for 6 mm glass-cord GT2 (not measured).
