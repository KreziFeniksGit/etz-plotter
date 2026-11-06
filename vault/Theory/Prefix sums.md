---
tags: [theory, open]
source: theory/sets/03_task7.py
updated: 2026-11-06
---
# Prefix sums

1D: P[i] = a[0] + ... + a[i−1]; sum(l..r) = P[r+1] − P[l]. 2D: P[i][j] = sum of the rectangle above-left;
rect sum = P[x2][y2] − P[x1][y2] − P[x2][y1] + P[x1][y1]. Turns 10^5 queries from O(n·m) each into O(1).
Egor asked to **redo it** (31 Oct): understood only with a worked table; next time write it from scratch, then a new task without hints.
Related: [[Count operations before writing code]], [[Theory error log]], [[Route planner]].
