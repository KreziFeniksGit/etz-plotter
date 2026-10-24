# ETZ plotter firmware (PlatformIO, ESP32-S3-DevKitC-1 N16R8)

Current program: **v4** - the three steppers (X, Y, wrist) through the TMC2209 drivers, controlled by text commands
from the serial monitor **or the laptop dashboard** (`laptop/esp_dashboard.py`). Pins: `include/pins.h` (= `wiring.md` section 2;
X and wrist STEP/DIR are swapped there to match Egor's crossed J1/J3 cables). Wi-Fi and Bluetooth are never started.

**No outside libraries** - only the Arduino core and our own code in `lib/`:
| Library | Does |
|---|---|
| `lib/Tmc2209` | TMC2209 single-wire UART: datagrams with CRC8, our own echo skipped, register write/read; setup (GCONF, current and standing current in IHOLD_IRUN, microsteps and on/off in CHOPCONF, TCOOLTHRS for the load reading), status (DRV_STATUS) and load (SG_RESULT) |
| `lib/StepGen` | step pulses from a 40 kHz hardware-timer interrupt (integer maths only), up to 16000 steps/s per motor. Trapezoid or **S-curve** (the acceleration itself ramps over "jerk" ms; exact jerk-limited stopping distance), and `moveWith` for **coordinated XY lines** (both axes get the same profile shape, start in the same tick, arrive together). Loop code can never disturb the motion |
| `lib/Console` | line editor (echo, Backspace, arrow keys ignored) and splitting a line into words |
| `lib/Settings` | named blocks in flash (ESP-IDF NVS calls): settings profiles, the crash copy of the black box |
| `lib/BlackBox` | last 64 events in RTC memory: survive a crash / watchdog / brownout restart; copied to flash after one |
| `lib/Guard` | `HeatModel` (motor temperature estimate from the current) and `CrashDetector` (sudden load drop = hit something) |

History: v1 used AccelStepper + TMCStepper (worked), v2 FastAccelStepper (motors moved randomly on Egor's board),
v3 (24 Oct) replaced all of them with our own code, v4 (25 Oct) added the protection, profiles, S-curve and lines.

## Run it
1. VS Code -> PlatformIO -> Open Project -> this `firmware` folder.
2. Plug the USB cable into the port marked **UART** on the ESP32 board (not "USB").
3. Power the driver board (battery through the stop button): **the TMC2209s only answer over UART when their motor
   power (VM) is on.** If the battery comes on later, the firmware sets each driver up by itself when it starts answering.
4. PlatformIO: Upload, then Monitor (115200). Type `help`.

## Protection that always runs
| What | How |
|---|---|
| **Heat guard** | each motor's temperature is estimated from its current (steady rise = 80 K x (I / I_rated)^2, time constant tau). At 70 C the standing current drops to 20 %; at 90 C the motor stops and its driver goes off until it is below 65 C. `cur` cannot go above the motor's rated current. The model's numbers (80 K, tau) are typical values: VERIFY with a finger / thermometer after a long run |
| **Crash detection** | while a motor moves, its load reading (StallGuard) is read every 5 ms. A sudden drop below 30 % of the normal value (2 readings in a row) = it hit something: all motors stop at once, the event goes to the black box and the axis is marked "position not trusted" until `zero` / homing. `crash x 0` turns it off for a motor |
| **Idle off** | a driver that has not moved for 60 s turns off; the next move turns it back on |
| **Laptop watchdog** | with `wd <ms>` set, the motors stop if no command / ping arrives in time |
| **Long commands** | `selftest`, `tune`, `test` still answer `ping` and `json`, and `stop` aborts them |

## Commands
| Command | Does |
|---|---|
| `status` | each driver: answers over UART?, current, flags, position, settings, motor temperature |
| `test` | each motor 1 turn forward and back, one after another |
| `r x 2` / `r w -0.5` | turn a motor 2 turns / half a turn back |
| `m y 1600` | move 1600 microsteps (3200 = 1 turn) |
| `g x 6400`, `zero x` | go to an absolute position / call the present position 0 (position trusted again) |
| `line 8000 3000` | X and Y together in a straight line to these absolute steps; they arrive at the same moment |
| `all 1` | all three motors 1 turn at once |
| `stop` | stop everything (decelerate); aborts a long command |
| `speed 3200`, `accel 6400` | max speed (steps/s, up to 16000), acceleration, all motors |
| `speed x 1600`, `accel w 3200` | the same for one motor only (each motor keeps its own) |
| `jerk 40`, `jerk x 40` | S-curve: the acceleration builds up over 40 ms (0 = trapezoid). Gentler on a carried stack |
| `cur x 700`, `hold x 30` | moving current in mA (max = the motor's rating) / standing current in % of it |
| `crash`, `crash x 25` | show / set the crash threshold (% of the normal load; 0 = off) |
| `heat`, `heat w 700 600`, `heat limits 70 90` | estimated motor temperatures / rated mA and tau of a motor / warn and off temperatures |
| `idle 60` | driver off after 60 s standing (0 = never) |
| `off w` / `on w` | driver output off (motor turns freely by hand; position then not trusted) / on |
| `dir x` | reverse a motor's direction (only while it stands) |
| `save`, `save fast` | keep all settings in flash: no name = `boot` (loaded at every power-on), or a named profile |
| `load fast`, `profiles`, `forget fast`, `defaults` | switch profile / list them / delete one / back to the built-in values |
| `selftest` | drive power, battery, RAM, chip temperature, last restart, and per driver: answers, settings arrived, STEP/DIR arrive (`pins`), steps counted (16 steps there and back, read from the driver's MSCNT), shorts, overheating, motor temperature; home switches. Ends with `ok selftest PASS` or `err selftest FAIL n`. The dashboard adds the camera |
| `tune x`, `tune x 2000` | auto-tune: back and forth over 3200 (or 2000) steps, faster each time (+1600 steps/s) until the load reading shows slipping, then the acceleration the same way; uses 70 % of the last good values. **The axis needs that much free room.** `save` keeps the result |
| `log`, `log crash`, `log clear` | black box: last 64 events and commands (boot number, time) / the copy made after the last crash or brownout (survives power-off) |
| `mem` | ESP32 RAM (free / lowest ever / biggest block), PSRAM, loop stack left, chip temperature, uptime, loop passes per second, boot number, why it last restarted |
| `pulse x 3200 [us]`, `reg x`, `pins x` | low-level checks: plain pulses without the timer / driver registers + raw UART bytes / does the driver see our STEP and DIR pins |
| `json`, `stream 250`, `wd 1500`, `ping`, `echo 0` | for programs: one status line / status every 250 ms / stop the motors if no ping for 1.5 s / keep-alive / no echo |

## If a driver says NO ANSWER
- Drive power off (battery, stop button pressed?) - the most common reason.
- UART address: X = 0, Y = 2, wrist = 3, set by the MS1/MS2 traces on the driver board.
- The UART wire (plug pin 3) and the two 3V3 wire links on the controller board.
- `reg x` shows the raw bytes on the UART wire: 4 = only our echo (driver silent), 12 = echo + answer, 0 = wire problem.

## Next
Homing switches, mm instead of steps (80 steps/mm on GT2 20T at 16 microsteps), servo lift, magnet, distance sensor,
stop / start / LEDs. Ideas list: `docs/ideas.md`.
