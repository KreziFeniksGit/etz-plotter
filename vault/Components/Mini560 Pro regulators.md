---
tags: [component, decision]
source: components.csv
updated: 2026-11-06
---
# Mini560 Pro regulators

Two Mini560 Pro 5 V step-down modules (**Egor, 22 Oct**): #1 logic (ESP32, magnet, connector C), #2 servo rail.
Why two: servo current spikes must not reset the ESP32. There is no 6 V version; never the 9 V one (MG996R max 7.2 V).
Footprint from Egor's photo (`pcb/split_boards.md`). Related: [[Power tree]], [[MG996R servo]].
