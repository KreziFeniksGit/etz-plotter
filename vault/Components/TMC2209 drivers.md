---
tags: [component]
source: wiring.md
updated: 2026-11-06
---
# TMC2209 drivers

BIGTREETECH TMC2209 V1.3 modules x4 (X, Y, wrist, spare) on headers, UART on one PDN_UART wire (addresses X 0, Y 2, wrist 3).
StealthChop, current set over UART; EN tied to GND, off = TOFF 0. They answer UART only when VM (motor power) is on.
Our own `Tmc2209` library ([[No outside firmware libraries]]). Load reading (StallGuard) feeds [[Crash detection]];
temperature flags feed [[Heat model]]. Allowed by the ETZ (same class as TMC2208).
Related: [[Pin map]], [[Firmware]].
