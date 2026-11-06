---
tags: [component, decision]
source: wiring.md
updated: 2026-11-06
---
# ESP32-S3 DevKitC-1

ESP32-S3-DevKitC-1 N16R8 (16 MB flash, 8 MB octal PSRAM). **Egor, 11 Oct**, replaced the Raspberry Pi Pico 2.
Why: fast, many timers (RMT/MCPWM), USB link to the laptop. Cost: it has a radio ([[Radio never started]]) and many
pins are taken (strapping 0/3/45/46, USB 19/20, flash 26-32, PSRAM 33-37) - see [[Pin map]], [[GPIO38 and GPIO48 are inputs only]].
Runs our [[Firmware]]. Link to laptop = COM3 at the bench.
