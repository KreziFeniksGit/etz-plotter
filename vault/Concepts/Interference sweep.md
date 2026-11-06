---
tags: [concept]
source: assembly.py
updated: 2026-11-06
---
# Interference sweep

`assembly.py` places everything per pose and checks for clashes: 54 poses (Y x X x lift + wrist extremes), cable chains,
harness and fasteners included; parked inside zones 1+2; whole device inside the polygon.
Lesson: [[Sweeps must sample where things actually pass]]. Related: [[CAD Pipeline]], [[Cable chains and harness]].
