---
tags: [concept]
updated: 2026-11-06
---
# Homing and soft limits

`home x|y|all`: fast search (25 mm/s) to the switch, off it, slow touch (2 mm/s), position = offset; timeout 25 s.
After homing, targets outside the travel are refused (`err limit`). Raise the lift first (firmware does not).
Switch logic: HIGH = pressed or broken wire ([[Omron D2F home switches]]). Why it matters: [[No encoders]] - homing every run is the reference.
Related: [[Firmware]], [[Bring-up]].
