# Main control PCB: parts list (v1.0, 22 Oct 2026)

Source: `wiring.md` (power tree, ESP32-S3 pin map). One 2-layer board in place of the perfboard (`perfboard_100x80` in the model,
100 x 80 mm on 4 M3 standoffs). Modules plug into female headers, so a burnt module is a 1-minute swap.
Ask the organisers first that a self-designed board with plug-in driver modules counts as "own control electronics" (open item).

## Power tree
```
4S LiPo (XT60) -- F1 5 A blade fuse (inline) --+-- J_BAT (unswitched) --+-- U5 Mini560 Pro 5 V  -> +5V LOGIC
                                               |                        '-- R 100k / 15k -> GPIO2 (battery voltage)
                                               '-- stop block 1 (NC) -- J_DRIVE (switched) --+-- TMC2209 x4 VM (C 100 uF each)
                                                                                             +-- U6 Mini560 Pro 5 V -> +5V SERVO
                                                                                             +-- green LED (1.5 k)
                                                                                             '-- R 100k / 22k -> GPIO47 (stop sense)
+5V LOGIC -- D1 1N5819 -> ESP32 board 5V pin;  -> F2 PTC 0.5 A -> connector C V;  -> stop block 2 (NC) -> magnet 5 V
```

## A. Plug-in modules (on the PCB, on headers)
| Ref | Part | Qty | Footprint on the PCB | Notes |
|---|---|---|---|---|
| U1 | ESP32-S3-DevKitC-1 N16R8 | 1 | 2x 1x22 female headers, rows 25.4 mm apart (VERIFY) | USB-UART port = laptop link |
| U2..U4 | TMC2209 V1.3 (BIGTREETECH) | 3 | 2x 1x8 female headers each, rows 12.7 apart | X, Y, wrist |
| U7 | TMC2209 V1.3, spare | 1 | same | hot spare (its socket can stay empty) |
| U5 | **Mini560 Pro, 5 V version** | 1 | 4 pads: IN+ IN- OUT+ OUT- (VERIFY on your module), about 29 x 18 x 5.4 | 5 V logic: ESP32, magnet, connector C. Input 7..32 V (5 V version), up to 5 A |
| U6 | **Mini560 Pro, 5 V version** | 1 | same | servo rail. The Mini560 has no 6 V version (3.3 / 5 / 9 / 12 V); **never use the 9 V one on the MG996R** (max 7.2 V). At 5 V the lift uses about 25 % of the servo's stall torque: fine |
| U8 | BSS138 level shifter, 2-channel (or 4-channel) | 1 | 1x6 header (VERIFY pin order: LV, HV, GND, LV1/HV1, LV2/HV2) | connector C UART 5 V <-> ESP32 3.3 V |

**What the BSS138 is:** a tiny MOSFET. The "BSS138 level shifter" is a small board with BSS138s and pull-up resistors that
translates a signal between 3.3 V and 5 V in both directions. Connector C (the rules' UART) works at 5 V, but the ESP32's pins
are 3.3 V and are damaged by 5 V, so the UART TX/RX lines go through it.

## B. Small parts on the PCB
| Ref | Part | Qty | What for |
|---|---|---|---|
| Q1 | IRLZ44N logic-level N-MOSFET, TO-220 (home board; AO3400A SOT-23 on the factory board) | 1 | switches the magnet from GPIO21 |
| D1 | SS34 Schottky (SMA) | 1 | +5V LOGIC -> ESP32 board 5V pin (stops back-feeding the laptop's USB) |
| D2 | SS34 Schottky (SMA) | 1 | flyback across the magnet coil |
| F2 | PTC resettable fuse 0.5 A, 1206 | 1 | connector C V pin: a short on an external device cannot pull down the logic rail |
| C1..C4 | 100 uF 35 V SMD electrolytic, 8 x 10 | 4 | one at each TMC2209 VM pin |
| C5 | **470 uF 16 V SMD electrolytic, 8 x 10** | 1 | servo rail, at the servo connector: catches the MG996R's current spikes |
| C6 | **100 nF ceramic 1206** | 1 | servo rail, next to C5 (high-frequency noise) |
| C7 | 100 uF 10 V SMD electrolytic, 6.3 x 7.7 | 1 | +5V LOGIC, near the ESP32 (magnet switch-on spike) |
| C8 | 10 nF ceramic 1206 | 1 | connector A filter |
| R1 | 100 k | 1 | stop-sense divider (top) |
| R2 | 22 k | 1 | stop-sense divider (bottom) -> GPIO47 |
| R3 | 100 k | 1 | battery divider (top) |
| R4 | 15 k | 1 | battery divider (bottom) -> GPIO2 |
| R5 | 10 k | 1 | connector B divider (top) |
| R6 | 20 k | 1 | connector B divider (bottom) -> GPIO10 |
| R7 | 1 k | 1 | connector A series -> GPIO1 |
| R8 | 1 k | 1 | TMC UART: GPIO15 TX -> PDN_UART bus |
| R9 | 1 k | 1 | servo PWM series (GPIO14) |
| R10 | 10 k | 1 | driver EN pull-up to 3V3 (drivers off while the ESP32 boots) |
| R11 | 10 k | 1 | distance sensor XSHUT pull-up |
| R12, R13 | 4.7 k | 2 | I2C pull-ups (fit only if the TOF400C has none) |
| R14 | 100 R | 1 | MOSFET gate |
| R15 | 100 k | 1 | MOSFET gate pull-down (magnet off while booting) |
| R16 | 1.5 k, 0.25 W | 1 | green LED on the drive bus (about 9 mA at 14.8 V) |
| R17 | 220 R | 1 | red LED from GPIO42 (about 6 mA) |
| TP1..TP4 | test pads (2 mm, through-hole) | 4 | 3V3, +5V LOGIC, +5V SERVO, GND (multimeter) |

Resistors and small capacitors 1206 (home board), hand-solder pads; they sit on the copper side.
TMC2209 addresses 0..3: MS1/MS2 tied to GND / 3V3 by traces (no parts).

## C. Connectors on the PCB
| Ref | Type | Pins | Goes to |
|---|---|---|---|
| J1..J3 | JST-XH 4-pin | 4 | X, Y, wrist steppers |
| J4 | JST-XH 4-pin (optional) | 4 | spare driver |
| J5 | 1x3 male pin header 2.54 | 3 | MG996R servo (signal, +5V SERVO, GND) |
| J6 | JST-XH 2-pin | 2 | magnet |
| J7, J8 | JST-XH 2-pin | 2 | X home switch, Y home switch |
| J9 | JST-XH 5-pin | 5 | distance sensor: 3V3, GND, SDA, SCL, XSHUT |
| J10 | XT60PW-M (PCB, horizontal) | 2 | battery in (after F1, before the stop) |
| J11 | XT30PW-M (PCB, horizontal) | 2 | drive bus in (after stop block 1) |
| J12 | JST-XH 2-pin | 2 | stop block 2: pin 1 +5V LOGIC out, pin 2 magnet 5 V back |
| J14 | JST-XH 2-pin | 2 | green LED |
| J15 | JST-XH 2-pin | 2 | red LED |
| J16 | JST-XH 2-pin | 2 | start button |
| J17 | 2x5 box header (IDC) | 10 | panel connector board: A (SIG, V, GND), B (SIG, V, GND), C (TX, RX, V, GND) |

## D. Off the PCB (panel, cables, base)
| Part | Qty | Where |
|---|---|---|
| 4S LiPo 2200 mAh, XT60 | 1 | battery tray |
| XT60 + XT30 plugs (to match J10 / J11; check the genders) | 1 each | battery lead, stop button lead |
| F1: inline blade fuse holder + 5 A blade fuse (+ spares) | 1 | battery lead, before everything |
| Emergency stop 22 mm, latching, 2 NC blocks (XB2 / LAY37) | 1 | control panel |
| Start button 16 mm, momentary | 1 | control panel |
| LED 5 mm green + 5 mm red, with panel holders | 2 | control panel |
| Female headers 1x3, 1x3, 1x4 on a small strip board (connectors A, B, C) | 1 | control panel wall |
| 400-point breadboard | 1 | breadboard tray |
| JST-XH crimp housings + contacts kit (2/4/5-pin), Dupont 3-pin, 10-pin IDC ribbon | 1 kit | harnesses |
| Silicone wire AWG16 (battery), AWG18 (drive bus), AWG24/26 (signals), 4-core AWG24 (steppers) | | harnesses |
| M3 standoffs 10 mm + screws | 4 | under the PCB (as now) |

## Open / VERIFY
- Mini560 Pro pad layout and exact size: send a photo of yours (top and bottom), or its listing.
- BSS138 module pin order, ESP32 DevKitC header row spacing.
- Whether the TOF400C has its own I2C pull-ups.
- Organisers: self-designed PCB allowed? Connector A/B V pin voltage (full rules text).
