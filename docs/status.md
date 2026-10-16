# Project status and history

Last update: 15 Oct 2026 (v2.8: 2020 V-slot profiles; wrist stepper is now a NEMA17 pancake 17HS4023S, magnet moved to x 110, y 18.5; X travel 287..430).

## Where we are
The whole device is modelled in FreeCAD (Python scripts), checked and exported:
- 24 printed parts (15 frame + 9 wrist module), all pass the DFM rules, STEP in `out/printed/`.
- FEA of the load-carrying printed parts (`tools/fea.py`, `out/fea.json`) and a backlash budget: `docs/stiffness_review.md`.
- Whole device STEP + FCStd in two poses (parked, working), coloured, grouped tree.
- Real cable chains (rebuilt per pose), cable harness tubes, wiring map (`wiring.md`).
- All 140 fasteners modelled and checked (`frame/fasteners.py`, `out/fastener_bom.csv`).
- Stability / rail loads / sag (`tools/stability.py`, `out/stability.json`).
- 11 tolerance test coupons (`tolerance/`), not printed yet.
- Parts checklist with shop links for the teacher: artifact "ETZ Plotter Parts" (https://claude.ai/artifact/M8HTCgmFh44aH4F9nQc8U6).

## Check results (v2.2)
- No clash at rest; no collision in 54 poses (Y 40/124/208/292/376 x X 287/323/359/395/430 x face 5/40 mm + 4 wrist extremes); chains, cables and fasteners included (v2.8 re-run: all clean).
- No fastener clips anything (rest + 16 poses vs moving parts); every screw engages enough; blind screws end in their target.
- All poses inside the 600 x 500 polygon; parked inside zones 1+2; lowest non-gripper part over the field at face 5 mm: camera lens 29.4 mm.
- Mass 4.14 kg; CoM >= 90 mm inside the feet; tipping needs 30.5 m/s2 (design acceleration 2); worst rail moment 1.78 N m vs 37.5 rated; profile sag <= 0.17 mm (joints not included). Servo lift: 0.23 N m needed = 21 % of the MG996R stall at 6 V.

## Decisions (and why)
- Cartesian XY plotter (the earlier SCARA arm was dropped). Approved by Egor on 10 Oct.
- All profiles are 2020 V-slot (OpenBuilds section, 6 mm slot opening; Egor, 15 Oct). Corner brackets: Soberizavod 20x20 slot 6 T01 (cast).
- Y: 2020 beam on 4 printed risers (10 mm cable tunnel), MGN12 400 rail, NEMA17 + GT2. Post 2020 x 130 in a printed socket; boom 2020 x 270 with 2 corner brackets; X: MGN12 250 under the boom.
- Wrist module: MG996R servo (Egor's choice, 11 Oct; was DS3218) with a 25T aluminium arm horn drives an 80 mm parallelogram (magnet face 5..40 mm, level), a NEMA17 pancake 17HS4023S rotates the magnet (0..360; Egor, 15 Oct, was a NEMA11), no wrist home sensor (Egor, 12 Oct: the hall switch was dropped; the wrist is set to its mark by hand before power-up), P20/15 electromagnet, camera on the shelf.
- X travel PXB 287..430 (magnet x 397..540, cells 397..537; MAG_X 110). Park at Y 40, X 287 (wrist carriage 2 mm clear of the Y carriage).
- Controller ESP32-S3-DevKitC-1 N16R8 (Egor's choice, 11 Oct; replaced the Pico 2). It has Wi-Fi/BT, which the rules require OFF: the firmware never starts the radio. TMC2209 x4 over UART, 4S 2200 LiPo, Pololu 5 V and 6 V regulators, E-stop with 2 NC blocks (drive bus + magnet 5 V).
- No encoders: tolerance 10 mm vs ~1.6 mm calibrated, >10x torque margin, homing every run, StallGuard can detect stalls.
- Outputs are STEP only (never STL) - Egor's standing instruction.
- Belts are open lengths clamped at both ends on the carriage (Egor, 12 Oct), tensioned at idler sliders with M3 screws; the motors are fixed. Load parts printed with 6 walls, >= 50 % infill.

## Version history
- v1 (10 Oct): own prism kernel, first plotter model, viewer artifact (outdated).
- v2 (10 Oct): FreeCAD rebuild to the design rules; wrist module, frame, whole-device checks.
- v2.1 (11 Oct): real cable chains, cable tunnel risers, cable tubes, wiring.md, stability check.
- v2.2 (11 Oct): every fastener modelled and checked (feet pockets, beam bolt counterbores, Y idler to y 12, X idler axle flipped, bracket holes, rail holes, rib, tray ears); tolerance coupons.
- v2.3 (11 Oct): git repo + CLAUDE.md; STEP-only pipeline; Windows/Linux FreeCAD runners.
- v2.4 (11 Oct): white raised 'STOP' lettering (8 mm, cosmetic) on the stop button cap. First run on Egor's PC (FreeCAD 1.1) showed the Y carriage built as an EMPTY shape: in 1.1 a failed fillet damages the input and can return a broken solid. `fillet_all` now fillets a copy, checks strictly and retries one edge at a time with smaller radii; the Y carriage socket corner is filleted before the block-screw counterbores (the +x pair now go through that fillet). All checks clean again on 1.1.
- v2.5 (11 Oct): zip ties and wrist cables. The zip-tie slot pairs were turned 90 deg (a tie could not wrap the cable): `zip_pair` now puts the slots either side of the cable. 10 ties modelled (`W.ZIPS`, `frame.ZIPS`, post ties, 2 round the top arm). Wrist harness drawn and rebuilt per pose (`W.harness_paths`, `cables.wrist_harness`): camera, hall, stepper leads -> end plate -> top arm -> under the X block; servo lead under the carriage plate. Hall lead hole moved: it came up under the stepper; the sensor now sits leads-down and its leads run under the shelf to a hole beside the end plate. All wrist cables stay inside zone 2 when parked (y < 79.9). Spare tie slots with no cable removed (Y motor mount, Y idler bracket, X motor mount). Controller switched to the ESP32-S3-DevKitC-1 N16R8 (Egor): board in the model, new pin map in wiring.md (avoids strapping, flash, PSRAM and USB pins).
- v2.6 (11 Oct): Egor's STEP models in `vendor/` (MG996R, 25T aluminium arm horn, 11HS12-0674S, 17HS16-2004S1; 684 open bearing and MGN12 meshes kept for reference). Export uses them; `world(detail=True)` and `assembly.py` `detailed_*` checks re-check with them. MG996R fitted from its model: case 40.4 x 20, tab holes 48.4 apart (M2 bolts + large washers, M3 left 2 mm of plastic), rib grooves under the tabs, servo plate moved to y 3.56 so the arm stays at y 20, lead exits at the spline end. Top arm: centre screw + one M3 into the horn at r 24 (lightening slot starts at x 31, arm ties at x 36/56). Y motor turned so its lead stub points +y (it hit the battery). TMC2209s were drawn 10 mm wide at 11 mm pitch (real 15.3): now a 2 x 2 grid on female headers. Generated models: ESP32 board with module, USB-C and headers; regulators; DRV5023 body; flag magnet.
- v2.7 (12 Oct): Egor's review request (sag, bending, backlash, open belts; photos of the motor mounts). New `tools/fea.py` (gmsh + CalculiX): x_idler_bracket failed (0.65 deg idler tilt, 14 MPa) and x_motor_mount was borderline (0.2 deg). x_motor_mount: 6 mm plate, flanges, arms also bolted to the post's -x face (0.025 deg). y_motor_mount: 6 mm plate, base both sides, 4 gussets, 4 fixed screws, no slots. Both idlers on sliders pushed by an M3 screw in a lug. The X side plate and slider sit above z 155: the wrist harness passed through the old plate at X 380..400 (the sweep never sampled there). Open belts: Y clamp 30 mm / 3 screws, X clamp 42 mm / 3 screws, ends meet over the middle screw. Backlash budget 0.11 mm (Y), 0.07 mm (X) (`stability.json`). Y motor cable rerouted round the new base. Hall sensor, flag magnet, their pocket, lead and coupon D1 pockets removed (Egor); D1 is now `tol_D1_press_bearing`.
- v2.8 (15 Oct): two changes Egor asked for. (1) All 2020 profiles are V-slot: OpenBuilds section (mouth 9.16, 6.25 throat, lips 1.8 deep, 11 mm cavity, 4.2 centre hole, r 1.5 corners). Drop-in M3/M5 T-nuts still sit under the lips (engagement checked), the beam riser tongues (5.2) fit the throat, rails and brackets sit on the flat faces; corner bracket = Soberizavod slot 6 T01 (VERIFY hole position / keys). (2) Wrist stepper NEMA11 -> NEMA17 pancake 17HS4023S (42 x 42 x 23, 0.14 kg). The 42 mm body hit the lower arm's B boss and the end plate, so the magnet axis moved from (105, 21) to (110, 18.5): the motor is 1.35 mm clear of the arm boss, 1.85 mm of the end plate (narrowed to x 87), and stays at y < 40 (parked in zone 2). X travel shifts with it to PXB 287..430 (the magnet still covers 397..540). Shelf wider (y -3..39) and longer (x 168); motor on 4x M3x8 from below; camera moved to x 147 and fixed with M2 self-tapping screws from below (the motor now covers the old screw heads). Motor socket turned to +x; stepper and camera cables run over the motor top to a new junction J (80, 35.4, 94). Hub unchanged (5 mm D, 12.5 mm on the shaft). New servo lift check in stability.py: 0.23 N m = 21 % of MG996R stall. TMC2209 wrist current 0.6 A. Coupons D2/E2 now for the pancake (E2 = `tol_E2_nema17_pancake`). fea.py uses an ASCII temp folder when the repo path has non-ASCII letters (gmsh failed on 'Рабочий стол'). All checks clean.

## Open items (in order)
0. Build order: `docs/print_test_order.md` (coupons, then Y, X, wrist, electronics, chains, full test).
1. Egor prints the tolerance coupons A, C, D1, E1, F1 (then the rest) and reports which variant fits -> set the constants in `wrist/wrist_module.py` section 1, re-run everything, re-export.
2. Calipers on the parts marked VERIFY: 17HS4023S (body 23, shaft 20..24 - the hub takes up to 23, thread depth 4.5, connector side), V-slot section and Soberizavod bracket hole position, MG996R (sizes came from a third-party model: tab holes 48.4, tab-to-cover 7.7, spline offset 9.6, horn seat depth), horn hole thread, magnet thread depth, camera board, chain link pitch and end link, corner bracket hole position, MGN12 rail hole pitch/counterbore, NEMA11 thread depth.
3. Egor checks which parts the school has (parts checklist artifact); BOM may change.
4. Camera choice (Egor) -> CAM_* parameters in the wrist module.
5. Organisers: is a self-designed PCB with plug-in TMC2209 allowed; V pin of connectors A and B.
6. Possible: custom PCB (KiCad) replacing the perfboard - Egor asked if possible; offered, waiting for go and fab choice (JLCPCB / PCBWay).
7. Not modelled: magnet leads (loose coil, they turn with the wrist). VERIFY which side the 17HS4023S connector is on (modelled on +x) and where the servo lead leaves its case.
8. Next big items: firmware plan (ESP32-S3, RMT/MCPWM steppers, radio never started, UART to laptop, OpenCV on the laptop), reworked project plan.
