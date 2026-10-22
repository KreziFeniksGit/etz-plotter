# Main control PCB (KiCad 10)

- `bom.md`: every part on and off the board, the power tree, what is still VERIFY.
- `build_pcb.py`: parts, nets (from `wiring.md`) and placement -> `etz_control.kicad_pcb`. Edit the script, not the board,
  until routing starts. Run: `"C:\Program Files\KiCad\10.0\bin\python.exe" pcb\build_pcb.py`
- Check: `kicad-cli pcb drc pcb\etz_control.kicad_pcb` (placement: 0 violations; "unconnected" = not routed yet).
- Picture: `render_top.png` (`kicad-cli pcb render --side top ...`).

Status (22 Oct): 130 x 105 mm, 2 layers, 69 footprints, 58 nets, placed, not routed. Next: net classes (wide power
traces), routing (Freerouting, needs Java), ground pour, Gerbers for JLCPCB / PCBWay.

VERIFY before ordering (guesses about bought modules): ESP32-S3-DevKitC-1 pin rows (22.86) and pinout revision (v1.1 has
its RGB LED on GPIO38 = TOF XSHUT here), TMC2209 V1.3 pin order, Mini560 Pro pad positions, BSS138 module pin order,
motor connector pin order (match your motor cables).
