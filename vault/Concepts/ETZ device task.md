---
tags: [concept, rule]
source: docs/etz_rules_summary.md
updated: 2026-11-06
---
# ETZ device task

The device finds checkers (26 x 5 mm, steel washer, 5 colours) on an A4 field (9 x 6 cells of 28 mm + buffer column, ArUco 27/28/29),
moves / stacks (<= 5) / rotates them to cells given by the task; reads colours, ArUco/AprilTag/QR, pictures.
Placed = centre within 10 mm, lid up. Regional: one of 6 tasks; final: one of 10. Task + params before the red LED; Start is the only action.
Footprint: rests on zone 1 (350 x 500); before/after inside zones 1+2. Batteries <= 16 V; no printer boards / GRBL / G-code; wired offline laptop.
Related: [[Official ETZ field coordinates]], [[Accuracy budget]], [[Task registry]], [[Competition Rules]].
