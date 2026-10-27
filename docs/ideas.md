# Ideas: things we can still build (25 Oct)

Already done (firmware v4, dashboard, `laptop/route_planner.py`): heat guard, self-test, crash detection, black box,
auto-tune, settings profiles in flash, S-curve + coordinated XY lines, route planner, idle off, laptop watchdog,
driver auto-setup, memory view. Still open from the first list: battery guard (6), smart magnet (5), lost-step check (4).

**Goal (Egor, 27 Oct): measure everything** - every voltage, current and state the ESP32 can reach, live in the dashboard.
No new PCBs: add-on modules and wires. Plan and pin list: `docs/pcb_guide.md` section 5 (next step: INA226 in the battery
lead, own driver; rail dividers on GPIO4 / 13 / 14).

Each idea: what it is - why it helps.

## Speed (the run time is the score)
1. **Overlap lift and travel** - start the XY move as soon as the magnet clears the stack, lower it during the deceleration. Saves ~0.3 s per move.
2. **Wrist turns during the travel** - firmware runs the wrist at the same time as the XY line (the planner already counts it that way).
3. **Load-aware speed** - fast profile when empty, gentle (S-curve, lower accel) when carrying a 4-5 stack; chosen per move automatically.
4. **Run the whole plan on the ESP32** - the laptop sends the full list of moves once; the ESP32 runs them back to back without USB round trips (no 50-100 ms gaps).
5. **Input shaping** - measure the frame's wobble frequency (camera or load reading) and shape the moves so it does not ring after a stop; allows higher accel.
6. **CoolStep** - let the driver lower the current automatically when the load is small: cooler motors, more battery.
7. **Better route search** - add stack-aware "buffer" choices and longer local search (or-opt) in the planner; try 1000s of orders in the background while the camera reads the field.
8. **Pick the nearest of equal checkers** - when the task only says "a red checker", choose the red one that gives the shortest route.

## Accuracy and vision
9. **Field found by the camera** - read the ArUco marks at the start and compute the field -> machine transform; no manual alignment at all.
10. **Place check** - after each place, a photo checks the checker is within 10 mm of the cell centre; if not, nudge it.
11. **Calibration map** - photograph the grid at many points once; store a correction table (belt stretch, skew of the axes).
12. **Pick check** - confirm a checker is really on the magnet (distance sensor or camera); retry if not.
13. **Stack height check** - distance sensor before and after each place: the stack grew by exactly 5 mm.
14. **Colour calibration** - one look at a white sheet / known checker at the start fixes the colour thresholds for the hall's lighting.
15. **Wrist ring light** - a small LED ring on the wrist, switched by the ESP32: the same light for every photo.
16. **Multi-frame voting** - read colour / QR / ArUco on 3-5 frames and take the majority: fewer misreads.
17. **Picture stickers** - recognise the sticker pictures with template matching or a tiny offline network trained on our own photos.
18. **Steps/mm wizard** - move a known distance, measure it with the camera, store the exact steps/mm per axis.
19. **Backlash measurement** - in `tune`, measure the play on direction reversals and add it in the firmware.

## Reliability
20. **Battery guard** - read the battery all the time, warn early, slow down when it sags, park before brownout.
21. **Smart magnet** - full power to grab, ~40 % to hold, short reverse pulse to release (the washer stays slightly magnetised).
22. **Magnet on-time limit** - the magnet switches off if held too long (it heats up).
23. **Resume after a reset** - keep the run's progress in RTC memory; after a brownout restart, continue from the last finished move.
24. **Sensorless homing backup** - if a home switch fails, home by the load reading against the end stop.
25. **Soft limits** - after homing, the firmware refuses any target outside the travel (never hits the ends).
26. **No-go zones** - posts, cable chain, the field edge: moves are planned around them.
27. **Mechanical fingerprint** - store the normal load readings per axis; a later drift means a loose belt, screw or bearing.
28. **Driver temperature trend** - log driver chip temperatures; warn before they reach the limit.
29. **Lost-step check** - after a run, touch the home switch and compare; re-home by itself if off.
30. **Hang watchdog** - the ESP32's own task watchdog: if the program ever hangs, motors off and a clean restart (black box keeps why).
31. **Binary protocol with CRC** - laptop <-> ESP32 messages that cannot be misread because of noise on the cable.
32. **Stop-button reaction** - the firmware sees the stop button (STOP_SENSE) and freezes the plan at once, so it can resume cleanly.

## Competition day
33. **Pre-run checklist screen** - one screen: battery, drivers, camera, field found, task loaded, all green = ready.
34. **Run history** - every run's time, errors and plan saved; compare practice runs.
35. **Digital twin** - simulate the whole run on the laptop with real timings before pressing start.
36. **Task number entry** - type the task number, the program loads its parameters and shows the plan.
37. **Speed run / safe run switch** - one click between the tuned fast profile and a careful one.
38. **LEDs and start button per the rules** - green = drives powered, red = program running, start button starts it.
39. **Auto-park** - after the run or any error, park inside zones 1-2 (rule: projection inside before and after).
40. **Radio-off proof** - the firmware checks at runtime that Wi-Fi / Bluetooth were never started and prints it.
41. **Live time budget** - planned vs real time per move while it runs.
42. **Replay video** - record the camera with the plan drawn on top, for debugging after a run.

## Tools
43. **Firmware version + git hash** printed at boot and checked by the laptop (no "which version is on the board?").
44. **Profile backup** - the dashboard saves the ESP32 profiles to a laptop file and can restore them.
45. **Live graphs** - speed, load, motor temperature over time in the dashboard.
46. **Keyboard jog** - arrow keys move X/Y in the dashboard (0.1 / 1 / 10 mm steps).
47. **PC tests for the firmware libraries** - PlatformIO "native" environment: StepGen, CrashDetector, HeatModel tested on the laptop.
48. **mm everywhere** - commands in mm and degrees instead of steps.
49. **Connector A/B/C tools** - read connector A (analog), B (digital), talk on C (UART 9600) from the dashboard: ready for any sensor the judges give.
50. **One-click full check** - self-test + camera + field detection + a short test move of each axis, with a printed report.
