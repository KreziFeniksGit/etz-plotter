---
tags: [hub]
updated: 2026-11-06
---
# Laptop Software

Python 3.12 (`laptop/.venv`). The laptop plans and commands; the ESP32 executes. Wired link only, fully offline ([[Competition Rules]]).

Chain: [[Vision pipeline]] -> [[Field transform]] -> [[Task registry]] -> [[Route planner]] -> [[Run program]] -> [[Serial protocol]] -> ESP32 or [[Digital twin]].
- Official coordinates: [[Official ETZ field coordinates]]
- Machine numbers in one place: `laptop/machine.py` + `machine_cal.json` ([[Machine coordinates]])
- Dashboard: `esp_dashboard.py` (`--demo` runs on the twin)
- Self-tests: twin, tasks, route_planner, run, selftest (vision) - all must PASS.
- Lessons: [[The twin finds real bugs before the hardware exists]], [[Do not react to your own abort messages]], [[Check coordinates against the official document]]
- Theory links: [[Vision geometry]], [[Prefix sums]]
