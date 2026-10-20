# ETZ plotter - instructions for Claude

You are continuing Egor's olympiad robotics project with him. Read this file fully, then `docs/status.md`
(where we are, decisions, open items). Rules of the competition: `docs/etz_rules_summary.md`.
Design rules Egor requires: `docs/design_rules.md`.

## Who and what
- Egor, grade 11, VsOSh (all-Russian olympiad) informatics, robotics profile, ETZ 2026-27 final stage.
- The device: a Cartesian XY plotter that picks checkers (26 x 5 mm, steel washer inside) with an electromagnet,
  rotates them (wrist) and stacks them up to 5, on a 600 x 500 polygon. It is designed here as parametric
  FreeCAD Python scripts; Egor opens the results in FreeCAD.
- Egor writes in English: answer in English, plainly, short. He is not a mechanical engineer: explain what a
  thing is for when it is not obvious, and show pictures (renders) when it helps.
- He works on Windows (PC, laptop) and his phone; sessions may run locally or in the cloud.

## Standing instructions (always)
- **STEP only. Never produce STL files** (not even as an extra). Slicers open STEP.
- Follow `docs/design_rules.md` for every printed part: parameters at the top, tolerances from the named
  constants, walls >= 2.4 mm, fillets on internal corners, overhang <= 45 deg, bridges < 10 mm, fits 220 x 220,
  M2..M5 + Ruthex M3 inserts, zip-tie features. Never guess a bought-part dimension: mark it `VERIFY` and ask.
- After any geometry change, run the checks (below) and do not deliver until they are clean. Say plainly when
  something is a placeholder or not modelled.
- Keep `README.md`, `docs/status.md`, `components.csv`, `wiring.md` true after each change. Commit with a clear
  message and push, so his other devices get it.
- **Push right away after every finished change** (model, docs, BOM, coupons) once its checks are clean - do not
  ask first and do not leave work uncommitted at the end of a turn (a session can die mid-way: on 16 Oct a finished
  MG996R revert sat uncommitted for days). Bump the version (v2.x) in `docs/status.md` for model changes.

## Repository map
| Path | What |
|---|---|
| `wrist/wrist_module.py` | Wrist module: all tolerance constants (section 1), bought-part data, 9 printed parts, `pose()` for lift and wrist angle |
| `wrist/dfm.py` | Print-rule checks (walls, overhangs, bridges, sharp internal corners) |
| `wrist/review.py` | Wrist interference sweep + DFM -> `wrist/out/review.json`, `wrist/out/*.step` |
| `frame/frame.py` | Base, Y axis, Y carriage, post, boom, X axis, panel, trays, electronics; layout parameters at the top |
| `frame/chains.py` | X and Y cable chains (built per pose), `y_chain_guide` |
| `frame/cables.py` | Cable harness tubes (paths per group); `wrist_harness()` rebuilds the wrist harness per pose from `W.harness_paths()` |
| `frame/fasteners.py` | Every screw / nut / washer / insert / T-nut, placed per group; `bom()` |
| `assembly.py` | `world(PYC, PXB, h, wrist_deg, fasteners=...)` places everything; all whole-device checks -> `out/assembly_review.json`, `out/fastener_bom.csv` |
| `export_gui.py` | Coloured, grouped STEP + FCStd (parked and working pose) and `out/printed/*.step` (print orientation) - needs the FreeCAD GUI |
| `tools/stability.py` | Masses, tipping, rail moments, sag, backlash budget -> `out/stability.json` |
| `tools/fea.py` | FEA (gmsh + CalculiX from FreeCAD) of the motor mounts, idler brackets, Y carriage -> `out/fea.json`; see `docs/stiffness_review.md` |
| `tools/render_pose.py` | PNG render of any pose (crop optional) |
| `tools/assembly_sim.py` | Assembly simulation: build order, part insertion paths, screw entry, tool / nut / T-nut / iron access -> `out/assembly_sim.json` |
| `tools/anim_export.py` | Meshes for the 3D build-steps page (`out/anim/`, artifact "ETZ Plotter Build Steps") |
| `tolerance/coupons.py` | 11 tolerance test coupons -> `tolerance/out/*.step`; `tolerance/README.md` = how to test |
| `verify_step.py` | Re-import a STEP and count parts/solids |
| `vendor/` | Real STEP models of bought parts (Egor's downloads). `W.detailed()` / `F.detailed()` place them; `world(detail=True)` swaps them in (export + `detailed_*` checks) |
| `components.csv` | Every bought component, why it was chosen, CAD data |
| `wiring.md` | Power, stop button, ESP32-S3 pin map, harnesses, driver currents |

Coordinates: X along the 600 mm side (zone 1 x 0..350, field from x 350), Y along 500, Z up from the table, mm.
Y-carriage parts are built at PYC0 = 40 and moved by (0, PYC-40, 0); wrist parts are built in module coordinates
(x from PXB, y from PYC, absolute z) and moved by `W.pose()` then (PXB, PYC, 0). Travel: PYC 40..376, PXB 287..430,
magnet face h 5..40 mm, wrist any angle. Groups: base, ycar, wm_xcar, wm_armT, wm_armB, wm_end, wm_wrist, chainX, chainY.

## Running things
FreeCAD 1.0.x or 1.1.x is the CAD kernel (OpenCascade); Egor's PC has 1.1. Scripts run with FreeCAD's own Python:
- Windows: `fcpy.bat assembly.py`, GUI export `fcgui.bat export_gui.py` (finds `C:\Program Files\FreeCAD 1.*`,
  or set `FREECAD_DIR`). In subfolders: `..\fcpy.bat review.py`.
- Linux / cloud: `./fcpy assembly.py`, `./fcgui export_gui.py` (offscreen Qt). If FreeCAD is missing (cloud
  session, pip/apt blocked), run `tools/setup_freecad_linux.sh` (AppImage from GitHub releases, no root).

Full check and export after a change (about 15 minutes in total):
1. `cd wrist && ../fcpy review.py` - interference none, DFM clean.
2. `./fcpy assembly.py` - static_park {}, cable_paths_through_parts none, fastener_clips_at_rest none,
   fastener_engagement_problems none, fastener_sweep none, sweep none, detailed_* none, worst_outside_polygon 0, parked in zones,
   every frame part DFM clean (thin 0, sharp 0, overhang 0).
3. `./fcpy tools/assembly_sim.py` (problems: 0), `./fcpy tools/fea.py` (all ok) then `./fcpy tools/stability.py`
4. `./fcgui export_gui.py` then `./fcpy verify_step.py out/ETZ_plotter_parked.step`
5. If tolerances changed: `cd tolerance && ../fcpy coupons.py`

## Known gotchas
- Without the GUI, `Part.export()` writes an EMPTY STEP: use `shape.exportStep(path)`. Colours and the grouped
  tree need `export_gui.py` run inside FreeCAD (it ends with `os._exit(0)`).
- DFM on engraved text is very slow: coupons are checked with `LABELS = False`; check compounds per solid.
- Tessellating many detailed STEP files at fine tolerance runs out of memory: use 0.25-0.3 for renders.
- Vendor models: the fast checks use simple shapes sized from the vendor STEP; `assembly.py` also runs `detailed_static_park`,
  `detailed_fastener_clips`, `detailed_sweep` with the real models. Wire stubs and stray features are trimmed when placing them.
- Zip ties: `zip_pair` slots sit either side of the cable (cable runs along 'along'); a tie entry in `W.ZIPS` / `frame.ZIPS`
  cuts the slots (`zip_slots`) and places the tie (`zip_tie`) from one line, so they always match.
- `fillet_all()` fillets every concave/convex edge; very small features may fail to fillet (logged in `FILLET_LOG`).
- FreeCAD 1.1: a failed `makeFillet` can damage the shape it was called on, and can return a broken solid that
  passes `isValid()`. `_fillet()` works on a copy and uses `check(True)`; never call `makeFillet` in `fillet_all` directly.
- The matplotlib renders use a painter's algorithm, so some faces show through; fine for checks, not pretty.
- Engagement for tapped holes ('self', 'tapped' targets) is measured by sampling, for solid targets by volume.

## Older material
The claude.ai Project "проект етз" also has older docs (the abandoned SCARA design, the first project plan,
an independent review, a hardware BOM). They are history; this repository is the current source of truth.
