# ETZ plotter v2: whole device

**Open in FreeCAD:** `out/ETZ_plotter_parked.FCStd` (native, coloured, grouped) or `out/ETZ_plotter_parked.step`.
`ETZ_plotter_working.*` is the same model at Y 250, X 400, magnet face 5 mm, wrist 90 deg.
Tree: ETZ_plotter > Base_and_Y_axis, Y_carriage_and_X_axis, Wrist_module, Electronics_and_controls, Cables_and_chains, Fasteners, Field_reference.
Coordinates: X along the 600 mm side of the polygon, Y along the 500 mm side, Z up from the table (mm).

**Print files:** `out/printed/` has all 22 printed designs (13 frame parts + 9 wrist module parts) in print orientation, as STEP (PrusaSlicer, OrcaSlicer, Bambu Studio and Cura 5.x open STEP).
`y_beam_riser_x4` is printed four times.

**Wiring:** `wiring.md` (power, stop button, ESP32-S3 pins, every harness, driver currents).

**Tolerance tests:** `tolerance/` has 11 test coupons (STEP) and `tolerance/README.md` says how to test each one and which
constant to change. Print them before the real parts.

## Fasteners (v2.2)
All 133 fasteners are in the model (`Fasteners` in the tree): every screw with its head, nut, washer, heat-set insert or T-nut,
341 solids. `out/fastener_bom.csv` is the complete list with quantities. The check (`assembly.py`) found and fixed these:
- **Rubber feet:** a 3 mm foot cannot hold a screw. Now screw-on feet 20 x 7 mm sit 4 mm deep in pockets under the plywood
  (20 mm Forstner bit) and stick out 3 mm, so nothing else moves. Wood screw 3.5x12 from below.
- **Y beam bolts:** a flush M5 countersunk screw was either too short for the T-nut or hit the profile core. Now M5x20 socket caps
  in 9.3 mm counterbores, 7.5 deep, from below.
- **Y idler moved to y 12** (was 22): its axle nut hit the Y block when parked. The beam end plate of the idler bracket is lower
  (z 41.5) to clear the same nut.
- **X idler axle:** the nut would have hit the boom, so the bolt head now sits between the boom and the idler and the nut is outside.
- **Corner brackets:** the centre rib was in the way of the screw heads; modelled with side walls and holes 11 mm from the corner
  (VERIFY on your brackets). The two heads on one bracket touched at 10 mm.
- **Rails:** MGN12 rails now have their counterbored M3 holes (25 mm pitch; VERIFY), M3x8 into T-nuts.
- **Servo tab nuts:** the wrist carriage ribs were cut to 7 mm so the washers and nylocs fit.
- **Trays:** screw heads hit the breadboard and battery tray walls; ears moved out 2.5 / 1.5 mm, the breadboard 2 mm further +Y.
- **Y chain moving end:** button heads (M3x20) so the cable bundle fits over them.
Results: no fastener clips any part at rest or in 16 poses against the moving parts; every screw engages enough
(inserts >= 4 mm, T-nuts >= 2.5..3 mm, nuts fully, tapped metal within its thread depth) and blind screws end inside their target.


## Cable chains and cables (v2.1)
- **X chain** (10 x 15 R18, 280 mm): fixed end on the boom top at x 230..250 (2 M3 drop-in T-nuts), lower run lies on the boom,
  U-bend toward +X, upper run back to the moving end on top of `chain_post`. The post top is now at z 208 (boom top 172 + 2 x R18)
  and has a 45 deg brace and a slot for the end link screws (any hole spacing fits).
- **Y chain** (10 x 15 R18, 250 mm): lower run in the printed `y_chain_guide` on the plywood (x 235.5, y 213..421), U-bend toward +Y,
  upper run to the moving end on top of the Y carriage (M3 + nut through a slot). The guide's 17 mm floor (pockets underneath)
  lifts the chain so the upper run meets the carriage top.
- Both chains are rebuilt for every pose: the bend sits where the chain length puts it (it moves at half the carriage speed).
  X bend x 395..467, Y bend y 250..418: the Y bend stays 57 mm inside the polygon edge.
- **Cable tunnel:** the Y beam now sits on four printed risers (10 mm), so the cables from the battery, the panel and the Y motor
  cross under the beam (at y 60 and y 205) to the electronics board. Before this, nothing could reach the board without crossing the
  Y carriage's path. The post is 10 mm shorter (130 mm), so the boom height is unchanged.
- The cable bundles are modelled as tubes (`cable_*`), so the collision check sees them.
- **X travel is now pivot X 292..435** (magnet X 397..540, the cells need 397..537). Park X is 292. Raising the Y axis left the
  wrist carriage 3 mm into the Y carriage at the old minimum (256).

## Whole-device check (`assembly.py`, results in `out/assembly_review.json`)
- no clash between any two parts at rest, and no cable passes through a part;
- no collision in 54 poses: Y 40/124/208/292/376 x X 292/328/364/400/435 x face height 5/40 mm, plus wrist +-90/180, chains and cables included;
- every pose stays inside the 600 x 500 polygon; parked device inside zones 1+2, feet only in zone 1;
- lowest part over the field at face height 5 mm: camera lens at 29.4 mm (clears a 5-stack);
- every printed part: walls >= 2.4 mm, no unrounded internal corner, no overhang > 45 deg, widest bridge 9.3 mm, fits 220 x 220.

## Stability and stiffness (`tools/stability.py`, results in `out/stability.json`)
- Mass about 4.0 kg with all screws (base 2.56, Y carriage and boom 0.98, wrist module 0.43, chains 0.08).
- Tipping: the centre of mass stays at least 92 mm inside the feet. Tipping would need 31 m/s2 (3.2 g); the design acceleration is 2 m/s2.
- Rail loads: worst moment 1.65 N m on the Y block against 37.5 N m rated (23x margin).
- Sag of the magnet from the aluminium profiles: at most 0.16 mm. The printed socket and the corner brackets add more; calibration takes it out,
  and the placement tolerance is 10 mm.

**Regenerate:** `freecad export_gui.py` (needs the FreeCAD GUI for colours), `./fcpy assembly.py` and `./fcpy tools/stability.py`
with FreeCAD's python. `./fcpy tools/render_pose.py Y X h wrist out.png` renders any pose.

**Frame parts (same rules as the wrist module):** y_carriage (post socket with round relief groove, block screws sunk 5 mm: fit them
before the post; slot for the Y chain end), y_belt_spacer, y_belt_clamp (tooth grooves), y_motor_mount (tension slots), y_idler_bracket
(Y home switch post), y_beam_riser x4 (tongues locate the beam in its slot), y_chain_guide, x_motor_mount (counterbored M5 into the post,
X home switch), x_idler_bracket (slotted axle for X belt tension), post_cap, control_panel (stop, start, LEDs, connectors A/B/C),
breadboard_tray, battery_tray.

**Screws:** `out/fastener_bom.csv` is the complete list (it replaces the screw lists further down where they differ). Zip ties are not modelled.

---

# ETZ plotter v2: component choices and the wrist module

Model v2 follows the design rules: parameters at the top of the script, separate printable parts, rule tolerances, 2.4 mm minimum walls, filleted corners, at most 45 degree overhangs, short bridges, cable-tie features. The CAD is FreeCAD (OpenCascade) Python, so the solids are real B-rep with true fillets.

## Files
- `wrist/wrist_module.py`: the parametric model (all dimensions in sections 1 to 3 at the top).
- `wrist/review.py`: the review that produced the numbers below.
- `wrist/out/*.step`: the wrist parts in print orientation (the same files are in `out/printed/`). `wrist/out/wrist_module_assembly.step`: the whole module with the bought parts.
- `wrist/out/review.json`: all review results. `wrist/out/*.png`: renders.
- `components.csv`: every component of the device, with the reason it was chosen and the data used in the CAD.
- `vendor/`: real models of bought parts (MG996R, 25T aluminium arm horn, 11HS12-0674S, 17HS16-2004S1; the 684 bearing and MGN12 meshes are kept for reference only). The exported STEP/FCStd use them; the fast checks use simple shapes sized from them, and `assembly.py` also re-checks with the real models (`detailed_*` results).

Run the model yourself: install FreeCAD 1.0 or 1.1 (Linux AppImage or Windows installer), then
`freecadcmd -c "exec(open('wrist_module.py').read())"`, or open the file in the FreeCAD GUI with Macro > Macros > Execute.

## Wrist module: design decisions
- **Carriage and servo plate are one L-part.** This gives a stiff joint with no screws. It prints with the block face down; the servo window has a W-shaped 45 degree roof, so it needs no bridge. The lower pivot boss is a teardrop for the same reason.
- **Parallelogram, 80 mm arms.** The magnet face stays level from 5 to 40 mm. The servo swings +-12.6 degrees and the X shift (up to 1.9 mm) is corrected in software.
- **Bearings in the arms, clamped on the inner ring only.** A nylon spacer 4.2 x 7 x 3 goes through a 7.6 mm shoulder hole on one side and a 7 mm shim washer goes on the other, so nothing touches the outer ring. Moving gaps are 0.5 to 0.8 mm.
- **The top arm bolts to a 25T aluminium single-arm horn**: centre screw into the spline plus one M3 into the horn's tapped hole at r 24, with the horn's arm lying along the top arm.
- **Lightening slots** in both arms remove about 25 % of the web. The two flanges carry the bending, so stiffness hardly drops.
- **Shelf and end plate are separate flat parts.** Both print flat, so the stepper and pivot holes are vertical, round and accurate. They join with two M3 screws into inserts in the end plate's foot pad, which sits clear of the pivot nut.
- **The belt clamp** has half-round grooves at 2 mm pitch that take the belt teeth.
- **The hall switch** sits leads-down in a press pocket 0.8 mm from the hub's flag magnet; its leads run under the shelf to a hole beside the end plate.
- **MG996R servo**: M2 bolts with large washers through its 4.5 mm tab holes (M3 would leave only 2 mm of plastic to the window); shallow grooves take the ribs under its tabs.

## Tolerances used
| Feature | Size |
|---|---|
| M3 / M4 / M2 clearance holes | 3.25 / 4.25 / 2.25 (+0.25) |
| NEMA11 screw holes, pilot | 2.7, 22.2 (+0.2) |
| 684ZZ press seat | 9.12 (+0.12) |
| D-bore on the stepper shaft | 5.12 with flat at 4.62 (+0.12) |
| Servo window | case +0.4 per side |
| Spacer in the shoulder hole | 0.3 radial |
| Heat-set insert hole | 4.0 x 6.5 deep |

## Review results
- Interference: none, checked at face height 5, 10, 16, 22.5, 30, 36 and 40 mm and wrist angle 0, 90 and 180 degrees, with every bought part included.
- Smallest moving gaps: 0.3 mm (spacers in the arms) and 0.5 mm (lower arm to its boss and to the shelf). Servo case to window: 0.36 mm.
- Lowest point at face height 5 mm: camera lens 29.4 mm, which clears a stack of 5 checkers (25 mm).
- Every printed part: walls at least 2.4 mm, no unrounded internal corner, no overhang beyond 45 degrees, widest bridge 6.3 mm, all fit a 220 x 220 bed. About 72 g of PETG.

## Wrist module parts list
| Part | Qty | Print orientation |
|---|---|---|
| wrist_carriage | 1 | block face down |
| x_belt_riser | 1 | standing |
| x_belt_clamp | 1 | grooves up |
| chain_post | 1 | on its -Y face |
| arm_top, arm_bottom | 1 + 1 | flat |
| end_plate | 1 | -Y face down |
| shelf | 1 | stepper face down |
| wrist_hub | 1 | shaft end down |

Suggested settings: PETG, 0.2 mm layers, 4 walls, 40 % gyroid, no supports.

**Bought parts:** MG996R servo + 25T aluminium arm horn, NEMA11 11HS12-0674S, P20/15 5 V magnet, DRV5023 hall switch + 3x2 magnet, 3x 684ZZ, 3x nylon spacer 4.2x7x3, 3x shim 4.2x7x0.8, camera, 10x Ruthex M3x5.7.

**Screws:**
- 4x M3x6 ISO4762: carriage to the rail block.
- 4x M2x12 ISO4762 + DIN 9021 washer under the head + nyloc (no washer under the nut): servo tabs.
- 1x M4x30 ISO4762 + nyloc: lower A pivot.
- 2x M4x20 ISO4762 + washer + nyloc: B pivots.
- 2x M3x10: belt riser. 2x M3x10: chain post. 2x M3x8: belt clamp. 2x M3x12 + nut: X chain end on the post.
- 2x M3x10: shelf to end plate.
- 4x M2.5x6 ISO7380: NEMA11.
- 4x M2x12 + nut: camera.
- 1x M3x6 or M3x8 ISO7380: magnet. Use the length that suits the magnet's thread depth.
- 1x M3x10 ISO7380: top arm to the horn (r 24 hole, tapped M3 in the horn: VERIFY).

## Assembly order
1. Press the heat-set inserts: riser (2 top, 2 bottom), chain post foot (2), end plate foot (2).
2. Screw the wrist carriage to the rail block (4x M3x6 from below). Do this before the servo goes in: the servo covers two of the screws.
3. Fit the riser and chain post from below (M3x10).
4. Push the servo through the window from the -Y side and bolt the tabs (M2x12, large washer under the head, nyloc).
5. Press the bearings into both arms from the end-plate side (flush).
6. Set the servo to its centre pulse (1500 us), fit the horn with the arm level, and screw the top arm to it.
7. Lower pivot A: M4x30 from the servo side, through the boss, spacer, bearing, shim and nyloc. Snug only: the arm must swing freely.
8. Screw the shelf to the end plate (2x M3x10 from below). Mount the NEMA11 (4x M2.5x6 from below) and the camera.
9. B pivots: M4x20 with washer and spacer from the arm side, then bearing, shim, end plate and nyloc.
10. Press the hub onto the stepper shaft (D flat aligned), with the magnet screw already inside it, then screw on the electromagnet. Press the 3x2 magnet into the flag and the hall switch into its pocket.
11. Route the cables (see wiring.md): camera cable tie on the shelf, hall leads under the shelf and up its hole, the harness tie on the end plate, two ties round the top arm, servo lead to the bundle, two ties on the chain post.

## Measure before printing (marked VERIFY in the script)
Servo (MG996R, taken from a third-party STEP model): tab face to cover top, case height, spline centre to case end, tab hole spacing (48.4), horn face height, horn screw hole thread. Magnet: thread depth. Camera: board size and hole spacing. Enter the measured values at the top of `wrist_module.py`; everything else follows.
