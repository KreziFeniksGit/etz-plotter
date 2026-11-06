---
tags: [decision]
updated: 2026-11-06
---
# No encoders

The steppers run open loop. Why: placement tolerance is 10 mm vs ~1.6 mm calibrated accuracy ([[Accuracy budget]]),
torque margin > 10x ([[17HS16-2004S1 XY steppers]]), homing every run ([[Homing and soft limits]]), and
StallGuard sees stalls ([[Crash detection]]). Lost steps would be caught by re-homing.
Theory link: closed-loop control is in [[PID control]] - we do not need it on the axes.
