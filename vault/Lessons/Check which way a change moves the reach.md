---
tags: [lesson]
updated: 2026-11-24
---
# Check which way a change moves the reach

**What happened:** 24 Nov, fixing the [[X reach shortfall]] without a longer rail. The first idea was a longer wrist
shelf (magnet further +x). That gains reach on one side and loses it on the other: the field is short at BOTH ends of
X. The real fix was more carriage travel (belt clamp moved -x) plus moving the whole machine 13 mm away from the field.

**Rule:** Before proposing a geometry fix, write the needed range at both ends (min and max) and check that the change
widens the range, not just shifts it. Do the sum in numbers first (`machine.worst_reach_shortfall()`), then model.

Related: [[Machine coordinates]], [[Field transform]]
