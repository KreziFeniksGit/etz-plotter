---
tags: [lesson]
updated: 2026-11-06
---
# Fix crossed cables in pins.h, not with a soldering iron

**What happened:** Controlling the wrist moved X and the other way round: the J1 and J3 cables were crossed. Egor: "just switch them in the code".

**Rule:** Swap STEP/DIR in `firmware/include/pins.h`, write the as-built mapping in `wiring.md` so the docs stay true.

Related: [[Pin map]], [[Firmware]]
