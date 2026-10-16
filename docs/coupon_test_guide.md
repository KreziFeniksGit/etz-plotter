# Tolerance coupons: what to bring and exactly what to do

Every coupon is a small test print with each fit made 3 ways: **tight / model value (middle) / loose**.
The value is engraved next to each hole. You find which one fits best, tell Claude, and every part gets
re-made with that size before you print the real parts.

## 1. Print settings (use the same ones for the real parts later)
- PETG, 0.4 nozzle, **0.2 mm layers, 4 walls, 40 % gyroid infill, no supports**.
- Slicer: **turn OFF any hole / XY size compensation** (Orca/Bambu: "X-Y hole compensation" = 0; Prusa: "XY size compensation" = 0).
- Load the STEP from `tolerance/out/` (the `.step` files, not the old `.stp` ones) and print it as it lies. Don't rotate it.
- Print first: **A, C, D1, E1, F1** (under 90 g together). The rest when you have the parts.

## 2. Shopping / bring list
| Coupon | You need |
|---|---|
| A, B (bolt holes) | 1 screw each: M2, M2.5, M3, M4, M5 (any length 10-20 mm) |
| C (inserts) | 4x Ruthex M3 x 5.7 inserts, soldering iron (insert tip if you have one), 1x M3 x 10 screw, a flat metal plate or the iron's flat tip |
| D1 (bearing) | 1x 684ZZ bearing, a vice or a big clamp (or two pieces of wood + a hammer, gently) |
| D2 (press pins) | NEMA17 pancake motor 17HS4023S (its 5 mm D-shaft), a short piece of 2020 V-slot |
| E1 | NEMA17 motor 17HS16-2004S1 + 4x M3 x 8 |
| E2 | NEMA17 pancake 17HS4023S + 4x M3 x 8 |
| F1 | MG996R servo |
| F2 | a short piece of 2020 V-slot (50-100 mm) |
| F3 | 1 nylon spacer 4.2 x 7 x 3, 2-3 zip ties (2.5-3 mm wide), 3x M2 x 6 (or x 8) self-tapping screws, small Phillips screwdriver |
| G | 22 mm stop button, 16 mm start button, 6 mm LED holder (with their nuts) |
| all | calipers, a pen, your phone (take a photo of each result) |

## 3. Exactly what to do, coupon by coupon
Write down the engraved number of the winner for each row.

**A and B, bolt holes.** Push each screw straight through its holes, from the tightest to the loosest.
Winner = the smallest hole the screw drops through (or slides through with a finger push) **without turning it**.
If B's winner is bigger than A's, report both.

**C, inserts (3.8 / 3.9 / 4.0 / 4.1).** Iron at about 230 °C (PETG). Put an insert on each hole and press it in
slowly and straight with the iron, until it is flush; then press it flat with the cold plate while it cools (5 s).
Wait 2 min, then screw the M3 in and tighten firmly. Winner = goes in straight, sits flush, little plastic
pushed up, and **does not spin** when tightened. (Too loose a hole spins; too tight a hole pushes a ring of plastic up.)

**D1, bearing seat.** Press the 684ZZ into each seat with the vice (flat jaws, slowly). Winner = goes in
**flush, does not wobble, still spins freely** with a finger. If it falls in by itself, it is too loose.

**D2, D-bore hubs and pins.** Push each hub onto the pancake motor's shaft by hand, firmly. Winner = goes on
with firm force, **does not turn on the shaft and does not rock**. Pins: push each into the 2020 centre hole.
Winner = goes in by hand and holds the coupon when you lift the profile.

**E1 and E2, motor pilots.** Put the motor's round pilot boss into each pattern and fit the 4 screws.
Winner = motor sits **flat with the pilot in, no forcing, all 4 screws go in without bending** sideways.

**F1, servo window (gap 0.3 / 0.4 / 0.5).** Slide the MG996R into each window. Winner = slides in by hand
without forcing, tabs sit flat, **does not rattle** when you shake it.

**F2, profile.** Sleeves: slide each onto the 2020 profile. Winner = slides on by hand, **no visible play**.
Tongues: slide each along the V-slot. Winner = slides the whole length **without catching**, little side play.

**F3, spacer, zip ties, M2 pilots.** Spacer: winner = drops in and turns freely. Zip tie: winner = passes
through **without forcing** (the left one is the model value). M2 pilots (1.6 / 1.8 / 2.0): drive a screw into each;
winner = cuts its thread, **holds when tightened, does not split** the plastic. This one now also sets the servo screws.

**G, panel holes.** Fit each button / holder and tighten its nut. Winner = goes in by hand and **does not rotate**
when the nut is tightened.

## 4. Send back
One line per coupon: `A: M3 0.25, M4 0.25, M5 0.35 / C: 4.0 / D1: 0.12 / ...` plus photos if something looked odd.
If the winner is the tightest or loosest of its row, say so: the best size may be further out and that coupon gets
re-made one step further and printed again.
