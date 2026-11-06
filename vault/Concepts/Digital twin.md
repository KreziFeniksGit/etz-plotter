---
tags: [concept, decision]
source: laptop/twin.py
updated: 2026-11-06
---
# Digital twin

`laptop/twin.py`: a fake ESP32 that speaks the exact [[Serial protocol]] plus field physics (checkers, stacks, pick within
a capture radius, drop that lands / tips, crash when moving low, battery drain, Start button).
**Why (29 Oct):** the plotter does not exist yet; the twin lets the [[Run program]] and [[Route planner]] be tested end to end.
Proof it pays: [[The twin finds real bugs before the hardware exists]].
Limits: capture radius, servo speed, magnet timings are guesses until [[Bring-up]] - [[Say plainly what was only compiled or simulated]].
Used by the dashboard `--demo`. Related: [[Laptop Software]], [[Firmware]].
