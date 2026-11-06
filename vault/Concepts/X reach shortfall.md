---
tags: [concept, risk, open]
updated: 2026-11-06
---
# X reach shortfall

**Found 29 Oct.** X travel (magnet x 397..540) only just covers the field. With the sheet at the ETZ limits (5 mm, 3 deg)
a cell centre can lie 11.9 mm (row Е) / 8.1 mm (row А, buffer) outside reach (`machine.worst_reach_shortfall()`).
Now: run.py clamps and compensates. Real fix: ~20 mm more X travel (longer [[MGN12 rails]] + boom). Decide after measuring the build ([[Bring-up]] step 10).
Cause chain: [[17HS4023S wrist stepper]] moved the magnet axis. Related: [[Field transform]], [[Open Items]].
