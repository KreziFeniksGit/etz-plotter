# ETZ plotter firmware (PlatformIO, ESP32-S3-DevKitC-1 N16R8)

Current program: **v2** - the three steppers (X, Y, wrist) through the TMC2209 drivers, controlled by text commands
from the serial monitor **or the laptop dashboard** (`laptop/esp_dashboard.py`). Pins: `include/pins.h` (= `wiring.md` section 2). Libraries: TMCStepper (driver
setup and status over UART), FastAccelStepper (step pulses with acceleration made by the ESP32 hardware, so reading the drivers never disturbs the motion) - both general libraries, allowed by the rules.
Wi-Fi and Bluetooth are never started.

## Run it
1. VS Code -> PlatformIO -> Open Project -> this `firmware` folder.
2. Plug the USB cable into the port marked **UART** on the ESP32 board (not "USB").
3. Power the driver board (battery through the stop button): **the TMC2209s only answer over UART when their motor
   power (VM) is on.**
4. PlatformIO: Upload, then Monitor (115200). Type `help`.

## Commands
| Command | Does |
|---|---|
| `status` | each driver: answers over UART?, current, microsteps, error flags, position |
| `test` | each motor 1 turn forward and back, one after another |
| `r x 2` / `r w -0.5` | turn a motor 2 turns / half a turn back |
| `m y 1600` | move 1600 microsteps (3200 = 1 turn) |
| `all 1` | all three motors 1 turn at once |
| `speed 3200`, `accel 6400` | max speed (steps/s), acceleration |
| `cur x 700` | RMS current in mA (X/Y 900, wrist 600 by default) |
| `off w` / `on w` | driver output off (motor turns freely by hand) / on |
| `dir x` | reverse a motor's direction |
| `g x 6400`, `zero x` | go to an absolute position / call the present position 0 |
| `stop` | stop everything |
| `json`, `stream 150`, `wd 1500`, `ping`, `echo 0` | for programs: one status line / status every 150 ms / stop the motors if no ping for 1.5 s / keep-alive / no echo |

## If a driver says NO ANSWER
- Drive power off (battery, stop button pressed?) - the most common reason.
- UART address: X = 0, Y = 2, wrist = 3, set by the MS1/MS2 traces on the driver board.
- The UART wire (plug pin 3) and the two 3V3 wire links on the controller board.
- The motor still turns without UART (the driver runs on its default settings), just with the pot's current.

## Next
Homing switches, mm instead of steps (80 steps/mm on GT2 20T at 16 microsteps), servo lift, magnet, distance sensor,
stop / start / LEDs, and the command protocol for the laptop program.
