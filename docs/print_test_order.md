# Print and test order

Build the plotter one subsystem at a time, and test each one before printing the next, so a bad fit
or a weak part shows up early and costs one print instead of the whole set.
All printed models are STEP files in `out/printed/` (already in print orientation). For the whole
device as a reference while assembling, open `out/ETZ_plotter_parked.FCStd` (or `.step`) in FreeCAD.

Print settings: PETG, 0.4 nozzle, 0.2 mm layers, no supports, no hole compensation.
Load parts (motor mounts, idler brackets, carriages, risers, arms) get 6 walls and >= 50 % infill;
trays and panel can use 4 walls, 20-30 %.

---

## Step 0. Tolerance coupons and the belt grip
**Why:** every hole, press fit and slot in the real parts uses these constants. If they are wrong,
everything after this is wrong.

| Print (`tolerance/out/`) | Bring |
|---|---|
| First: `tol_A_bolt_holes_vertical`, `tol_C_inserts`, `tol_D1_press_bearing`, `tol_E1_nema17`, `tol_F1_servo_window` | M2..M5 screws, Ruthex M3 insert + soldering iron, 684ZZ bearing, NEMA17 (17HS16), MG996R |
| Then: `tol_B_bolt_holes_horizontal`, `tol_D2_press_dbore_pins`, `tol_E2_nema17_pancake`, `tol_F2_profile_socket_tongue`, `tol_F3_spacer_ziptie_pilot`, `tol_G_panel_holes` | pancake 17HS4023S, a piece of 2020 V-slot, nylon spacer, zip ties, stop/start buttons, LED holder |
| Belt grip test: `out/printed/wrist_x_belt_riser.step` + `wrist_x_belt_clamp.step` | GT2 belt scrap, 2 Ruthex inserts, 3x M3x10 |

**Test:** follow `tolerance/README.md` (pick the variant that fits). Pull the belt hard by hand: it must not slip.
**Then:** tell Claude the winning variants. The constants get updated and every part is re-exported
before you print Step 1. Also measure the VERIFY parts with calipers (list in `docs/status.md`, open item 2).

---

## Step 1. Base and Y axis (the first moving axis)
**Goal:** the Y carriage runs the full 336 mm smoothly, homes the same way every time, and moves the
distance you command.

| Printed (`out/printed/`) | Qty |
|---|---|
| `y_beam_riser_x4` | 4 |
| `y_motor_mount` | 1 |
| `y_idler_bracket` | 1 |
| `y_idler_slider` | 1 |
| `y_carriage` | 1 |
| `y_belt_clamp` | 1 |
| `y_belt_spacer` | 1 |

| Bought | Qty |
|---|---|
| Plywood 6 mm 250 x 470 (cut from `out/plywood_base.dxf`) + 4 printed feet (`foot_x4`) | 1 |
| 2020 V-slot 400 mm (Y beam) | 1 |
| MGN12 rail 400 + MGN12H block | 1 |
| NEMA17 17HS16-2004S1 | 1 |
| GT2 20T pulley, GT2 20T toothless idler, GT2 6 mm belt ~0.92 m | 1 each |
| Omron D2F-01L home switch | 1 |
| Screws: M5x20 + M5 T-nuts (beam), M3x8 + M3 T-nuts (rail), M3x8 (carriage to block), M3x10 (motor), M5x25 + nut (idler axle), M3x16 + nut (tension), M3x14 + inserts (belt clamp), M5x12 (idler bracket, tap the beam end M5), wood screws 4x10 and 3.5x12 | see `out/fastener_bom.csv` |
| Test electronics (on the breadboard, loose): ESP32-S3 board, 1x TMC2209, LiPo + 5 A fuse + XT60, 5 V regulator | 1 each |

**Tests:**
1. By hand, motor belt off: the carriage slides the whole length with no tight spots.
2. Tension the belt with the idler slider screw (about 25 N per strand, `docs/stiffness_review.md`): plucked, it should "twang", not flap.
3. Powered: move 100 mm, mark, move back, 10 times. Repeat homing 10 times. Spread of the marks should be well under 1 mm.
4. Command 300 mm and measure with a ruler: set steps/mm (40 mm per motor turn).
5. Push the carriage back and forth against the motor holding torque and watch for play (backlash budget is 0.11 mm).

---

## Step 2. Post, boom and X axis
**Goal:** X runs its full travel square to Y, the boom does not sag or wobble when the carriage moves fast.

| Printed (`out/printed/`) | Qty |
|---|---|
| `post_cap` | 1 |
| `x_motor_mount` | 1 |
| `x_idler_bracket` | 1 |
| `x_idler_slider` | 1 |
| `wrist_wrist_carriage` (the plate on the X block; the wrist hangs on it later) | 1 |
| `wrist_x_belt_riser`, `wrist_x_belt_clamp` (reuse the Step 0 ones if the grip passed) | 1 each |

| Bought | Qty |
|---|---|
| 2020 V-slot 130 mm (post) and 270 mm (boom) | 1 each |
| Soberizavod 20x20 corner brackets + M5x8 + T-nuts | 2 |
| MGN12 rail 250 + MGN12H block | 1 |
| NEMA17 17HS16-2004S1, GT2 pulley, idler, belt ~0.67 m | 1 each |
| Omron D2F-01L home switch | 1 |
| Screws: M5x10 + T-nuts (post socket), M5x16 / M5x12 (motor mount to post), M5x12 (idler bracket, tap the boom end M5), M5x30 + nyloc (idler axle; fit it before the bracket goes on), M3x8 + T-nuts (rail), M3x6 (plate to block), M3x25 + nut (tension) | see `out/fastener_bom.csv` |
| 2nd TMC2209 on the test breadboard | 1 |

**Tests:**
1. Check the boom is square to Y (set square on the rails) before tightening the brackets fully.
2. Same as Step 1: smooth by hand, tension, repeatability, homing, steps/mm on X.
3. Run X and Y together, diagonal moves at full speed: watch the boom tip for shaking. Draw a 100 mm square with a pen taped to the carriage and measure the diagonals (should match within ~1 mm).

---

## Step 3. Wrist module (lift, rotation, magnet)
**Goal:** the magnet face moves 5..40 mm level, the wrist turns any angle, the magnet picks a checker and lets it go.
Tip: build it on the `wrist_wrist_carriage` on the bench first (carriage off the X block), then mount it.

| Printed (`out/printed/`) | Qty |
|---|---|
| `wrist_chain_post` | 1 |
| `wrist_arm_top` | 1 |
| `wrist_arm_bottom` | 1 |
| `wrist_end_plate` | 1 |
| `wrist_shelf` | 1 |
| `wrist_wrist_hub` | 1 |

| Bought | Qty |
|---|---|
| MG996R servo + 25T aluminium single-arm horn | 1 |
| 684ZZ bearings, nylon spacers 4.2x7x3, shim washers 4.2x7x0.8 | 3 each |
| NEMA17 pancake 17HS4023S | 1 |
| P20/15 electromagnet 5 V, AO3400 MOSFET, 1N5819 diode | 1 each |
| Screws: M2x8 self-tapping + large washers (servo tabs), M4x30 / M4x20 + nylocs + washers (pivots), M3x8 button (pancake), M3x6 button (horn centre), M3x8 set screw + insert (magnet stud), M3x10 button (arm to horn), M3x10 + inserts (shelf, chain post) | see `out/fastener_bom.csv` |
| 6 V regulator, 3rd TMC2209 (wrist, 0.6 A) | 1 each |
| A few test checkers | |

**Tests:**
1. By hand, servo horn off: the parallelogram moves up and down freely with no play at the pivots.
2. Servo sweep: measure the magnet face height at each end (5 and 40 mm) and set the servo pulse limits; check the face stays level.
3. Wrist: turn 360 deg and back 10 times to your hand-set mark (there is no wrist home sensor): it should come back to the mark.
4. Magnet: pick a checker from the table, lift to 40 mm, shake the carriage, drop. Then stack 5 checkers.

---

## Step 4. Electronics, panel and trays
**Goal:** the device runs from its own battery with the rule-required stop, start, LEDs and connectors.

| Printed (`out/printed/`) | Qty |
|---|---|
| `control_panel` | 1 |
| `battery_tray` | 1 |
| `breadboard_tray` | 1 |

| Bought | Qty |
|---|---|
| Latching E-stop with 2 NC blocks, 16 mm start button, green + red LEDs with holders | 1 each |
| 4S LiPo 2200 + fuse + XT60, 2x Mini560 Pro 5 V regulators | 1 each |
| ESP32-S3 board, 4x TMC2209, perfboard with connectors A/B/C, BSS138 level shifter, passives (`wiring.md`) | |
| 400-point breadboard | 1 |
| Wood screws 3.5x50 (panel), 3.5x12 (trays), M3x16 countersunk (standoff) | |

**Tests (from `wiring.md`):**
1. Before any motor is connected: check 5 V and 6 V rails with a multimeter.
2. Press E-stop while an axis moves: motors and servo must lose power, and the magnet must drop the checker.
3. Green LED = drives powered, red = program running; start button starts the program.
4. Connectors A/B/C: check voltages and the UART on C with a laptop.

---

## Step 5. Cable chains and cable routing
**Goal:** no cable gets pulled, pinched or dragged anywhere in the travel.

| Printed (`out/printed/`) | Qty |
|---|---|
| `y_chain_guide` | 1 |

| Bought | Qty |
|---|---|
| Cable chain 10x15 R18 (X 280 mm, Y 250 mm + end links) | 1 m |
| M3x12 + nuts, M3x10 button + T-nuts, M3x20 button + nut, wood screws 3.5x20 | |
| Zip ties 2.5-3 mm, wires and JST connectors (`wiring.md`) | |

**Tests:**
1. Move slowly to every corner of the travel and every wrist extreme (both lift ends, full turn): watch every cable.
2. Unplug test: every harness unplugs at the board.

---

## Step 6. Whole device test
1. Home, then visit a grid of points over the field (like the 5 x 5 grid in the model checks) and measure the error at each.
2. Pick-and-place a full task: pick, turn, stack to 5, on battery only, for 30 minutes (battery runtime).
3. Park check: it parks inside zones 1+2 and stays inside the 600 x 500 polygon.

---

## Order that matters (checked by `tools/assembly_sim.py`)
The simulation builds the device in this order and checks every part, screw, nut, T-nut and insert can be fitted with
normal tools (hex keys, a straight hex driver, Phillips stubby / precision drivers, a nut driver or spanner, the iron).
These are the places where the order is not optional:
- **Y carriage:** screw it to the Y block (4 screws, down through the notches in the socket) **before the post goes in**.
- **Y and X idlers:** put the axle, idler and slider together on the bench first, then fit the unit (the X axle head sits between boom and idler).
- **Rails:** drop the T-nuts in before the rail goes on; slide the block along the rail to reach the screws under it.
- **Wrist:** screw the bare wrist carriage plate to the X block first (3 screws from below; the 4th block hole is not used: no tool can reach it past the servo plate),
  then the riser, clamp, chain post, servo, arms, end plate, shelf and motor. Servo: M2 self-tapping screws from the tab side.
- **Magnet:** melt the insert into the hub bottom, screw the M3x8 set screw in from below (4.5 mm in), spin the magnet on with
  Loctite 243, then push the hub onto the motor shaft.
- **Controller:** screw the perfboard to the standoffs, then plug the ESP32 in (it covers a standoff screw).
- **Control panel:** fit the connector board through the two small windows in the +x wall (precision PH0 driver, 60 mm shaft), then screw the panel down.
- **Plywood (6 mm):** beam bolts go in from below; the feet bolt on from the top (M3x10 countersunk into the foot insert). Every other part on the board: bolt from the top, washer + hex nut underneath; hold the nut with a 5.5 / 7 mm spanner with the board tipped on its side or lifted off the table. Controller, panel, breadboard and battery are placed by hand (not modelled since 22 Oct): drill their holes where you want them.
Not simulated: belts, cables, chains and zip ties (flexible, pushed aside by hand).

---

Interactive 3D version of these steps: artifact "ETZ Plotter Build Steps" (https://claude.ai/artifact/Fm5uXZjVuXohkbDCnw3GGj).
Rebuild its model data after a geometry change with `./fcpy tools/anim_export.py` (writes `out/anim/parts.json` + `meshes.dat`,
then `base64 -w0 out/anim/meshes.dat > out/anim/meshes.b64.txt`); the page source is `out/anim/index.html`.
