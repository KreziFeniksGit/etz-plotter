---
tags: [concept]
source: laptop/machine.py
updated: 2026-11-06
---
# Field transform

Field (official mm) <-> machine (carriage) mapping. Nominal: mx = 564.5 − Y, my = 116.5 + X; magnet = (PXB + 110, PYC + 18.5).
The sheet may be 5 mm off and 3 deg turned, so every run the camera finds the 3 ArUco marks and a rigid least-squares fit
(rotation + shift) gives the real transform; the residual shows a bad detection.
Theory link: [[Vision geometry]], [[Geometry and navigation]]. Related: [[Official ETZ field coordinates]], [[X reach shortfall]], [[Vision pipeline]].
