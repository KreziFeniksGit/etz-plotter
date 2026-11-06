---
tags: [concept, rule]
source: docs/design_rules.md
updated: 2026-11-06
---
# Design rules (DFM)

Egor's rules for every printed part: parameters at the top; tolerances from named constants (TOL_MOVE 0.4, TOL_PRESS 0.12,
TOL_BOLT, TOL_MOTOR 0.2); walls >= 2.4 mm; fillets on internal corners; overhang <= 45 deg; bridges < 10 mm; fits 220 x 220;
M2..M5 + Ruthex inserts; zip-tie slots. Checked automatically by `wrist/dfm.py`.
Related: [[Tolerance coupons]], [[Zip-tie features]], [[CAD Pipeline]], [[Never guess a bought-part dimension - mark VERIFY]].
