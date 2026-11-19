# Laptop programs (Python 3.12)

## ESP32 dashboard
`laptop\.venv\Scripts\python laptop\esp_dashboard.py` (add `--demo` to try it without the board). Close the PlatformIO
monitor first. Shows each driver live (answers?, position, moving / holding / free, current, load, overheating, short,
open wire), the watchdog, and has buttons: turns, zero, on / off (free), reverse, current, speed / accel, STOP ALL, a
command line and a log. `esp_link.py` = the connection (no board reset on connect, status stream, ping every 0.4 s:
the firmware stops the motors if the laptop goes silent for 1.5 s).

## Vision (OpenCV)

Finds the field by its ArUco marks (27, 28, 29), then the coloured checkers (red, green, blue, yellow, magenta) and QR
codes, and tells which **cell** each one is in. Own algorithms on OpenCV building blocks (allowed by the rules).

| File | What |
|---|---|
| `field.py` | the real ETZ field (A4 portrait): columns А..Е (А right), rows 0..8, buffer row above (А..Д), marks 27 (origin, bottom-right), 28, 29. Measured from the official drawing: marks fit to 0.2 mm, cell centres to 0.3 mm |
| `vision.py` | field homography, checker detection (colour + cell), QR reading (whole picture, then cell by cell) |
| `show_field.py` | shows the test field in a window with random checkers and QR codes (no printer needed) |
| `camera_test.py` | live camera: draws what it found, prints it |
| `cam_stand.py` | camera on the test stand (`camera_stand/`), close up: focus score, checker colour / px per mm / height, QR, ArUco. `--test` = no camera |
| `make_stickers.py` | A4 sheet `out/stickers_a4.png` (300 dpi): 16 ArUco 4x4 (no 27-29), 16 AprilTag 36h11, 16 QR (15 mm), each in a 26 mm cut circle + 100 mm scale bar; reads the sheet back to check every sticker |
| `selftest.py` | no camera: fake photos (tilt, blur, noise, colour cast) of known layouts -> must find everything. Now: 10 / 10 |

## Setup (done once; already done on Egor's PC)
```
py -3.12 -m venv laptop\.venv
laptop\.venv\Scripts\python -m pip install opencv-contrib-python numpy
```

## Test with a webcam and the laptop screen
1. Terminal 1: `laptop\.venv\Scripts\python laptop\show_field.py` - the field opens in a window (resize it); N = new layout (the
   true layout is printed), Q = quit.
2. Terminal 2: `laptop\.venv\Scripts\python laptop\camera_test.py` (**USB webcam is usually `camera_test.py 1`**; 0 = laptop camera). Point
   the webcam at the screen so all three marks are visible. Q quit, P print, S save a snapshot.
3. Compare what it prints with what `show_field.py` printed.

Tips: turn screen brightness up, avoid reflections of lamps/windows on the screen, hold the webcam steady. If colours
come out wrong, tune `SAT_MIN`, `VAL_MIN` and the `HUE` ranges at the top of `vision.py`.
