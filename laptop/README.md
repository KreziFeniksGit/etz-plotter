# Laptop vision (Python 3.12 + OpenCV)

Finds the field by its ArUco marks (27, 28, 29), then the coloured checkers (red, green, blue, yellow, magenta) and QR
codes, and tells which **cell** each one is in. Own algorithms on OpenCV building blocks (allowed by the rules).

| File | What |
|---|---|
| `field.py` | the real ETZ field (A4 portrait): columns А..Е (А right), rows 0..8, buffer row above (А..Д), marks 27 (origin, bottom-right), 28, 29. Measured from the official drawing: marks fit to 0.2 mm, cell centres to 0.3 mm |
| `vision.py` | field homography, checker detection (colour + cell), QR reading (whole picture, then cell by cell) |
| `show_field.py` | shows the test field in a window with random checkers and QR codes (no printer needed) |
| `camera_test.py` | live camera: draws what it found, prints it |
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
