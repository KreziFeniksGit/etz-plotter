---
tags: [decision]
updated: 2026-11-06
---
# Cartesian plotter instead of SCARA

**Chosen 10 Oct (Egor approved).** The first design was a SCARA arm (history in `docs/history/`).

Why Cartesian: straight axes are simple to model, calibrate and reason about; accuracy does not depend on joint angles;
the field is a rectangle; homing switches give an absolute reference every run ([[No encoders]]).
Cost: the device is big for the 350 x 500 zone 1, and the X travel only just covers the field ([[X reach shortfall]]).

Related: [[ETZ Plotter]], [[Machine coordinates]], [[Accuracy budget]].
