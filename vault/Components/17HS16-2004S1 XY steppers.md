---
tags: [component]
source: components.csv
updated: 2026-11-06
---
# 17HS16-2004S1 XY steppers

NEMA17 42x42x40, 45 N·cm, 2 A, low 2.6 mH inductance (keeps torque at speed on 14.8 V). X and Y.
Needed torque ~0.03 N·m: margin > 10x ([[No encoders]]). Run at 0.9 A RMS (half rated: cool on battery) - [[TMC2209 drivers]].
80 steps/mm with [[GT2 belts and pulleys]] at 16 microsteps. Vendor STEP in `vendor/`.
Theory link: [[A gearbox multiplies torque by its ratio]], [[Rotation and inertia]]. Related: [[Mechanics]].
