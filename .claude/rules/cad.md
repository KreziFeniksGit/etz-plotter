---
paths:
  - "wrist/**"
  - "frame/**"
  - "tolerance/**"
  - "tools/**"
  - "vendor/**"
  - "assembly.py"
  - "export_gui.py"
  - "verify_step.py"
---
# CAD work (FreeCAD scripts)

Printed parts follow `docs/design_rules.md`: parameters at the top, tolerances from the named constants
(TOL_MOVE, TOL_PRESS, TOL_BOLT, TOL_MOTOR in `wrist/wrist_module.py` section 1), walls >= 2.4 mm, fillets on internal
corners, overhang <= 45 deg, bridges < 10 mm, fits 220 x 220, M2..M5 + Ruthex M3 inserts, zip-tie features.
A bought-part size you have not measured or read from a datasheet / vendor STEP is marked `VERIFY` and asked.
Bump the model version (v2.x) in `docs/status.md` for model changes.

## Running
FreeCAD 1.0.x / 1.1.x (Egor's PC: 1.1), scripts run with FreeCAD's own Python:
- Windows: `fcpy.bat assembly.py`, GUI export `fcgui.bat export_gui.py` (finds `C:\Program Files\FreeCAD 1.*`, or set
  `FREECAD_DIR`). From the Bash tool a relative `fcpy.bat` is not found: `cmd //c "C:\Users\Egor\Desktop\etz-plotter\fcpy.bat assembly.py"`.
- Linux / cloud: `./fcpy assembly.py`, `./fcgui export_gui.py` (offscreen Qt). No FreeCAD: `tools/setup_freecad_linux.sh`.

## Checks
Run the checks that cover the change (Egor prefers this): a wrist-only change -> `wrist/review.py` +
`ETZ_QUICK=wrist` assembly run. The full run (about 15 min) before exporting / delivering the whole model:
1. `cd wrist && ../fcpy review.py` - interference none, DFM clean.
2. `./fcpy assembly.py` - static_park {}, cable_paths_through_parts none, fastener_clips_at_rest none,
   fastener_engagement_problems none, fastener_sweep none, sweep none, detailed_* none, worst_outside_polygon 0,
   parked in zones, every frame part DFM clean (thin 0, sharp 0, overhang 0).
3. `./fcpy tools/assembly_sim.py` (problems: 0), `./fcpy tools/fea.py` (all ok), then `./fcpy tools/stability.py`.
4. `./fcgui export_gui.py`, then `./fcpy verify_step.py out/ETZ_plotter_parked.step`.
5. Tolerances changed: `cd tolerance && ../fcpy coupons.py`.

## Gotchas
- Without the GUI, `Part.export()` writes an EMPTY STEP: use `shape.exportStep(path)`. Colours and the grouped tree need
  `export_gui.py` inside FreeCAD (it ends with `os._exit(0)`).
- FreeCAD 1.1: a failed `makeFillet` can damage the shape it was called on, and can return a broken solid that passes
  `isValid()`. `_fillet()` works on a copy and uses `check(True)`; never call `makeFillet` in `fillet_all` directly.
  Very small features may fail to fillet (logged in `FILLET_LOG`).
- DFM on engraved text is very slow: coupons are checked with `LABELS = False`; check compounds per solid.
- Tessellating many detailed STEP files at fine tolerance runs out of memory: use 0.25-0.3 for renders.
- Vendor models: fast checks use simple shapes sized from the vendor STEP; `assembly.py` also runs `detailed_static_park`,
  `detailed_fastener_clips`, `detailed_sweep` with the real models (wire stubs and stray features trimmed).
- Zip ties: one entry in `W.ZIPS` / `frame.ZIPS` cuts the slots (`zip_slots`) and places the tie (`zip_tie`), so they
  always match; `zip_pair` slots sit either side of the cable (cable runs along 'along').
- The matplotlib renders use a painter's algorithm: some faces show through. Fine for checks, not pretty.
- Fastener engagement: tapped holes ('self', 'tapped') measured by sampling, solid targets by volume.
