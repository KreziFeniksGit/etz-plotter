---
tags: [decision, rule]
updated: 2026-11-06
---
# STEP only, never STL

Egor's standing instruction: outputs are STEP only, never STL (not even as an extra) - his slicer opens STEP and STEP
keeps exact geometry. `*.stl` is gitignored and the stop hook blocks a turn that leaves an STL behind
([[Rules that cannot bend belong in hooks]]). Related: [[CAD Pipeline]].
