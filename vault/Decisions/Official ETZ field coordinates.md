---
tags: [decision]
source: laptop/field.py
updated: 2026-11-06
---
# Official ETZ field coordinates

**29 Oct:** `laptop/field.py` was rewritten to the official frame: origin = centre of ArUco 27; cell = row letter
А..Е + column 0..8; centre X = 28·column, Y = 28·row (А = 1): Б3 = (84, 56). Buffer = column 9 (X 252), rows А..Д.
Marks 27 (0,0), 28 (224,0), 29 (252,168). The old frame was transposed and mirrored - names matched, coordinates did not.
Lesson: [[Check coordinates against the official document]]. Used by [[Field transform]], [[Task registry]], [[Route planner]].
