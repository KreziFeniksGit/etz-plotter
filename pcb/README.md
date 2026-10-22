# Main control PCB (KiCad 10)

**Current version: HOME (single-sided, toner transfer), placed, NOT routed - Egor routes it by hand (22 Oct).**
`build_pcb.py` has `HOME = True`: 169 x 136 mm, copper on the bottom only, traces >= 0.5 mm (signals 0.6, 5 V 1.2, motors 1.0,
power 2.0), 0.6 mm gaps (0.8 around power), oval 1.7 x 2.6 pads with 1.0 mm drills on 2.54 mm rows (round 1.9 on the 2x5 header),
1206 parts and the SMD parts on the copper side, IRLZ44N (TO-220) instead of the SOT-23 MOSFET. DRC with these rules: 0 errors.
The auto-router could not do it single-sided (66 wire jumpers + 70 drilled holes and still 9 open): route by hand.
Tips for routing by hand:
- Route power first (VBAT, VDRIVE, GND), then motors, then signals. Leave GND for a ground pour at the end (Place > Zone, B.Cu).
- Where a trace cannot cross, use a wire jumper on the top side: drill two holes, insulated wire, solder underneath.
- **You may swap ESP32 pins** to remove crossings (the firmware is not written yet). Allowed GPIOs: 1, 2, 4..18, 21, 39..42, 47
  (38 only if your board is v1.0). A_IO and VBAT_SENSE must stay on GPIO 1..10 (ADC1). Never use 0, 3, 19, 20, 26..37, 43..46, 48.
  Tell Claude which pins you moved: wiring.md, the schematic and the firmware follow.
- For printing: File > Plot, layer B.Cu + Edge.Cuts, PDF, black, scale 1:1, drill marks "small"; NOT mirrored for the bottom layer
  (the toner transfer itself mirrors it the right way).

| File | What |
|---|---|
| `bom.md` | every part on and off the board, the power tree, what is still VERIFY |
| `build_pcb.py` | parts, nets (from `wiring.md`), placement, JLCPCB rules, net classes -> routes with Freerouting -> GND pours + stitching vias |
| `etz_control.kicad_pcb` | the board (open it in KiCad) |
| `etz_control.kicad_sch` + `etz_control_schematic.pdf` | **full connection schematic** (KiCad + PDF), A2; `schematic_preview.png` |
| `build_sch.py` | makes the schematic from the same parts/nets as `build_pcb.py`, then checks: KiCad netlist == board nets, ERC, PDF |
| `etz.kicad_sym`, `etz.pretty/`, `sym-lib-table`, `fp-lib-table` | project library: symbols + footprints of the plug-in modules (ESP32-S3-DevKitC-1, TMC2209, Mini560 Pro, BSS138) |
| `etz_control_gerbers_jlcpcb.zip` | upload this to JLCPCB / PCBWay (Gerbers + drill), 2 layers, 1.6 mm, 1 oz |
| `render_top.png`, `render_bottom.png`, `copper.svg` | pictures |
| `drc.json` | KiCad design-rule check result |

Rebuild: `"C:\Program Files\KiCad\10.0\bin\python.exe" pcb\build_pcb.py` (about 3 min: routing), then
`kicad-cli pcb drc --refill-zones pcb\etz_control.kicad_pcb`, then the Gerber / drill export (see the end of this file).
Routing needs Java 25 + Freerouting 2.5 in `%USERPROFILE%\tools` (`jre25\`, `freerouting-2.5.0.jar`).

## v1.0 (22 Oct): 130 x 105 mm, 2 layers, 69 footprints, 58 nets, fully routed
DRC: 0 unconnected, 0 clearance errors. Remaining warnings (accepted): the XT60 / XT30 outlines cross the board edge on purpose
(the plug goes in from the edge); 3 GND pins (U1B pin 1, U8A/U8B pin 4) have 1 thermal spoke instead of 2 - they are also
joined by a trace.

## Review checklist (from JLCPCB / Altium / DigiKey / TI layout guides) and how this board meets it
| Check | Status |
|---|---|
| DRC set to the fab's limits, not KiCad defaults | min track / clearance 0.15, via 0.6 / 0.3 drill, hole-to-hole 0.5, copper to edge 0.4 (JLCPCB standard is 0.127 / 0.3) |
| Trace width by current (IPC-2152, ~10 C rise) | VBAT / VDRIVE 1.5 mm (~4 A), 5 V rails 1.0 mm, motor phases 0.8 mm (0.9 A), signals 0.3 mm |
| Bulk capacitor close to each driver's VM | C1..C4 100 uF directly below each TMC2209 |
| Servo rail spike capacitor | C5 470 uF + C6 100 nF next to the servo rail |
| Solid ground | GND pour on both layers, 44 stitching vias, thermal reliefs for hand soldering |
| Footprints match the real parts | KiCad standard library; module pinouts VERIFY (below) |
| Polarity marked | + on electrolytics and XT plugs, K bar on diodes, pin 1 marks on headers |
| Labels | every connector named on the silkscreen; board name + version |
| Test points | 3V3, +5V, +5V servo, GND |
| Mounting | 4x M3 holes, 4 mm from the corners |
| Protection | main 5 A fuse inline; 0.5 A PTC on connector C's V pin; flyback diode on the magnet; EN pull-up keeps drivers off at boot; gate pull-down keeps the magnet off |
| Auto-router output reviewed | 0 unrouted; power traces checked wide; see renders |
| Not applicable | antenna keep-out (the radio is never used), impedance control, fiducials (hand assembly) |

## VERIFY before ordering (guesses about bought modules)
ESP32-S3-DevKitC-1 pin rows (22.86) and pinout revision (v1.1 has its RGB LED on GPIO38 = TOF XSHUT here); TMC2209 V1.3
pin order; Mini560 Pro pad positions (IN at one end, OUT 25.4 mm away - measure yours); motor
connector pin order (match your motor cables); XT60 / XT30 genders. A photo of each module with a ruler settles them.

## Export commands
```
kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts --subtract-soldermask -o pcb/fab/ pcb/etz_control.kicad_pcb
kicad-cli pcb export drill --format excellon --excellon-units mm --excellon-separate-th -o pcb/fab/ pcb/etz_control.kicad_pcb
```

## Making your own PCB from the schematic
Open `etz_control.kicad_pro`, open the schematic, then Tools > Update PCB from Schematic (F8) into a NEW board (or delete the
footprints in the existing one first: the generated board uses two sockets per module, the schematic one footprint per module).
Footprints are already assigned. Net classes (track widths) are in the project: Power 1.5 mm, Rail5V 1.0, Motor 0.8, signals 0.3.
