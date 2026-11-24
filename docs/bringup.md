# Bring-up: from the first power-on to the first task (real plotter)

Do the steps in order; each has the commands (serial monitor or the dashboard's command box) and a pass check.
Numbers you measure go into `laptop/machine_cal.json` (keys in brackets; `laptop/machine.py` has the defaults), and
firmware settings into a profile with `save`. Commit `machine_cal.json` after each session.
Before anything: practise the whole run on the digital twin (`python laptop/run.py`, board = TWIN).

## 0. Battery (do this first - see pcb/review_2026-10-27.md)
- Multimeter on the pack and on each cell (balance lead). 4S: 3.7..4.2 V per cell. A cell under 3.0 V: charge on a
  balance charger at 0.1-0.2 C; under ~2.5 V or swollen: do not use the pack.
- Compare the multimeter with the dashboard's battery number; more than 0.3 V apart -> tell Claude (calibration factor).
- Unplug the battery after every session (the logic regulator drains it, docs/pcb_guide.md section 4).

## 1. First power-on
1. Motors unplugged, battery on, stop button released. Dashboard -> Connect -> **Self-test**.
   Pass: drive power on, battery >= 14.8 V, all 3 drivers answer, "settings arrived", "sees STEP and DIR", "counts our steps".
2. Plug the motors (power off while plugging!). Self-test again.

## 2. Directions
- `r x 0.1`, `r y 0.1`: the carriage must move towards larger machine x / y (away from the home switch side).
  Wrong way: `dir x` / `dir y`, then `save`.
- Wrist: `r w 0.25` turns a quarter; note which way (positive = counter-clockwise seen from above is our convention;
  else `dir w`).

## 3. Home switches and homing
1. Self-test shows "home switches: X free, Y free". Press each switch by hand: it must show PRESSED (NC wiring: a
   broken wire also reads PRESSED, which is the safe side).
2. `home x`, then `home y` (`home all` later). Pass: `ok home x`, the carriage stops gently at the switch.
3. With the carriages at home, measure the CAD positions: X carriage pivot x and Y carriage centre y from the
   polygon's corner -> [`home_pxb`, `home_pyc`] (CAD park = 287 / 40). Machine x = polygon x + 13 (v2.17: the machine
   stands 13 mm further from the field, plywood -x edge 77 mm from the polygon edge), so add 13 to the measured x.
4. Soft limits: after homing, `gomm x 200` must answer `err limit x`.

## 4. Steps per mm
1. `home all`, mark the carriage on the profile, `gomm y 200`, measure the real distance D with a ruler.
   [`steps_per_mm_y`] = 80 x 200 / D. Same for X with 120 mm. Expect 80 +- 1.
2. `gomm y 0` -> it returns to the mark (within 0.2 mm: else the belt slips or the pulley grub screw is loose).

## 5. Speed (ETZ: at least 100 mm/s = 8000 steps/s)
- The firmware default (3200 steps/s = 40 mm/s) is BELOW the rule. run.py sets the speeds from machine_cal.json at
  every start, but also set them in the board: `speed 8000`, `accel 40000`, `jerk 20`, `save`.
- `tune x` / `tune y` (needs the carriage in the middle and free travel both ways) -> fastest reliable values;
  write 70 % of them into [`speed_x`, `accel_x`, ...] and `save`.

## 6. Servo lift
1. `servo 1500`: arms level? Measure the magnet face height above the table: should be about 22.5 mm.
2. Find the pulse for face height 5 mm (touching a single checker: 5 mm) and for 40 mm: `servo 1300`, `servo 1700`...
   With us5, us40: [`servo_us_per_deg`] = |us40 - us5| / 25.2, [`servo_sign`] = +1 if us40 > us5 else -1,
   [`servo_us_level`] = the pulse at 22.5 mm (or the mean of us5 and us40).
3. Time a full 5 -> 40 mm move with the phone's slow-motion video -> [`servo_s_per_deg`] = time / 25.2.

## 7. Magnet
1. A checker on the sheet, magnet face on it (`servo` to the 5 mm pulse), `mag on`, lift: it must hold through a
   fast move (`linemm`) and a wrist turn (`wrist 180`).
2. `mag off` over a cell from 1 mm above: it must drop at once. If it sticks (the M8 washer stays magnetised):
   there is no reverse pulse in our hardware (one low-side MOSFET) -> add a thin non-magnetic spacer (tape / felt)
   on the magnet face, or raise [`mag_release`].
3. Capture radius: put the checker 2, 4, 6, 8 mm off the magnet axis, lower, `mag on`, lift: the largest offset that
   still picks reliably (5 of 5) -> [`capture_r`]. Note how far off-centre it then hangs (does it self-centre?).

## 8. Wrist zero
- Before every power-on set the wrist to its mark by hand (no home sensor). `wrist 0` must then point it at the mark.

## 9. Camera (after the camera is chosen)
- Intrinsics: print a chessboard, 15 photos, OpenCV calibrateCamera (script to be written).
- Camera -> magnet offset: put a checker under the magnet, move the camera over it, read its position in the image;
  the difference = the offset (to be added to machine.py).
- Field check: scan, then send the magnet over mark 27, 28, 29 (run window / `linemm`): must be within 1 mm of the centres.

## 10. Reach check (fixed in the model v2.17)
- v2.17: X travel PXB 287..452 and the machine 13 mm further from the field (plywood -x edge 77 mm from the polygon
  edge). Even with the sheet at the ETZ limits (5 mm off, 3 deg turned) every cell is in reach, with about 1 mm to spare
  at each end (before: up to 11.9 mm short). The margin is small: place the base carefully (77 mm), and check on the real
  machine: `home all`, then `gomm x 0` / `gomm x 165` and see that the magnet covers row А and row Е with the sheet
  pushed 5 mm toward each side. If the real switch or rail end costs travel, run.py still clamps and warns.

## 11. First tasks (ETZ 4.2)
1. On the twin first: `python laptop/run.py`, TWIN, task 1 (Д1 -> Д5), Enter task, Start.
2. Real plotter: board = COM port, task 1, Enter task (red LED on), put the checker in Д1, press the real Start button.
3. Then task 2 (far along one axis) and task 3 (three on a line), then the stack task 6.
4. Each run: note the run time and any clamp / crash warnings in the log.

## 12. Save
- `save` (power-on profile `boot`), `save fast` for the tuned profile; commit `laptop/machine_cal.json`.
