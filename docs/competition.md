# Competition day (ETZ 2026-27 final)

Sources: short ETZ (docs/etz_kratko_26_27.pdf, summary in docs/etz_rules_summary.md). The testing order, scoring and
time per task are only in the FULL ETZ (not in the repo yet) - fill the gaps below when it arrives.

## ETZ 4.3 self-check, mapped to our device
| ETZ check | Our device | Status |
|---|---|---|
| stands only on its zone; before / after the run entirely over zones 1 + 2 | base on zone 1; parked pose checked in CAD (`assembly.py`: parked in zones) | check on the real build |
| drives from batteries <= 16 V; stop button cuts the drives | 4S LiPo 16.8 V max (nominal 14.8 V); latching stop with 2 NC blocks (drive bus + magnet 5 V) | 16.8 V full charge: ask the organisers whether "nominal <= 16 V" is what counts (it should be) |
| edges rounded, wires insulated and fixed | fillets on every printed part; zip ties modelled | check on the build |
| wired link only, laptop offline | USB cable; ESP32 radio never started (no Wi-Fi / BT code); laptop: turn Wi-Fi off | |
| red LED (program running), green LED (drives powered), Start button | red LED GPIO21 (`led red`), green LED from the drive bus, Start GPIO47 (`event start`) | firmware for LED / Start: fw session 29 Oct |
| connectors A, B, C and a breadboard (>= 400 contacts at the final) | A/B/C on the controller board (dividers, PTC on C); breadboard on the panel | breadboard size: check it is >= 400 |
| interface: task number, parameters | run.py window: task list + parameter boxes | |
| own control system and program | own firmware (no outside libraries), own laptop programs | |

## The run (ETZ 3.5 cycle) with run.py
1. Before the slot: battery charged (>= 15.5 V), wrist on its mark, `selftest` PASS, camera check.
2. Choose the task number and type the parameters -> **Enter task** (red LED goes on).
3. The judges set out the checkers. **Do not touch anything.**
4. Press **Start on the device** (the only action allowed while red is on).
5. The program: home, scan, plan, moves, park, red LED off. Watch the log; do not touch the laptop unless it stops.

## Pre-run checklist
- [ ] battery >= 15.5 V (dashboard), cells balanced
- [ ] stop button released, green LED on
- [ ] wrist set to its mark before power-on
- [ ] `selftest` PASS (drivers, pins, step counting, switches), camera PASS
- [ ] plotter parked inside the zones
- [ ] laptop: Wi-Fi off, power cable in, run.py open on the right COM port, profile `fast` loaded
- [ ] sheet: if it lies near the 5 mm / 3 deg limits, ask the judges whether it may be straightened (reach, docs/bringup.md 10)

## When something goes wrong
| Symptom | Likely cause | What to do |
|---|---|---|
| NO ANSWER from drivers | drive power off, stop pressed, battery | release stop, check battery, Self-test |
| CRASH event | moved low over a stack / collision / StallGuard false alarm | run.py re-homes and parks; check the field; if false alarm: `crash x 0` for that axis |
| HOT event | motor estimate over 90 C | let it cool; lower `cur` or `hold`; check the heat model numbers |
| battery low / stop | pack below 14.8 / 14.0 V | swap / charge the battery |
| checker not picked | capture radius, scan offset, magnet weak | check camera->magnet offset, `capture_r`, magnet hold % |
| checker sticks to the magnet | washer magnetised | spacer on the magnet face, longer `mag_release` |
| placed > 10 mm off | sheet near the reach limit (row Е / А), calibration | clamp warnings in the log; check steps/mm and the field fit |
| watchdog event | USB cable / laptop froze | check the cable; re-run |

## Practice plan
1. Twin: every task type, random layouts, with faults (run.py --test) - until the procedure is automatic.
2. Real plotter, single checker: task 1 x 20 runs; log time and placement error (ruler from the cell dot).
3. Stacks of 2..5 and taking the top of a stack; rotation.
4. Timed full runs of mixed tasks; target: every checker within 5 mm, no crash, run time ~ the planned time + 10 s.
5. Practise the whole cycle with a friend as the judge (arming, set-out, Start, no touching).

## Open questions (organisers / full ETZ)
- scoring per checker, penalties, time limit per task, number of attempts
- the 10 final task formats (add them to `laptop/tasks.py` TASKS)
- "nominal <= 16 V": 4S LiPo is 14.8 V nominal, 16.8 V full - confirm it is accepted
- is a self-designed PCB carrying plug-in TMC2209 modules "own control electronics" (it should be)
- V pin voltage of connectors A and B
- may the sheet be straightened if it lies near the 5 mm / 3 deg limits?
