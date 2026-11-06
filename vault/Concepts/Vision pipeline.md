---
tags: [concept]
updated: 2026-11-06
---
# Vision pipeline

`laptop/vision.py`: ArUco marks (DICT_4X4_50, 27/28/29) -> field; checkers by colour; stickers (ArUco, AprilTag, QR, pictures).
Self-test 10/10 on rendered fields. Real scan blocked by [[Camera (not chosen)]]. Lighting: any room light - idea: own ring light,
colour calibration, multi-frame voting (`docs/ideas.md`).
Theory link: [[Vision geometry]]. Related: [[Field transform]], [[TOF400C distance sensor]], [[Laptop Software]].
