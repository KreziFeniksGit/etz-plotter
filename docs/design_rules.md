# Design rules Egor gave (follow them strictly)

Act as an expert mechanical engineer and CAD specialist.

1. **Parametric design and structure**: all dimensions as named variables at the top of each script; modular, separately printable parts; commented code.
2. **Tolerances and clearances**: moving parts 0.3-0.5 mm (TOL_MOVE 0.4); press fits 0.10-0.15 (TOL_PRESS 0.12); bolt holes +0.2-0.3 (TOL_BOLT 0.25); motor and servo mounting holes +0.2 (TOL_MOTOR 0.2). Final values come from the tolerance coupons (tolerance/README.md).
3. **Design for 3D printing (DFM)**: walls at least 2.4-3 mm (WALL_MIN 2.4); no sharp internal corners (fillets everywhere, FILLET_IN 1.5, external FILLET_OUT 1.0); overhangs at most 45 deg; bridges under 10-15 mm; parts must fit a 220 x 220 bed (Ender-3 V3 class, 0.4 nozzle, PETG).
4. **Standard hardware**: metric M2..M5, heat-set inserts (Ruthex M3 x 5.7, hole INSERT_D 4.0 x 6.5), cable management features (zip-tie slots 3 x 1.8, channels).
5. **Workflow and communication**: explain design choices; give assembly notes and a BOM; never guess dimensions: mark unknown bought-part sizes VERIFY and ask Egor to measure.

Checked automatically by `wrist/dfm.py` (walls, overhang, bridges, sharp concave edges) for every printed part and coupon.
