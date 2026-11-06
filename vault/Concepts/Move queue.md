---
tags: [concept]
updated: 2026-11-06
---
# Move queue

Firmware v5: `q <cmd>` adds a line, `qrun` runs them back to back - each starts when motors, servo and waits finish.
Why: no USB round-trip gaps (50-100 ms each) between moves. An `err` or any guard event stops it (`event q stopped`).
The [[Run program]] sends one queue per checker move. Related: [[Serial protocol]], [[Firmware]].
