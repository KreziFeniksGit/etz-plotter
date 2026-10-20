# SCARA arm status (7 October: v3 optimised, no electronics box, 16 V supply, longer Z column)

Older v2 notes are kept below the v3 section. v2 folder is untouched as a fallback.

## Rule constraint
- Max nominal supply voltage is 16 V (4S pack is 14.8 V nominal, 16.8 V charged: check whether the rule counts charged voltage). All torque, speed and power numbers are computed at 16 V.

## v3 current state (folder etz_arm_v3_optimized/)
- Electronics box removed. Bare boards go on a perfboard on 4 M3 standoffs; base plate has 4 M3 holes at (+-45, -165 +- 35) mm in plate coordinates. See bare_electronics_pack.pdf.
- 15 printed designs, 61 screws, 13 nuts, 30 inserts. Fastener check clean.
- Z column extended by 50 mm: rods 220 mm, Tr8 screw 200 mm, taller top mount (ZEXT=50 in parts.py). Stroke is 85 mm, magnet height 5 to 90 mm (hz). Z lead decision: keep Tr8x2 (slow at 16 V, 10 to 15 mm/s; Tr8x4 or a 40 mm Z motor are the faster options). Rod bending over the longer span (~0.1 mm est.) is not in the droop figure.
- J1 bearing span widened from 8 to 15 mm with an internal shelf (arm_boss_ledge), for better moment stiffness.
- Coupler 5 to 8 mm (25 mm) modelled. Collision and fastener checks clean after the extension; platform FE unchanged.
- Audit fixes: Z mount corner notch, link 2 hub skin 1.0 mm, carriage nut-pocket walls +0.8 mm, elbow bearing offset, hardware_bom.csv, stale files cleaned.
- Printability: lip stair-step gussets, platform mid web, wrist bracket webs (8.5 mm bridge, no support), clip tunnel chamfer, cam bracket printed flipped.
- Coupons: 72 unique discs + 10 tolerance plates + compensate.py. Viewer artifact v4 and animation artifact v13 (both with the extended column).
- Accuracy (accuracy_and_test_plan.pdf, 16 V): lateral error at the magnet 5.5 mm worst case / 1.8 mm RSS open loop, 1.6 / 0.44 mm calibrated; vertical 8.5 mm worst, 1.2 calibrated, plus droop 3.2 mm at 3 N.
- J1 at 16 V, 90 deg extended: use smoothed ramps at 0.9 s (margin 2.76); 0.5 s stalls. Fallbacks: 0.59 Nm J1 motor, 4:1 ratio.
- Electronics: 12 V magnet via MOSFET + PWM (duty at most 70 %) + flyback diode; TB6612 cannot take the rail. Peak about 43 W. LM2596 16 V to 5 V.
- Open: mast/boom fixing not modelled, NEMA11 M2.5 engagement 2.0 mm, real test prints (bridges, hub with overlapping solids), J1 stop margin about 2 deg, pulley grub screws, full sequence-aware reach (reach_seq) not rerun after the Z extension, rule wording on charged voltage.

## v2 notes (6 October)
- Link 2 at 2.4 mm: 0.127 mm/N channel only, 0.059 bonded. v3 gives 0.116 / 0.063.
- Droop at the magnet, arm extended, 3 N: 3.2 mm covers screwed, 4.1 mm channels only, 2.6 mm glued, 2.1 mm glued + 2 mm Al platform lid.
- Link 1 0.082 mm/N, platform tilt 0.0033 / 0.0034.
