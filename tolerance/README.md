# Tolerance test coupons

Print these before the real parts, on the same printer with the same PETG, nozzle and slicer profile
(0.2 mm layers, 4 walls, 40 % gyroid, no supports, no hole-size compensation in the slicer).
Each coupon lies in its print orientation: load the STEP into the slicer and print it as it comes.

Every row has three variants (tight, **model value in the middle**, loose), engraved on the coupon.
Pick the variant that fits as described below, then change the constant at the top of
`wrist/wrist_module.py` (section 1). Every part that uses it changes with it; re-run `export_gui.py`.

Bring the real parts to the test: screws M2..M5, a Ruthex M3 insert, a 684ZZ bearing, the 3 x 2 magnet,
the wrist NEMA17 pancake (17HS4023S) and a NEMA17, the RDS3235 servo, a piece of 2020 V-slot profile, a nylon spacer,
zip ties, the stop button, start button and an LED holder.

**Print first (under 90 g at full density):** A, C, D1, E1, F1. The others (about 100 g) when you have the parts.

**Results so far (Egor, 16 Oct), already in the model:**
| Test | Result | Constant now |
|---|---|---|
| A, B M2 / M2.5 / M3 | +0.15 | `TOL_BOLT` 0.15 |
| A, B M4 / M5 | +0.15 too loose | `TOL_BOLT_D` 0.05 until A2 is printed |
| C inserts | 4.1 | `INSERT_D` 4.1 |
| D2 hubs | 0.18 | `TOL_DBORE` 0.18 |
| E1 NEMA17 | +0.10 | `TOL_MOTOR` 0.10 |
| F2 sleeve | 20.2 slides but jams at the end: too tight | `SOCKET_GAP` stays 0.2 (20.4): try that one |
Still to print: **`tol_H_next_A2_D1_F2`** (one file: A2 M4/M5 holes, D1 684ZZ seat, F2 V-slot tongues; the F2 sleeves were measured and are left out), F1 (`tol_F1_servo_rds3235`, new servo), F3, G, E2, D2 pins.

| Coupon | Tests | Pass | Constant (model value) |
|---|---|---|---|
| A `tol_A_bolt_holes_vertical` | M2, M2.5, M3, M4, M5 clearance holes printed vertical; columns +0.05 / +0.15 / +0.25 | the smallest hole the screw drops through without turning | `TOL_BOLT` (0.25) |
| A2 `tol_A2_bolt_holes_m4_m5` | M4 and M5 only, +0 / +0.05 / +0.10: plate (vertical holes) and bar (horizontal) | same as A | `TOL_BOLT_D` (M4, M5: 0.05) |
| B `tol_B_bolt_holes_horizontal` | M3, M4, M5 holes through a standing wall (like the socket and motor-mount holes) | same as A; if B needs a bigger step than A, take the bigger one | `TOL_BOLT` |
| C `tol_C_inserts` | insert holes 3.8 / 3.9 / 4.0 / 4.1, 6.5 deep | the insert goes in straight with the iron, sits flush, little plastic pushed up, and an M3 screw tightened firmly does not spin it | `INSERT_D` (4.0) |
| D1 `tol_D1_press_bearing` | 684ZZ seat (with the 7.6 shoulder hole as in the arms); columns +0.06 / +0.12 / +0.18 | bearing: pressed in with a vice or clamp, flush, no wobble, still spins freely | `TOL_PRESS` (0.12) |
| D2 `tol_D2_press_dbore_pins` | D-bore hubs on the wrist stepper shaft (NEMA17 pancake, 5 mm D); pins for the 2020 centre hole (post cap) | hub: pushed on by hand with firm force, does not turn on the shaft, no rocking. Pin: pushed in by hand, holds the cap | `TOL_PRESS` |
| E1 `tol_E1_nema17` | NEMA17 pilot 22 and M3 holes on 31 mm; +0.0 / +0.1 / +0.2 | the motor sits flat with the pilot in, no forcing, all four screws go in without bending sideways | `TOL_MOTOR` (0.2) |
| E2 `tol_E2_nema17_pancake` | wrist NEMA17 pancake: pilot 22 and M3 holes on 31 mm (same pattern as E1; try it on the pancake itself, whose boss and threads may differ) | same as E1 | `TOL_MOTOR` |
| F1 `tol_F1_servo_rds3235` | RDS3235 face mount, 3 plates: horn hub hole gap 0.3 / 0.4 / 0.5 per side, M2 holes +0.05 / +0.15 / +0.25, heads sunk 2.5 | screw the servo on with 3x M2x5: the screws line up and go in by hand; press the horn on through the hole: it turns freely without touching | `TOL_MOVE` (0.4), `TOL_BOLT` (M2) |
| F2 `tol_F2_profile_socket_tongue` | sleeves 20.2 / 20.4 / 20.6 on the 2020 profile; V-slot tongues (the slot mouth shape, 0.1 / 0.2 / 0.3 smaller per side) like the beam risers | sleeve: slides on by hand all the way, no visible play. Tongue: slide a 2020 along it: no catching, little side play | `SOCKET_GAP` (0.2 per side), `VTONGUE_GAP` (0.2) |
| F3 `tol_F3_spacer_ziptie_pilot` | spacer holes 7.4 / 7.6 / 7.8; zip-tie slots 3 x 1.8 (left, model), 3.4 x 2.1, 3.8 x 2.4; M2 pilots 1.6 / 1.8 / 2.0, 5 deep | spacer: drops in and turns freely. Zip tie: passes without forcing. M2 screw: cuts its thread, holds when tightened, does not split the plastic | `SPACER_GAP` (0.3), `ZIP_SLOT` (3.0, 1.8), `M2_PILOT` (1.8) |
| G `tol_G_panel_holes` | stop button 22, start button 16, LED holder 6; +0.15 / +0.25 / +0.35 | the part goes in by hand, does not rotate when its nut is tightened | `TOL_PANEL` (panel holes are d + TOL_PANEL) |

If the best fit is the tightest or loosest variant, it may lie further out: set the constant one more step
in that direction and print that coupon again (`../fcpy coupons.py tol_A_bolt_holes_vertical` (Windows: `..\fcpy.bat coupons.py ...`) regenerates
just one coupon from the new value).

Things the coupons do not test: the belt clamp grip (print the real `x_belt_riser` + `x_belt_clamp`, 9 g,
and pull the belt), and the fit of bought parts whose sizes are still marked VERIFY (servo, magnet thread,
camera board, chain end links): measure those with calipers.

`out/coupon_dfm.json` has the print-rule check of every coupon (walls >= 2.4, no sharp internal corners,
no overhang > 45 deg, no bridges; checked without the engraved labels, which are 0.6 mm deep and cosmetic).
