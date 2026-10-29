---
paths:
  - "firmware/**"
---
# Firmware (ESP32-S3, PlatformIO)

- No outside libraries (Egor's rule): only the Arduino core and ESP-IDF; our own libs live in `firmware/lib/`.
  Ideas and algorithms from other projects are fine, the code is ours.
- Build: `~/.platformio/penv/Scripts/pio.exe run` in `firmware/` - 0 errors, 0 warnings. Upload only when Egor has the
  board plugged in: `-t upload --upload-port COM3`.
- The serial protocol is shared with `laptop/twin.py` (the digital twin) and `laptop/run.py`. When a command, reply,
  event or json field changes, change the twin to match and run `laptop/.venv/Scripts/python laptop/twin.py --test`
  and `laptop/run.py --test`. Update the command table in `firmware/README.md` and the pins in `wiring.md`.
- Say plainly what was only compiled and never run on hardware; the first real test of anything new goes into
  `docs/bringup.md`.
- Our hardware limits (do not promise what the board cannot do): the magnet is one low-side MOSFET (no reverse release
  pulse); the logic regulator stays on the battery (drains it when parked); battery divider 100k/15k (x7.67) on GPIO2.
