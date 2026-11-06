---
tags: [concept]
source: laptop/route_planner.py
updated: 2026-11-06
---
# Route planner

`laptop/route_planner.py`: orders the checker moves to minimise time - randomised greedy + local polish, stack legality,
buffer use, turn-in-place moves, real start positions, times from `machine.py`. The naive order is always a candidate.
Result: ~18 % faster than checker-by-checker on 200 random tasks.
Theory link: [[Prefix sums]] / algorithm speed ([[Count operations before writing code]]).
Related: [[Task registry]], [[Run program]], [[Laptop Software]].
