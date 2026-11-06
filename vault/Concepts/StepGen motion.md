---
tags: [concept]
updated: 2026-11-06
---
# StepGen motion

Own step generator: timer interrupt, trapezoid or S-curve (jerk-limited) profiles with an exact stop distance;
`line` locks X and Y so both arrive together (checked on the board 25 Oct).
`laptop/machine.py` has a Python port of the timing (move_time) so the planner's times match.
Theory link: [[Rotation and inertia]] (acceleration needs torque), [[Optimisation and terminal speed]].
Related: [[Firmware]], [[ETZ speed minimum]], [[Move queue]].
