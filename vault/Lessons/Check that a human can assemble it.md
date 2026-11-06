---
tags: [lesson]
updated: 2026-11-06
---
# Check that a human can assemble it

**What happened:** 16 Oct, Egor: "make sure it is humanly possible to assemble". The simulation found hidden screw heads, unholdable nuts, a magnet screw that could not pass the shaft bore.

**Rule:** Every new part goes through `tools/assembly_sim.py`: insertion path, tool reach, nut holding, iron reach.

Related: [[Assembly simulation]], [[Fasteners model]], [[P20-15 electromagnet]]
