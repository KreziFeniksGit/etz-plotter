# ETZ control: TEST BOARD T1 (2-layer, JLCPCB), 9 Nov 2026

This is a test version of `../etz_control.kicad_sch`, built as a factory 2-layer board. **The originals are untouched.** Everything lives in this folder.

| File | What it is |
|---|---|
| `test_parts.py` | Parts table: a copy of the one in `build_pcb.py`, plus the fixes below |
| `test_sch.py` → `etz_test.kicad_sch`, `etz_test_schematic.pdf` | The fixed schematic (ERC 0, netlist identical to the parts table) |
| `layout.py` → `etz_test.kicad_pcb` | The board, made from the schematic's netlist; footprints are linked to the symbols, so "Update PCB from Schematic" works |
| `nl.py`, `probe.py` | Netlist reader and a footprint-size helper |
| `renders/` | Top and bottom pictures |

To rebuild:
```
"C:\Program Files\KiCad\10.0\bin\python.exe" test_sch.py
"C:\Program Files\KiCad\10.0\bin\python.exe" layout.py 30
```

## Fixes compared to etz_control v1.0, and why

1. **XT30 polarity (J11).** The KiCad AMASS footprint has pad 1 = minus and pad 2 = plus. v1.0 had them swapped, so the drive battery would have reversed VM on all four TMC2209s, which kills them.
2. **TVS diodes D3 and D4 (SMBJ18A) at both power inputs.** They clamp spikes when a plug goes in and when motors brake. 4S LiPo is 16.8 V max, so an 18 V stand-off does not conduct in normal use. If the battery is plugged in backwards, the TVS shorts it and the battery fuse blows, and nothing else gets reverse voltage. VERIFY: the clamp is ~29 V and the TMC2209 VM absolute maximum is 29 V, which leaves no margin. SMBJ16A (clamp ~26 V) is the safer choice if 4S never goes above 16.8 V (stand-off 16 V, so it leaks a little at full charge).
3. **100 nF ceramic C9–C12 at every driver VM pin.** The 100 µF electrolytic is too slow for the chopper's fast current edges. The small cap sits on the VM and GND pins.
4. **4.7 µF ceramic C13 and C14 at each Mini560 input.** A buck draws its input current in sharp pulses. A ceramic cap right at the input keeps that loop small, which means less noise.
5. **ADC filter caps C15 (VBAT_SENSE) and C16 (STOP_SENSE),** like C8 already does on A_IO. A divider with a cap gives the ADC a low-impedance source.
6. **Test points TP5 VBAT, TP6 VDRIVE, TP7 GND,** so the meter probe has a place to go.

## Layout decisions

- **Zones:** power on the right edge (XT60 + XT30 face out, TVS on their pins, then both bucks). Drivers along the top, each with its motor plug straight above its motor pins. ESP32 bottom-left with the USB end at the left edge. All small plugs along the bottom.
- **Drivers in pin order:** W, Y, X, spare left to right, which is the order of their STEP/DIR pins on the ESP32. Signals run straight down with no crossings.
- **Power first:** VBAT, VDRIVE, the 5 V rails, the motor phases and 3V3 are routed first, at widths chosen by current (1.5 / 1.0 / 0.8 / 0.5 mm). Signals are routed afterwards, around them.
- **Ground:** no ground traces. Every SMD ground pad gets its own via into the pours. Both layers are GND pours, tied with stitching vias. The bottom layer is kept as clean as possible so the return currents have a solid path.
- **Labels:** each plug's name is on the silkscreen (X, Y, TOF, PANEL...), with + and − at the battery plugs. The revision is also etched in copper, so a bare board can still be identified.

## Left open (VERIFY / next revision)

- **GPIO38 (TOF_XSHUT).** On DevKitC-1 v1.1 the RGB LED is on IO38, and nothing can be moved: every allowed GPIO is already in use, and 3, 45, 46 and 48 are forbidden by the README. It works on v1.0. On v1.1 the LED will flicker with XSHUT. Check which DevKit version is in the box.
- **No ESD protection on J17 (panel cable).** It goes off-board, so it is the most likely place for a zap. Next revision: a TVS array.
- **No 22 Ω series resistors on the STEP lines.** They would soften edge ringing on long traces. Not needed at these lengths.
- **The spare driver U7 has no STEP/DIR.** All GPIOs are used. It only gets its power, plug and UART address.
- **Reverse polarity is handled by TVS + fuse (crowbar).** A P-FET would be nicer (no blown fuse), but at 4S the gate needs a zener clamp. See pcb-brain "P-MOSFET power path".

## Checks run (10 Nov 2026)

- Schematic: ERC 0. The netlist is identical to the parts table (77 parts, 58 nets).
- Board 146 x 100 mm, 2 layers. 580 tracks + vias, 25 ground vias at SMD pads, 193 stitching vias.
- DRC (`kicad-cli pcb drc --schematic-parity`): **0 errors, 0 unconnected, 0 schematic-parity issues**. One silkscreen-overlap warning (C13 reference touches the XT60 outline; cosmetic).
- Power width: the routes have their class width. Short neck-downs happen only where a track enters 2.54 mm-pitch module pins. The longest is about 10 mm at 1.125 mm, still ~3 A (VERIFY against the real current draw).
- 5 GND header pins (J9.2, U1.23, U3.3, U3.16, U4.16) had their thermal spokes blocked by passing tracks, so they connect solid to the pour. These are 0.64 mm pins, still easy to solder.
- Teardrops: the KiCad 10 Python API didn't expose them. Add them in the GUI if you want (Edit → Edit Teardrops).
- `gerbers/` contains the Gerber + drill files for JLCPCB. **Before ordering, open the board in KiCad, look it over yourself, and zip the gerbers.**

## How the routing works (lessons used)

1. Pass 1: only power, motor and 3V3 nets are visible to Freerouting. They get the best paths and the widest tracks.
2. The power tracks are locked. Pass 2 routes signals around them.
3. GND is never routed as tracks. Each SMD ground pad has its own via, and both layers are GND pour.
4. Bug found and fixed: at first the vias were netless, and Freerouting took them for other nets (shorts to GND). Giving them GND from the start stopped that.
