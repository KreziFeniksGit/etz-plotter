---
tags: [concept, risk]
updated: 2026-11-24
source: frame/frame.py (PXB_RANGE, FIELD_DX), laptop/machine.py
---
# X reach shortfall

**Found 29 Oct.** The old X travel (PXB 287..430, magnet x 397..540) only just covered the field. With the sheet at the
ETZ limits (5 mm, 3 deg) a cell centre could lie 11.9 mm (row Е) / 8.1 mm (row А, buffer) outside reach
(`machine.worst_reach_shortfall()`).

**Fixed 24 Nov (v2.17), without a longer rail** (Egor: the [[MGN12 rails]] stay 250, boom 270):
- The X belt clamp/riser moved 13 mm to -x, so the X block can go further +x: PXB max 452 (block 4 mm from the rail end).
- The whole machine stands 13 mm further from the field (`frame.FIELD_DX`, polygon x = machine x - 13), so the -x end
  of the field also stays in reach.
- Worst ETZ placement now needs PXB 288.1..451.1: shortfall 0, but only about 1 mm spare each end. Measure the real
  travel at [[Bring-up]] step 10.
- Cost: at PXB 452 the shelf end passes about 7 mm outside the 600 mm polygon edge during the run (allowed; parked stays inside).

Lesson from the fix: [[Check which way a change moves the reach]].
Cause chain: [[17HS4023S wrist stepper]] moved the magnet axis. Related: [[Field transform]], [[Machine coordinates]], [[Open Items]].
