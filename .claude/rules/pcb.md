---
paths:
  - "pcb/**"
---
# PCB work (KiCad 10, run with KiCad's Python)

Egor will not make new boards: add-on modules and wires only, unless he says otherwise. Use the `kicad` skill for reviews.
Lessons from `docs/pcb_guide.md` (home toner transfer, single-sided):
- Route only at 0 / 45 / 90 deg; put a short 45 deg jog before an off-grid pad instead of a free diagonal. No acute
  angles (acid traps).
- Traces >= 0.5 mm (we use 0.6), clearance >= 0.4 mm, through-hole pads 2 mm+, ring >= 0.5 mm, thermal spokes on pour
  pads, no copper text under ~2 mm, fill empty areas with ground.
- Every board needs a way to switch it off and to measure it: think about switches and test points before routing.
