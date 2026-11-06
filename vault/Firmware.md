---
tags: [hub]
source: firmware/README.md
updated: 2026-11-06
---
# Firmware

ESP32-S3, PlatformIO, Arduino core only: [[No outside firmware libraries]]. Versions v1 (borrowed libs) -> v3 own libs (24 Oct) -> v4 guards (25 Oct) -> v5 machine commands (29 Oct, compiled only).

Own libraries in `firmware/lib/`: Tmc2209 ([[TMC2209 drivers]]), StepGen ([[StepGen motion]]), Console ([[Serial protocol]]), Settings (profiles in flash), BlackBox ([[Black box]]), Guard ([[Heat model]], [[Crash detection]]), Inputs ([[Homing and soft limits]]), Magnet ([[Magnet release]]), MoveQueue ([[Move queue]]), SlewServo ([[MG996R servo]]).

Also: [[Battery guard]], [[Idle watchdog]], [[Radio never started]], [[Pin map]].
The laptop's [[Digital twin]] speaks the same [[Serial protocol]]: change both together.
Lessons: [[Check the wiring before blaming the firmware]], [[Firmware defaults must meet the rules]], [[Say plainly what was only compiled or simulated]].

Source: `firmware/README.md` (every command and reply).
