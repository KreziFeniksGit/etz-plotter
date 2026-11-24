---
tags: [concept]
source: wrist_stand/wrist_stand.py
updated: 2026-11-24
---
# Wrist test stand

Printed stand that holds the real wrist module so the [[MG996R servo]], [[P20-15 electromagnet]], [[17HS4023S wrist stepper]]
and [[TOF400C distance sensor]] can be tested while the [[MGN12 rails]] are not here yet.
The head copies the MGN12H block underside: 3 Ruthex inserts on the 20 x 20 pattern, face at z 139 above the desk
(= `W.Z_BLOCK_FACE`), so the magnet face is at the real h 5..40 and servo pulses mean the same heights as on the plotter.

Choice (24 Nov): real wrist on a dummy block, not a separate servo + magnet jig, because it tests the real
[[Parallelogram lift]] geometry, harness and pulse-to-height table; a jig would test only the electronics.
The head is 34 mm wide (block 27) for 2.4 mm walls round the inserts, so the X belt riser, clamp and chain post stay off.
Checks: no touch at 5 lifts x 4 wrist angles, DFM clean, CoM 62 mm inside the U foot ([[Stability and tipping]]).
Related: [[Bring-up]], [[Magnet release]], [[Design rules (DFM)]].
