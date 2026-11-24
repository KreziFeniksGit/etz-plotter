# ETZ plotter firmware (PlatformIO, ESP32-S3-DevKitC-1 N16R8)

Current program: **v5** - the three steppers (X, Y, wrist) through the TMC2209 drivers, plus homing, mm / degree
units with soft limits, the servo lift, the magnet, the red LED and start button, a battery guard and a move queue,
controlled by text commands from the serial monitor **or the laptop dashboard** (`laptop/esp_dashboard.py`). Pins: `include/pins.h` (= `wiring.md` section 2;
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
| `lib/SlewServo` | lift servo: LEDC 50 Hz, 14 bit; the pulse walks to the target at a speed limit (us per second); "done" = the pulse arrives |
| `lib/Magnet` | magnet: LEDC 20 kHz, peak-and-hold (100 % for 150 ms, then hold %), on-time guard |
| `lib/MoveQueue` | fixed list of 128 command lines (48 characters each) |
| `lib/Inputs` | `Debounce` (a button must stay at a level for 30 ms) and `Ema` (moving average of about the last n readings) |

History: v1 used AccelStepper + TMCStepper (worked), v2 FastAccelStepper (motors moved randomly on Egor's board),
v3 (24 Oct) replaced all of them with our own code, v4 (25 Oct) added the protection, profiles, S-curve and lines,
v5 (29 Oct) homing, mm, servo, magnet, wrist angle, LED / start, battery guard, move queue - **compiled only, not run
on the machine yet** (it is not assembled). The laptop digital twin (`laptop/twin.py`) speaks the same commands.

**Settings saved by v4 are not loaded by v5** (the settings block grew): after uploading v5 the board starts on the
defaults; set the motor values again (or `tune`) and `save`.

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
| **Long commands** | `selftest`, `tune`, `test`, `home` still answer `ping` and `json`, and `stop` aborts them; other commands get `err busy (...)` |
| **Battery guard** | battery voltage read every 100 ms, averaged over about 8 readings. Below 14.8 V `event battery low (14.75 V)`, below 14.0 V `event battery stop (13.98 V)`: motors stop, queue stopped, every move refused with `err battery` until the average is back above 15.1 V (`event battery ok (...)`). Below 5 V = no battery (bench on USB): guard off. Thresholds: `set batlow`, `set batstop` (0 = off) |
| **Magnet guard** | the magnet switches itself off after 30 s on (`event magnet timeout`); `set magmax` |
| **Soft limits** | after `home`, X and Y moves outside their limits (default X 0..165, Y 0..336 mm, VERIFY; 143 before model v2.17: a board with saved settings keeps its old `xmax`, so `set xmax 165` + `save`) are refused with `err limit x`, for every move command (steps or mm). Before homing all moves are allowed and json shows `homed:0`. A crash, `off` or `zero` clears `homed` |

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
| `stop` | stop everything (decelerate); aborts a long command; empties the queue (`event q stopped`). Does not touch the servo or the magnet (it would drop a carried checker) |
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

### v5: machine commands (mm, homing, lift, magnet, queue)
| Command | Reply / events | Does |
|---|---|---|
| `home x`, `home y`, `home all` | `ok home x` / `err home x timeout` / `err home x stopped` / `err home x switch stays pressed (broken wire?)` | (all = X then Y) fast search towards the switch (25 mm/s), off it, 3 mm further, slow touch (2 mm/s), position = home offset (default 0 mm). The fast search stops at once on the switch (no deceleration, so it does not overrun the switch). Timeout 25 s per axis. Answers when finished. Clears `lost`, sets `homed`. **Raise the lift first** (the firmware does not) |
| `gomm x 100`, `gomm w 90` | `ok gomm x` / `err limit x` | absolute position in mm (wrist: degrees, no shorter-way logic) |
| `linemm 100 200` | `ok linemm` / `err limit y` | straight XY line to (100, 200) mm, both axes arrive together |
| `wrist 90`, `wrist -45` | `ok wrist 90` | absolute wrist angle, 0 = the hand-set mark (`zero w` at the mark). Shorter way round, **unless** that would take it more than 360 deg from the mark (the magnet leads are a loose coil, wiring.md): then the other way. `set wristturn` |
| `servo 1500`, `servo off` | `ok servo 1500`, later `event servo done` | lift servo pulse, clamped to 500..2500 (`set servomin` / `servomax`). The pulse moves at 1500 us/s (`set servoslew`); `event servo done` when it arrives (an estimate: the servo gives no feedback). Before the first `servo` no pulse is sent (servo limp, json `servo:0`); the first one is a jump, "done" after 0.2-0.5 s. `servo off` = no pulses |
| `mag on`, `mag off` | `ok mag on`, `event magnet timeout` | 100 % for 150 ms (pulls the checker across the gap), then 40 % to hold (`set magkick`, `set maghold`); off by itself after 30 s. **No reverse release pulse is possible**: one low-side MOSFET can only switch the current off, not reverse it; the SS34 diode lets the field die in a few ms. If a checker sticks (the steel washer keeps a little magnetism), that needs an H-bridge - not on this board |
| `led red 1`, `led red 0` | `ok led red 1` | red "program running" LED (GPIO21) |
| (start button) | `event start` | GPIO47, pressed = LOW, must stay pressed 30 ms. Held at power-on: no event until let go and pressed again |
| `q linemm 100 200`, `q servo 1200`, `q mag on`, `q wait 300` | `ok q 4` (new length) / `err q full (128)` | add a line to the queue. Allowed: g m r line gomm linemm wrist servo mag led home wait |
| `qrun` | `ok qrun 4`, at the end `event q done 4` | run the queue: the next line starts only when the motors, the servo move and any wait have finished (the magnet's 150 ms kick is not waited for: add `q wait`). Lines can be added while it runs. A line that answers `err ...` stops it |
| `qclear`, `qstat` | `ok qclear`, `ok qstat 3 running` | empty it (and stop) / length + `running` or `idle` |
| (stop, crash, watchdog, motor too hot, battery stop, an `err` line) | `event q stopped` | the queue is emptied |
| `set`, `set xspm 80` | `ok set xspm 80` | the v5 settings by name: `xspm` `yspm` (steps/mm, 80 = GT2 20T at 16 microsteps), `wspd` (wrist steps/deg, 8.889), `xmin xmax ymin ymax` (soft limits), `xhome yhome` (position at the switch), `xhomedir yhomedir` (-1 / 1), `homefast homeslow homeback hometime`, `servomin servomax servoslew`, `maghold magkick magmax`, `batlow batstop`, `wristturn`. `save` keeps them. Changing steps/mm clears `homed` |

json has, besides the v4 fields: `vbatavg` (averaged battery V), `bat` (0 ok, 1 low, 2 stop), `servo` (present pulse us,
0 = off), `mag` (0/1), `led` (0/1), `qlen`, `qrun` (0/1), and per axis `homed` (0/1; the wrist is never homed).

## If a driver says NO ANSWER
- Drive power off (battery, stop button pressed?) - the most common reason.
- UART address: X = 0, Y = 2, wrist = 3, set by the MS1/MS2 traces on the driver board.
- The UART wire (plug pin 3) and the two 3V3 wire links on the controller board.
- `reg x` shows the raw bytes on the UART wire: 4 = only our echo (driver silent), 12 = echo + answer, 0 = wire problem.

## Not tested yet / VERIFY once built
- Which end each home switch is at and where it triggers (`xhomedir`, `xhome`; limits X 0..143, Y 0..336 are the
  modelled travel). Run the first `home x` with a hand on the stop button.
- Magnet hold 40 %: the pull falls faster than the current, so test that 40 % holds a checker through the fastest
  moves (and with the 5 V rail sagging); raise `maghold` if it drops one.
- Servo slew 1500 us/s must be slower than the real MG996R under load, or `event servo done` comes too early.
- Battery thresholds rely on the 100 k / 15 k divider and the ESP32 ADC (about +-2 %): compare `vbatavg` with a multimeter.

## Next
Distance sensor, connectors A / B / C. Ideas list: `docs/ideas.md`.
