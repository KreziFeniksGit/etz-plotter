# Project status and history

Last update: 11 Oct 2026 (v2.3: repository set up for Claude Code, STEP-only outputs).

## Where we are
The whole device is modelled in FreeCAD (Python scripts), checked and exported:
- 22 printed parts (13 frame + 9 wrist module), all pass the DFM rules, STEP in `out/printed/`.
- Whole device STEP + FCStd in two poses (parked, working), coloured, grouped tree.
- Real cable chains (rebuilt per pose), cable harness tubes, wiring map (`wiring.md`).
- All 133 fasteners modelled and checked (`frame/fasteners.py`, `out/fastener_bom.csv`).
- Stability / rail loads / sag (`tools/stability.py`, `out/stability.json`).
- 11 tolerance test coupons (`tolerance/`), not printed yet.
- Parts checklist with shop links for the teacher: artifact "ETZ Plotter Parts" (https://claude.ai/artifact/M8HTCgmFh44aH4F9nQc8U6).

## Check results (v2.2)
- No clash at rest; no collision in 54 poses (Y 40/124/208/292/376 x X 292/328/364/400/435 x face 5/40 mm + 4 wrist extremes); chains, cables and fasteners included.
- No fastener clips anything (rest + 16 poses vs moving parts); every screw engages enough; blind screws end in their target.
- All poses inside the 600 x 500 polygon; parked inside zones 1+2; lowest non-gripper part over the field at face 5 mm: camera lens 29.4 mm.
- Mass 4.0 kg; CoM >= 92 mm inside the feet; tipping needs 31 m/s2 (design acceleration 2); worst rail moment 1.65 N m vs 37.5 rated; profile sag <= 0.16 mm (joints not included).

## Decisions (and why)
- Cartesian XY plotter (the earlier SCARA arm was dropped). Approved by Egor on 10 Oct.
- Y: 2020 beam on 4 printed risers (10 mm cable tunnel), MGN12 400 rail, NEMA17 + GT2. Post 2020 x 130 in a printed socket; boom 2020 x 270 with 2 corner brackets; X: MGN12 250 under the boom.
- Wrist module: DS3218 servo drives an 80 mm parallelogram (magnet face 5..40 mm, level), NEMA11 rotates the magnet (0..360), hall homing, P20/15 electromagnet, camera on the shelf.
- X travel PXB 292..435 (magnet x 397..540, cells 397..537). Park at Y 40, X 292.
- Controller Raspberry Pi Pico 2 (no radio), TMC2209 x4 over UART, 4S 2200 LiPo, Pololu 5 V and 6 V regulators, E-stop with 2 NC blocks (drive bus + magnet 5 V).
- No encoders: tolerance 10 mm vs ~1.6 mm calibrated, >10x torque margin, homing every run, StallGuard can detect stalls.
- Outputs are STEP only (never STL) - Egor's standing instruction.

## Version history
- v1 (10 Oct): own prism kernel, first plotter model, viewer artifact (outdated).
- v2 (10 Oct): FreeCAD rebuild to the design rules; wrist module, frame, whole-device checks.
- v2.1 (11 Oct): real cable chains, cable tunnel risers, cable tubes, wiring.md, stability check.
- v2.2 (11 Oct): every fastener modelled and checked (feet pockets, beam bolt counterbores, Y idler to y 12, X idler axle flipped, bracket holes, rail holes, rib, tray ears); tolerance coupons.
- v2.3 (11 Oct): git repo + CLAUDE.md; STEP-only pipeline; Windows/Linux FreeCAD runners.

## Open items (in order)
1. Egor prints the tolerance coupons A, C, D1, E1, F1 (then the rest) and reports which variant fits -> set the constants in `wrist/wrist_module.py` section 1, re-run everything, re-export.
2. Calipers on the parts marked VERIFY: servo (tab-to-top, case height, spline offset, horn face), magnet thread depth, camera board, chain link pitch and end link, corner bracket hole position, MGN12 rail hole pitch/counterbore, NEMA11 thread depth.
3. Egor checks which parts the school has (parts checklist artifact); BOM may change.
4. Camera choice (Egor) -> CAM_* parameters in the wrist module.
5. Organisers: is a self-designed PCB with plug-in TMC2209 allowed; V pin of connectors A and B.
6. Possible: custom PCB (KiCad) replacing the perfboard - Egor asked if possible; offered, waiting for go and fab choice (JLCPCB / PCBWay).
7. Not modelled: zip ties, wrist-internal cables (service loop along the top arm).
8. Next big items: firmware plan (Pico 2, PIO steppers, UART to laptop, OpenCV on the laptop), reworked project plan.
