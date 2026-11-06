---
tags: [lesson]
source: docs/pcb_guide.md
updated: 2026-11-06
---
# Route PCB traces only at 0, 45 and 90 degrees

**What happened:** 27 Oct: Egor noticed odd angles (99, 113, 146 deg) on the hand-routed boards - the script drew straight lines to off-grid pads. No acute angles (acid traps) existed, so they work.

**Rule:** Route only 0/45/90; add a short 45 deg jog before an off-grid pad. 90 deg corners are fine electrically at our speeds.

Related: [[Home toner transfer PCB rules]], [[Split single-sided PCBs]]
