---
tags: [concept]
source: docs/stiffness_review.md
updated: 2026-11-06
---
# FEA

`tools/fea.py` (gmsh + CalculiX inside FreeCAD): motor mounts, idler brackets, Y carriage. Found (12 Oct) the X idler bracket
failing (0.65 deg tilt) -> redesigned; worst now 0.11 deg. Lesson: [[Non-ASCII paths break external tools]] (gmsh + "Рабочий стол").
Theory link: [[Statics and torque]]. Related: [[Backlash budget]], [[Stability and tipping]].
