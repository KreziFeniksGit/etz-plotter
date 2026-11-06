---
tags: [concept, rule]
updated: 2026-11-06
---
# ETZ speed minimum

ETZ: manipulator speed at least 100 mm/s (not measured, but task time is computed from it). 100 mm/s = 8000 steps/s at 80 steps/mm.
The firmware default 3200 steps/s = 40 mm/s is below it - run.py sets speeds every run ([[Firmware defaults must meet the rules]]).
Related: [[StepGen motion]], [[GT2 belts and pulleys]], [[Competition Rules]].
