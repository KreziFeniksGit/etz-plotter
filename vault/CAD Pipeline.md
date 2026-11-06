---
tags: [hub]
source: .claude/rules/cad.md
updated: 2026-11-06
---
# CAD Pipeline

The device is parametric FreeCAD Python (FreeCAD 1.1 on Egor's PC); scripts build, check and export STEP.

- Build: `wrist/wrist_module.py`, `frame/*.py`, `assembly.py` (`world(PYC, PXB, h, wrist_deg)`)
- Checks: [[Interference sweep]], [[Design rules (DFM)]], [[Assembly simulation]], [[FEA]], [[Stability and tipping]], [[Fasteners model]]
- Export: `export_gui.py` (needs the GUI) -> coloured STEP + `out/printed/*.step`; [[STEP only, never STL]]
- Targeted checks after a local change (`ETZ_QUICK=wrist`), the full ~15 min run before delivery - Egor's preference.
- Gotchas: [[FreeCAD 1.1 failed fillet damages the shape]], [[Part.export without the GUI writes an empty STEP]], [[Non-ASCII paths break external tools]], [[Vendor models can be the wrong variant]], [[Sweeps must sample where things actually pass]]

Source: `.claude/rules/cad.md`.
