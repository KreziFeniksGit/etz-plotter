---
tags: [concept]
updated: 2026-11-06
---
# Crash detection

StallGuard load readings from the [[TMC2209 drivers]] during a move; a sudden load jump = crash -> stop + `event crash`.
The [[Run program]] aborts and parks. Idea: sensorless homing backup, mechanical fingerprint (`docs/ideas.md`).
Related: [[No encoders]], [[Firmware]].
