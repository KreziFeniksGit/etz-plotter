---
tags: [concept]
updated: 2026-11-06
---
# Heat model

Firmware v4 guard: estimates motor temperature from current and time (first-order model, rise ~80 K at rated current, tau)
and stops a motor before it cooks. Born from Egor almost burning a stepper left on (25 Oct).
Numbers are VERIFY. Related: [[Idle watchdog]], [[Crash detection]], [[Measure everything]], [[Firmware]].
