---
paths:
  - "laptop/**"
---
# Laptop programs (Python 3.12, venv `laptop/.venv`)

- Python: `laptop/.venv/Scripts/python.exe` on Windows (`laptop/.venv/bin/python` on Linux). Do not set shell
  variables inside a chained command (`.venv=...` once broke a chain and silently skipped later steps).
- After a change run the self-tests that cover it; all must PASS:
  `twin.py --test`, `tasks.py --test`, `route_planner.py --test`, `run.py --test`, `selftest.py` (vision, 10/10).
  The GUI smoke test: `esp_dashboard.py --demo`.
- Coordinates are the OFFICIAL ETZ field frame (`field.py`: origin = ArUco 27, cell X = 28 x column, Y = 28 x row);
  machine numbers come only from `machine.py` / `machine_cal.json`, never hard-coded elsewhere.
- `twin.py` must keep speaking exactly the firmware protocol (`firmware/README.md`); change both together.
- Numbers the twin assumes (capture radius, servo speed, magnet timings) are guesses until bring-up measures them:
  say so when a result depends on them.
