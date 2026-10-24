# ETZ plotter firmware (PlatformIO, ESP32-S3-DevKitC-1 N16R8)

Current program: **v3** - the three steppers (X, Y, wrist) through the TMC2209 drivers, controlled by text commands
from the serial monitor **or the laptop dashboard** (`laptop/esp_dashboard.py`). Pins: `include/pins.h` (= `wiring.md` section 2).
Wi-Fi and Bluetooth are never started.

**No outside libraries** - only the Arduino core and our own code in `lib/`:
| Library | Does |
|---|---|
| `lib/Tmc2209` | TMC2209 single-wire UART: datagrams with CRC8, our own echo skipped, register write/read; setup (GCONF, current in IHOLD_IRUN, microsteps and on/off in CHOPCONF), status (DRV_STATUS) and load (SG_RESULT) |
| `lib/StepGen` | step pulses from a 40 kHz hardware-timer interrupt with trapezoid acceleration (integer maths only), up to 16000 steps/s per motor. Loop code (UART reads, printing) can never disturb the motion |
| `lib/Console` | line editor (echo, Backspace, arrow keys ignored) and splitting a line into words |

History: v1 used AccelStepper + TMCStepper (worked), v2 FastAccelStepper (motors moved randomly on Egor's board),
v3 (24 Oct) replaced all of them with our own code.

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
| `speed 3200`, `accel 6400` | max speed (steps/s, up to 16000), acceleration |
| `cur x 700` | RMS current in mA (X/Y 900, wrist 600 by default) |
| `off w` / `on w` | driver output off (motor turns freely by hand) / on |
| `dir x` | reverse a motor's direction (only while it stands) |
| `g x 6400`, `zero x` | go to an absolute position / call the present position 0 |
| `stop` | stop everything |
| `idle 60` | a driver that has not moved for 60 s turns itself off (cool, no hum); the next move turns it back on by itself. `idle 0` = never. Default 60 s. While asleep the motor can be turned by hand, so the position may be lost |
| `json`, `stream 150`, `wd 1500`, `ping`, `echo 0` | for programs: one status line / status every 150 ms / stop the motors if no ping for 1.5 s / keep-alive / no echo |

## If a driver says NO ANSWER
- Drive power off (battery, stop button pressed?) - the most common reason.
- UART address: X = 0, Y = 2, wrist = 3, set by the MS1/MS2 traces on the driver board.
- The UART wire (plug pin 3) and the two 3V3 wire links on the controller board.
- The motor still turns without UART (the driver runs on its default settings), just with the pot's current.

## Next
Homing switches, mm instead of steps (80 steps/mm on GT2 20T at 16 microsteps), servo lift, magnet, distance sensor,
stop / start / LEDs, and the command protocol for the laptop program.
