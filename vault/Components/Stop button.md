---
tags: [component, rule]
source: wiring.md
updated: 2026-11-06
---
# Stop button

22 mm latching mushroom E-stop with TWO NC blocks (ETZ: must cut all drive power). Block 1 cuts the drive bus
(steppers, servo), block 2 the magnet 5 V. The ESP32 stays on and sees the stop on GPIO42 ([[Pin map]]).
Also: green LED on the drive bus (real power state), red LED = program running, Start button = the only action while red is on.
Related: [[Power tree]], [[Competition Rules]].
