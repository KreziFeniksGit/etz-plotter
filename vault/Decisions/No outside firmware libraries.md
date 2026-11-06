---
tags: [decision, rule]
updated: 2026-11-06
---
# No outside firmware libraries

**Egor, 24 Oct:** "do everything raw, then split our code into our own libraries". Only the Arduino core / ESP-IDF.
Why: the ETZ demands own algorithms (libraries like AccelStepper are allowed, but own code is safer and he learns it);
GRBL / Marlin / G-code are banned anyway.
How: adapt ideas from other projects, write the code ourselves; libs in `firmware/lib/` ([[Firmware]]).
Related: [[StepGen motion]], [[TMC2209 drivers]], [[Competition Rules]].
