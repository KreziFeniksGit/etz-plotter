---
tags: [lesson]
updated: 2026-11-06
---
# FreeCAD 1.1 failed fillet damages the shape

**What happened:** 11 Oct: on Egor's FreeCAD 1.1 the Y carriage came out as an EMPTY shape: a failed `makeFillet` damaged its input and returned a broken solid that passed `isValid()`.

**Rule:** `_fillet()` works on a copy, checks with `check(True)`, retries edge by edge; never call `makeFillet` directly in `fillet_all`.

Related: [[CAD Pipeline]], [[Design rules (DFM)]]
