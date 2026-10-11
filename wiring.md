# ETZ plotter v2: wiring map

The harness names match the cable tubes in the model (`Cables_and_chains` in the FreeCAD tree).
Pin numbers are Raspberry Pi Pico 2 GPIO (GP) numbers. Check everything marked CHECK against the
full rules text before soldering.

## 1. Power

```
4S LiPo 2200 (XT60) --+-- 5 A blade fuse --+-- E-stop NC contact 1 --- DRIVE BUS 14.8 V (12.8..16.8 V)
                      |                    |                              |-- TMC2209 x4 VM (100 uF / 25 V at each)
                      |                    |                              |-- Pololu D36V28F6 -> 6 V servo rail
                      |                    |                              |-- green LED + 1.5 k to GND ("drives powered")
                      |                    |                              '-- 100 k / 22 k divider -> GP20 (stop sense)
                      |                    '-- Pololu D36V28F5 -> 5 V LOGIC (not switched by the stop)
                      |                                 |-- 1N5819 -> Pico VSYS (USB from the laptop also feeds VSYS)
                      |                                 |-- connector C, V pin (5 V, >= 200 mA)
                      |                                 '-- E-stop NC contact 2 -> magnet 5 V (switched by the stop)
                      '-- 100 k / 15 k divider -> GP27 (battery voltage, stop below 14.0 V)
```

- The stop button needs **two NC contact blocks** (XB2 / LAY37 bodies take stacked blocks). Block 1 cuts the drive bus
  (steppers and servo). Block 2 cuts the magnet's 5 V. The Pico, the sensors and connector C stay powered, so the program can
  see the stop (GP20) and report it.
- The green LED hangs directly on the drive bus, so it shows the real state of drive power, not what the program thinks.
- All grounds join at one point on the board: battery minus, both regulators, the drivers, the Pico GND.
- TMC2209 logic (VIO) comes from the Pico 3V3 pin.

## 2. Pico 2 pins

| GP | Function | Notes |
|---|---|---|
| 0 / 1 | UART0 TX / RX -> connector C | through a BSS138 2-channel level shifter (3.3 V <-> 5 V); 9600 8-N-1 |
| 4 / 5 | UART1 TX / RX -> TMC2209 PDN_UART bus | 1 k from TX to the bus, RX direct; driver addresses 0..3 set with MS1/MS2 |
| 6 / 7 | X STEP / DIR | |
| 8 / 9 | Y STEP / DIR | |
| 10 / 11 | Wrist STEP / DIR | NEMA11 |
| 2 / 3 | Spare driver STEP / DIR | 4th TMC2209, fitted as a spare |
| 12 | EN, all drivers (low = on) | 10 k pull-up to 3V3, so the drivers stay off while the Pico boots |
| 13 | Servo PWM (DS3218) | 1 k in series; servo powered from the 6 V rail |
| 14 | Magnet MOSFET gate (AO3400) | 100 R in series, 100 k gate to GND; 1N5819 across the magnet |
| 15 | Wrist home (DRV5023 OUT) | open drain: 10 k pull-up to 3V3; sensor powered from 3V3 |
| 16 | X home switch | to GND, internal pull-up; wire the NC contact so a broken wire reads as "pressed" |
| 17 | Y home switch | same as X |
| 18 | Start button | to GND, internal pull-up, debounce in software |
| 19 | Red LED ("program running") | 220 R to the LED |
| 20 | Stop sense | high = drive bus on (divider 100 k / 22 k) |
| 21 | Connector B, SIG | 10 k / 20 k divider: a 5 V signal reads as 3.3 V (5 V tolerant) |
| 26 | Connector A, SIG (ADC0) | 0..3.3 V; 1 k series + 10 nF to GND |
| 27 | Battery voltage (ADC1) | |
| 28 | Spare ADC | |
| USB | Laptop (wired, offline) | also powers the Pico while you develop |

Connector pins on the panel (2.54 mm female headers):
- **A** (1x3): SIG -> GP26, V = 3.3 V, GND. CHECK: the full text may ask for 5 V on V.
- **B** (1x3): SIG -> GP21 (divider), V = 5 V, GND. CHECK the V voltage in the full text.
- **C** (1x4): TX, RX (5 V side of the level shifter), V = 5 V logic rail (2.6 A regulator, so >= 200 mA is easy), GND.

## 3. Harnesses (model names)

| Harness | From -> to | Conductors | Wire |
|---|---|---|---|
| `cable_wrist_bundle` | wrist devices -> up the chain post -> X chain | servo 3, NEMA11 4, magnet 2, hall 3 = 12, plus the camera's USB cable | 0.14-0.25 mm2 (AWG26-24) silicone; servo leads as supplied |
| inside `cable_chain_x` | X chain, moving end -> fixed end | same 12 + USB | |
| `cable_ycar_bundle` | X chain fixed end -> down the post (-y face) -> Y chain moving end | same 12 + USB | zip ties at the post and the carriage slots |
| `cable_x_motor` | X motor -> Y chain moving end | 4 | AWG24, 4-core |
| `cable_x_home` | X home switch -> joins the X motor cable | 2 | AWG26 |
| inside `cable_chain_y` | Y chain, moving end -> fixed end | 18 + USB | |
| `cable_y_chain_to_board` | Y chain fixed end -> electronics board | 18 | |
| `cable_y_motor` | Y motor -> corridor at x 189 -> under the beam at y 205 -> board | 4 | AWG24 |
| `cable_battery` | battery XT60 -> corridor at x 184 -> control panel (fuse, stop) | 2 | AWG16 |
| `cable_panel_to_board` | panel -> under the beam at y 60 -> board: drive bus 2 (AWG18), magnet 5 V via stop block 2 (2), green LED from the bus (in the panel), red LED 2, start 2, stop sense via drive bus, connectors A 3, B 3, C 4 | about 18 | AWG18 for power, AWG26 for signals |
| `cable_y_home` | Y home switch -> board | 2 | AWG26 |

Inside the wrist module (not drawn): servo, NEMA11, magnet and hall cables run along the top arm with two zip ties and
leave a 60 mm slack loop at the carriage, so the arms can swing 5 to 40 mm without pulling the cables. The camera USB cable
follows the same path and goes straight to the laptop (it does not go to the Pico).

Connectors at the board: JST-XH 4-pin for each stepper, 3-pin Dupont for the servo, JST-XH 2-pin for the magnet and
switches, JST-XH 3-pin for the hall sensor, XT60 on the power input. Unplugging the wrist module is then one plug row.

## 4. Driver settings (UART)

| Driver | Motor | RMS current | Microsteps | Mode |
|---|---|---|---|---|
| 0 | X 17HS16-2004S1 | 0.9 A | 16 | StealthChop |
| 1 | Y 17HS16-2004S1 | 0.9 A | 16 | StealthChop |
| 2 | Wrist 11HS12-0674S | 0.45 A | 16 | StealthChop |
| 3 | spare | off | | |

At 16 microsteps a GT2 20T pulley gives 80 steps per mm; 100 mm/s is 8 kHz step rate, easy for the Pico's PIO.
The currents are about half the rated values: the load is tiny and the motors stay cool on the battery.
