---
tags: [lesson]
updated: 2026-11-06
---
# Part.export without the GUI writes an empty STEP

**What happened:** Headless `Part.export()` produced empty files.

**Rule:** Use `shape.exportStep(path)` headless; colours and the grouped tree need `export_gui.py` inside FreeCAD. Verify with `verify_step.py`.

Related: [[CAD Pipeline]], [[STEP only, never STL]]
