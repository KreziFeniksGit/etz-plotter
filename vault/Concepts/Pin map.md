---
tags: [concept]
source: wiring.md
updated: 2026-11-06
---
# Pin map

ESP32-S3 GPIO use (source `wiring.md` section 2): UART to drivers 5/6; STEP/DIR X 18/8 (as built), Y 16/17, wrist 7/15 (as built);
magnet 1; battery 2; stop sense 42; servo 41; I2C 40/39; home X 38, Y 48; start 47; red LED 21; connectors A 9, B 10, C 11/12.
Free: 4, 13, 14. Avoid strapping, USB, flash, PSRAM pins.
Lessons: [[Fix crossed cables in pins.h, not with a soldering iron]], [[GPIO38 and GPIO48 are inputs only]].
Related: [[ESP32-S3 DevKitC-1]], [[Electronics]].
