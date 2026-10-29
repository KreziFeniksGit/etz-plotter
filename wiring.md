# ETZ plotter v2: wiring map

Regulators (Egor, 22 Oct): two **Mini560 Pro 5 V** modules (there is no 6 V version; the 9 V one would burn the MG996R).
The full PCB parts list is `pcb/bom.md`. The control board, panel, breadboard and battery are placed on the plywood by hand
(not in the model); the harness routes in the model end where they used to be.

The harness names match the cable tubes in the model (`Cables_and_chains` in the FreeCAD tree).
Pin numbers are ESP32-S3 GPIO numbers on an ESP32-S3-DevKitC-1 N16R8 board. Check everything marked CHECK against the
full rules text before soldering.

**Rule: Wi-Fi and Bluetooth must be off on every controller.** The ESP32-S3 has a radio, so the firmware must never start
it (do not call `esp_wifi_init` / start BLE; build with Bluetooth disabled). Be ready to show the judges the code.

## 1. Power

```
4S LiPo 2200 (XT60) --+-- 5 A blade fuse --+-- E-stop NC contact 1 --- DRIVE BUS 14.8 V (12.8..16.8 V)
                      |                    |                              |-- TMC2209 x4 VM (100 uF / 25 V at each)
                      |                    |                              |-- Mini560 Pro 5 V #2 -> 5 V servo rail (470 uF + 100 nF)
                      |                    |                              |-- green LED + 1.5 k to GND ("drives powered")
                      |                    |                              '-- 100 k / 22 k divider -> GPIO42 (stop sense)
                      |                    '-- Mini560 Pro 5 V #1 -> 5 V LOGIC (not switched by the stop)
                      |                                 |-- 1N5819 -> board 5V pin (CHECK: do not also feed it from USB
                      |                                 |   without the diode; the diode stops back-feeding the laptop)
                      |                                 |-- connector C, V pin (5 V, >= 200 mA)
                      |                                 '-- E-stop NC contact 2 -> magnet 5 V (switched by the stop)
                      '-- 100 k / 15 k divider -> GPIO2 (battery voltage, stop below 14.0 V)
```

- The stop button needs **two NC contact blocks** (XB2 / LAY37 bodies take stacked blocks). Block 1 cuts the drive bus
  (steppers and servo). Block 2 cuts the magnet's 5 V. The ESP32, the sensors and connector C stay powered, so the program
  can see the stop (GPIO42) and report it.
- The green LED hangs directly on the drive bus, so it shows the real state of drive power, not what the program thinks.
- All grounds join at one point on the board: battery minus, both regulators, the drivers, the ESP32 GND.
- TMC2209 logic (VIO) comes from the board's 3V3 pin.

## 2. ESP32-S3 pins (split boards, 23 Oct - chosen so the single-sided controller board has no crossings)

Not used on purpose: GPIO 0, 3, 45, 46 (boot strapping), 19 / 20 (native USB), 26..32 (flash) and 33..37 (the N16R8's
octal PSRAM), 43 / 44 (UART0, wired to the board's USB-UART port = the laptop link). GPIO 4, 13, 14 are free.
GPIO 38 and 48: one of them drives the board's RGB LED (48 on v1.0, 38 on v1.1); both are used here as INPUTS only
(home switch, start), which cannot harm the LED. Never configure them as outputs.

| GPIO | Function | Notes |
|---|---|---|
| 5 | TMC2209 UART bus, RX | UART2 RX, direct on the single-wire PDN_UART bus to all three drivers |
| 6 | TMC2209 UART bus, TX | UART2 TX through R8 1 k onto the same bus; addresses by MS1/MS2: X 0, Y 2, wrist 3 |
| 7 / 15 | X STEP / DIR (board J1) | **as built the J1 and J3 cables are crossed: J1 drives the wrist driver, so the firmware uses 7 / 15 for the wrist and 18 / 8 for X** (`firmware/include/pins.h`). Step pulses from a timer interrupt (`firmware/lib/StepGen`) |
| 16 / 17 | Y STEP / DIR | |
| 18 / 8 | Wrist STEP / DIR (board J3) | wrist NEMA17 pancake 17HS4023S; used for X as built (see the 7 / 15 row) |
| - | Driver EN | tied to GND on the controller board: drivers always enabled. The firmware turns a driver off over UART (TOFF = 0); the stop button cuts their power |
| 9 | Connector A, SIG (ADC1_CH8) | 0..5 V sensor -> 10 k / 20 k divider -> 0..3.3 V; 10 nF to GND |
| 10 | Connector B, SIG | 10 k / 20 k divider: a 5 V signal reads as 3.3 V |
| 11 / 12 | UART1 TX / RX -> connector C | TX through 1 k; RX through a 10 k / 20 k divider (5 V -> 3.3 V); 9600 8-N-1 |
| 1 | Magnet MOSFET gate (on the power board) | 100 R in series, 100 k gate to GND there; 100N03A (UMW, TO-252, logic level); SS34 across the magnet. Firmware v5: LEDC PWM 20 kHz, 100 % for 150 ms then 40 % hold, off after 30 s on (`mag on/off`). Low-side switch only: no reverse release pulse possible |
| 2 | Battery voltage (ADC1_CH1) | divider 100 k / 15 k on the power board. Firmware v5: read every 100 ms, averaged over ~8; `event battery low` below 14.8 V, `event battery stop` + moves refused below 14.0 V; under 5 V = no battery (USB bench), guard off |
| 42 | Stop sense | high = drive bus on (divider 100 k / 22 k on the power board) |
| 41 | Servo PWM (MG996R) | LEDC, 50 Hz (14 bit); 1 k in series on the power board; servo on its own 5 V rail. Firmware v5: `servo <us>` 500..2500, slew 1500 us/s; no pulse until the first command |
| 40 / 39 | I2C SDA / SCL -> distance sensor (TOF400C) | 4.7 k pull-ups to 3V3 at the plug; XSHUT tied to 3V3 (sensor always on) |
| 38 | X home switch (input only) | to GND, internal pull-up; wire the NC contact so a broken wire reads as "pressed". Firmware: HIGH = pressed or broken wire; `home x` searches towards it (default the X 0 end, VERIFY) |
| 48 | Y home switch (input only) | same as X |
| 47 | Start button | to GND, internal pull-up; pressed = LOW, 30 ms debounce in the firmware -> `event start` |
| 21 | Red LED ("program running") | 220 R to the LED; output, `led red 0/1` |
| USB (UART port) | Laptop (wired, offline) | also powers the board while you develop |

Board-to-board cables (straight 1:1 JST-XH, pin 1 to pin 1), see `pcb/split_boards.md`:
- controller J1 / J2 / J3 -> driver board J1 / J2 / J3 (X, Y, wrist): 1 GND, 2 EN (GND), 3 UART, 4 STEP, 5 DIR, 6 3V3
- controller J4 -> power board J5: 1 MAG_IO, 2 GND, 3 +5V, 4 VBAT_SENSE, 5 STOP_SENSE, 6 SERVO_IO
- power board J3 (XT30) -> driver board J7 (XT30): VDRIVE

Connector pins on the panel (2.54 mm female headers on a small strip board, Egor 22 Oct):
- One 6-wire cable from the controller board (JST-XH 6, J5): 1 A_SIG, 2 B_SIG, 3 C_TX, 4 C_RX, 5 +5 V (through the 0.5 A PTC), 6 GND.
  On the strip, pin 5 feeds all three V pins and pin 6 all three GND pins. All dividers / resistors stay on the controller board.
- **A** (1x3): SIG -> 10 k / 20 k -> GPIO9, V = 5 V, GND. CHECK the V voltage in the full rules text.
- **B** (1x3): SIG -> 10 k / 20 k -> GPIO10, V = 5 V, GND.
- **C** (1x4): TX (1 k from GPIO11), RX (divider to GPIO12), V = 5 V through the 0.5 A PTC fuse (>= 200 mA is easy), GND.

## 3. Harnesses (model names)

| Harness | From -> to | Conductors | Wire |
|---|---|---|---|
| `cable_wrist_bundle` | wrist devices -> up the chain post -> X chain | servo 3, wrist stepper 4, magnet 2, distance sensor 5 (3V3, GND, SDA, SCL, XSHUT) = 14, plus the camera's USB cable | 0.14-0.25 mm2 (AWG26-24) silicone; servo leads as supplied |
| inside `cable_chain_x` | X chain, moving end -> fixed end | same 9 + USB | |
| `cable_ycar_bundle` | X chain fixed end -> down the post (-y face) -> Y chain moving end | same 9 + USB | zip ties round the post and through the carriage |
| `cable_x_motor` | X motor -> Y chain moving end | 4 | AWG24, 4-core |
| `cable_x_home` | X home switch -> joins the X motor cable | 2 | AWG26 |
| inside `cable_chain_y` | Y chain, moving end -> fixed end | 15 + USB | |
| `cable_y_chain_to_board` | Y chain fixed end -> electronics board | 15 | |
| `cable_y_motor` | Y motor -> corridor at x 189 -> under the beam at y 205 -> board | 4 | AWG24 |
| `cable_battery` | battery XT60 -> corridor at x 184 -> control panel (fuse, stop) | 2 | AWG16 |
| `cable_panel_to_board` | panel -> under the beam at y 60 -> board: drive bus 2 (AWG18), magnet 5 V via stop block 2 (2), green LED from the bus (in the panel), red LED 2, start 2, stop sense via drive bus, connectors A 3, B 3, C 4 | about 18 | AWG18 for power, AWG26 for signals |
| `cable_y_home` | Y home switch -> board | 2 | AWG26 |

Inside the wrist module (drawn, rebuilt for every lift pose):

| Harness | From -> to | Ties |
|---|---|---|
| `cable_wrist_camera` | camera board -> up through the shelf hole -> tied on the shelf -> up beside the stepper's +x side -> over the motor top -> junction J beside the end plate | 1 on the shelf (`wm_zip_camera`) |
| `cable_wrist_stepper` | NEMA17 pancake: plug-in 4-wire cable in its 6-pin JST-PH socket, socket turned to +x (VERIFY which side yours has) -> up and over the motor top -> J | - |
| `cable_wrist_harness` | J -> up the end plate's +y face between the pivot nuts -> over its top edge -> along the top arm's upper edge -> off the arm beyond the carriage plate -> under the X block -> `cable_wrist_bundle` | end plate (`wm_zip_end_plate`), 2 round the top arm's upper web through its lightening slot (`wm_zip_arm_1/2`) |
| `cable_wrist_servo` | servo (far end of the case; VERIFY lead exit) -> up beside the case -> under the carriage plate -> bundle | 1 through the carriage plate (`wm_zip_servo`) |

The harness rides on the arm, so between the end plate and the arm, and between the arm and the carriage, it only flexes a
little when the arms swing (5 to 40 mm); every lift pose is checked for clashes. The magnet leads are not drawn: they turn
with the wrist, so leave them a loose 2-turn coil from the magnet to J, and keep the wrist within one turn either way
of its start angle in the firmware. There is no wrist home sensor (dropped 12 Oct): set the wrist to its mark by hand
before power-up; the firmware counts the angle from there and returns to it at the end of each run. The camera USB cable follows the harness and goes straight to the laptop (not to the ESP32).

Other ties (drawn): two round the 2020 post and the bundle on its -y face (`zip_tie_post_1/2`), one through the Y carriage
(`zip_tie_ycar`), two through the chain post (`wm_zip_chain_post_1/2`). Every tie slot pair sits on either side of its cable,
so the tie goes down one slot, under the plate, up the other and round the cable.

Connectors at the board: JST-XH 4-pin for each stepper, 3-pin Dupont for the servo, JST-XH 2-pin for the magnet and
switches, XT60 on the power input. Unplugging the wrist module is then one plug row.

## 4. Driver settings (UART)

| Driver | Motor | RMS current | Microsteps | Mode |
|---|---|---|---|---|
| 0 | X 17HS16-2004S1 | 0.9 A | 16 | StealthChop |
| 1 | Y 17HS16-2004S1 | 0.9 A | 16 | StealthChop |
| 2 | Wrist 17HS4023S (NEMA17 pancake, rated 0.7 A) | 0.6 A | 16 | StealthChop |
| 3 | spare | off | | |

At 16 microsteps a GT2 20T pulley gives 80 steps per mm; 100 mm/s is 8 kHz step rate, easy for the ESP32-S3's RMT / MCPWM step generation.
The X/Y currents are about half the rated values: the load is tiny and the motors stay cool on the battery. The wrist pancake runs at 0.6 A (rated 0.7): it is a small motor, so it needs most of its current for its ~13 N cm.


## Distance sensor (TOF400C, VL53L1X), added 16 Oct
- Under the wrist shelf, component side down; 5 wires soldered to its pads (no header): VIN 3V3, GND, SDA GPIO40, SCL GPIO39, XSHUT tied to 3V3 on the controller board.
  They go up through the hole beside the board and join the wrist harness; twist SDA/SCL with GND (about 1 m).
- Read it with the magnet up (h 40): about 74 mm to the field, 49 mm to the top of a 5-stack (the VL53L1X needs >= 40 mm).
- Firmware: short distance mode, 50..100 ms timing budget, a small ROI (e.g. 4 x 4 SPADs) so only the stack under it is seen. Levels = round((field - reading) / 5 mm).
