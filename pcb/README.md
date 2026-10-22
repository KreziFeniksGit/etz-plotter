# Main control PCB (KiCad 10)

| File | What |
|---|---|
| `bom.md` | every part on and off the board, the power tree, what is still VERIFY |
| `build_pcb.py` | parts, nets (from `wiring.md`), placement, JLCPCB rules, net classes -> routes with Freerouting -> GND pours + stitching vias |
| `etz_control.kicad_pcb` | the board (open it in KiCad) |
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
pin order; Mini560 Pro pad positions (IN at one end, OUT 25.4 mm away - measure yours); BSS138 module pin order; motor
connector pin order (match your motor cables); XT60 / XT30 genders. A photo of each module with a ruler settles them.

## Export commands
```
kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts --subtract-soldermask -o pcb/fab/ pcb/etz_control.kicad_pcb
kicad-cli pcb export drill --format excellon --excellon-units mm --excellon-separate-th -o pcb/fab/ pcb/etz_control.kicad_pcb
```
