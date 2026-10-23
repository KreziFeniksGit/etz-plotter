# Split control boards (single-sided, toner transfer) - v1, 23 Oct 2026

Three small boards instead of one, each **hand-routed** (every track placed by a script, no auto-router), copper on the
bottom only. Traces >= 0.6 mm (power 2.0, 5 V 1.2, motors 1.0), gaps >= 0.6 mm, ground pour on the copper side,
SMD parts (1206 / SMA / SMD electrolytics) on the copper side, connectors and module sockets on the top.
KiCad DRC on each: **0 unconnected**, no clearance errors (only "starved thermal" warnings = a GND pin with 1 of 2 spokes).

| Board | Folder / script | Size | What is on it | Wire links |
|---|---|---|---|---|
| Driver | `drivers/`, `build_drivers.py` | 64 x 112 | 3x TMC2209 (X, Y, wrist) + 100 uF 25 V each, 3 motor plugs, XT30 VDRIVE in | 0 |
| Power | `power/`, `build_power.py` | 94 x 84 | XT60 battery in, XT30 drive in / out, 2x Mini560 Pro 5 V, servo plug + 470 uF + 100 nF, magnet switch (100N03A TO-252, SS34), stop block 2 plug, green LED, battery and stop dividers | 0 |
| Controller | `controller/`, `build_controller.py` | 118 x 115 | ESP32-S3-DevKitC-1 on sockets, all small parts, plugs to the other boards, TOF, home switches, start, red LED, panel A/B/C | 7 |

**Wire links** (controller only): insulated wire on the component side between two 2 mm pads, soldered underneath.
They are drawn as top-layer tracks (L1..L7 in KiCad): L1, L2 = TMC UART bus between the driver plugs; L4..L7 = 3V3 to the
driver plugs (a copper chain there would cut the ground pour into islands); L3 = 3V3 over the power-plug lines to the TOF.

## Cables (straight 1:1 JST-XH, pin 1 to pin 1; all <= 6 pins)
| From | To | Pins |
|---|---|---|
| controller J1 / J2 / J3 | driver J1 / J2 / J3 (X / Y / wrist) | 1 GND, 2 EN (GND), 3 UART, 4 STEP, 5 DIR, 6 3V3 |
| controller J4 | power J5 | 1 MAG_IO, 2 GND, 3 +5V, 4 VBAT_SENSE, 5 STOP_SENSE, 6 SERVO_IO |
| power J3 (XT30) | driver J7 (XT30) | VDRIVE, GND |
| controller J5 | panel header strip | 1 A_SIG, 2 B_SIG, 3 C_TX, 4 C_RX, 5 +5 V (PTC), 6 GND |
Checked by script: the plug pins of the three boards match net for net.

## Design decisions made for single-sided routing
- ESP32 GPIOs re-assigned (see `wiring.md` section 2); driver EN tied to GND (drivers off via UART TOFF = 0); TOF XSHUT tied to 3V3.
- UART addresses X 0, Y 2, wrist 3 (address 1 would need a crossing). No spare driver socket: a spare module replaces a failed one.
- Motor plug order 2B, 2A, 1A, 1B (swapping a coil's ends only reverses the motor: fix the direction in firmware).
- Small parts under the ESP32 board between its pin rows (they are on the copper side, the ESP32 sits on top on sockets).

## Mini560 Pro footprint (from Egor's photo, 23 Oct)
8 pins: IN column (EN side) and OUT column 29 mm apart; in each column two + pins (2.54 apart), 8.92 mm gap, two - pins.
Mounted component side up, IN end toward the board top edge, + pins on the right. EN is left open (module on). Check that
the back of your module says IN on the EN side.

## VERIFY before etching
ESP32-S3-DevKitC-1 pin row spacing (22.86) and pinout, TMC2209 module pin order, XT60 / XT30 genders, motor cable order. Photos of the modules with a ruler settle them.

## Printing for toner transfer
KiCad: File > Plot, layer B.Cu + Edge.Cuts, PDF, black, scale 1:1, drill marks "small", NOT mirrored (the copper is on the
bottom: the transfer mirrors it the right way). Top-layer tracks (wire links) are not printed: they are the wires you add.
