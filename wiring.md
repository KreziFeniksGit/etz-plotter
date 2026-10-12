# ETZ plotter v2: wiring map

The harness names match the cable tubes in the model (`Cables_and_chains` in the FreeCAD tree).
Pin numbers are ESP32-S3 GPIO numbers on an ESP32-S3-DevKitC-1 N16R8 board. Check everything marked CHECK against the
full rules text before soldering.

**Rule: Wi-Fi and Bluetooth must be off on every controller.** The ESP32-S3 has a radio, so the firmware must never start
it (do not call `esp_wifi_init` / start BLE; build with Bluetooth disabled). Be ready to show the judges the code.

## 1. Power

```
4S LiPo 2200 (XT60) --+-- 5 A blade fuse --+-- E-stop NC contact 1 --- DRIVE BUS 14.8 V (12.8..16.8 V)
                      |                    |                              |-- TMC2209 x4 VM (100 uF / 25 V at each)
                      |                    |                              |-- Pololu D36V28F6 -> 6 V servo rail
                      |                    |                              |-- green LED + 1.5 k to GND ("drives powered")
                      |                    |                              '-- 100 k / 22 k divider -> GPIO47 (stop sense)
                      |                    '-- Pololu D36V28F5 -> 5 V LOGIC (not switched by the stop)
                      |                                 |-- 1N5819 -> board 5V pin (CHECK: do not also feed it from USB
                      |                                 |   without the diode; the diode stops back-feeding the laptop)
                      |                                 |-- connector C, V pin (5 V, >= 200 mA)
                      |                                 '-- E-stop NC contact 2 -> magnet 5 V (switched by the stop)
                      '-- 100 k / 15 k divider -> GPIO2 (battery voltage, stop below 14.0 V)
```

- The stop button needs **two NC contact blocks** (XB2 / LAY37 bodies take stacked blocks). Block 1 cuts the drive bus
  (steppers and servo). Block 2 cuts the magnet's 5 V. The ESP32, the sensors and connector C stay powered, so the program
  can see the stop (GPIO47) and report it.
- The green LED hangs directly on the drive bus, so it shows the real state of drive power, not what the program thinks.
- All grounds join at one point on the board: battery minus, both regulators, the drivers, the ESP32 GND.
- TMC2209 logic (VIO) comes from the board's 3V3 pin.

## 2. ESP32-S3 pins

Not used on purpose: GPIO 0, 3, 45, 46 (boot strapping), 19 / 20 (native USB), 26..32 (flash) and 33..37 (the N16R8's
octal PSRAM), 43 / 44 (UART0, wired to the board's USB-UART port = the laptop link), 48 (RGB LED on the board).

| GPIO | Function | Notes |
|---|---|---|
| 17 / 18 | UART1 TX / RX -> connector C | through a BSS138 2-channel level shifter (3.3 V <-> 5 V); 9600 8-N-1 |
| 15 / 16 | UART2 TX / RX -> TMC2209 PDN_UART bus | 1 k from TX to the bus, RX direct; driver addresses 0..3 set with MS1/MS2 |
| 4 / 5 | X STEP / DIR | step pulses from the RMT or MCPWM peripheral |
| 6 / 7 | Y STEP / DIR | |
| 8 / 9 | Wrist STEP / DIR | NEMA11 |
| 11 / 12 | Spare driver STEP / DIR | 4th TMC2209, fitted as a spare |
| 13 | EN, all drivers (low = on) | 10 k pull-up to 3V3, so the drivers stay off while the ESP32 boots |
| 14 | Servo PWM (MG996R) | LEDC, 50 Hz; 1 k in series; servo powered from the 6 V rail |
| 21 | Magnet MOSFET gate (AO3400) | 100 R in series, 100 k gate to GND; 1N5819 across the magnet |
| 38 | free (was the wrist hall sensor, dropped 12 Oct) | |
| 39 | X home switch | to GND, internal pull-up; wire the NC contact so a broken wire reads as "pressed" |
| 40 | Y home switch | same as X |
| 41 | Start button | to GND, internal pull-up, debounce in software |
| 42 | Red LED ("program running") | 220 R to the LED |
| 47 | Stop sense | high = drive bus on (divider 100 k / 22 k) |
| 10 | Connector B, SIG | 10 k / 20 k divider: a 5 V signal reads as 3.3 V (the ESP32 is not 5 V tolerant) |
| 1 | Connector A, SIG (ADC1_CH0) | 0..3.3 V; 1 k series + 10 nF to GND |
| 2 | Battery voltage (ADC1_CH1) | ADC1 only (ADC2 shares hardware with the radio) |
| USB (UART port) | Laptop (wired, offline) | also powers the board while you develop |
Connector pins on the panel (2.54 mm female headers):
- **A** (1x3): SIG -> GPIO1, V = 3.3 V, GND. CHECK: the full text may ask for 5 V on V.
- **B** (1x3): SIG -> GPIO10 (divider), V = 5 V, GND. CHECK the V voltage in the full text.
- **C** (1x4): TX, RX (5 V side of the level shifter), V = 5 V logic rail (2.6 A regulator, so >= 200 mA is easy), GND.

## 3. Harnesses (model names)

| Harness | From -> to | Conductors | Wire |
|---|---|---|---|
| `cable_wrist_bundle` | wrist devices -> up the chain post -> X chain | servo 3, NEMA11 4, magnet 2 = 9, plus the camera's USB cable | 0.14-0.25 mm2 (AWG26-24) silicone; servo leads as supplied |
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
| `cable_wrist_camera` | camera board -> up through the shelf hole -> along the shelf's +y edge -> junction J beside the stepper | 1 on the shelf (`wm_zip_camera`) |
| `cable_wrist_stepper` | NEMA11 (+y side; VERIFY where the leads leave the motor) -> J | - |
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
| 2 | Wrist 11HS12-0674S | 0.45 A | 16 | StealthChop |
| 3 | spare | off | | |

At 16 microsteps a GT2 20T pulley gives 80 steps per mm; 100 mm/s is 8 kHz step rate, easy for the ESP32-S3's RMT / MCPWM step generation.
The currents are about half the rated values: the load is tiny and the motors stay cool on the battery.
