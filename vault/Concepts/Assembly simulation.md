---
tags: [concept]
updated: 2026-11-06
---
# Assembly simulation

`tools/assembly_sim.py` (16 Oct): builds the device in print/build order and checks each part slides in, each screw head
can travel in, a tool reaches it, nuts can be held, T-nut slots stay open, the iron reaches inserts.
Found 6 real problems (hidden screw heads, unholdable nuts...). Lesson: [[Check that a human can assemble it]].
Related: [[Fasteners model]], [[CAD Pipeline]].
