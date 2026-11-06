---
tags: [concept, goal]
source: docs/pcb_guide.md
updated: 2026-11-06
---
# Measure everything

**Egor's goal (27 Oct):** the ESP32 measures every voltage, current and state it can reach, live in the dashboard.
Why: he nearly burned a motor and found a drained battery by accident.
Now measured: battery voltage, drive power on/off, TMC2209 status/temp/load, chip temp/RAM, motor temp estimate.
Next: [[INA226 (planned)]] in the battery lead; rail dividers on GPIO4/13/14. No new PCBs: add-on modules and wires.
Related: [[Battery guard]], [[Heat model]], [[Black box]], [[Split single-sided PCBs]].
