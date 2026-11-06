---
tags: [component, decision]
source: components.csv
updated: 2026-11-06
---
# MG996R servo

Lifts the magnet through the [[Parallelogram lift]] (face 5..40 mm). Runs from its own 5 V rail ([[Mini560 Pro regulators]]).
History: DS3218 -> **MG996R (Egor, 11 Oct)** -> RDS3235 modelled (16 Oct) -> dropped, back to MG996R. See [[Egor changes parts often - confirm before investing]].
Numbers: ~11 kg·cm at 6 V; lift needs 0.23 N·m = ~22 % of stall; dead band ~5 us ≈ 0.6 mm height.
Firmware: `servo <us>` with a slew limit, "done" is an estimate (no feedback) - [[Firmware]].
Sizes came from a third-party model: VERIFY tab holes 48.4, spline offset. Vendor STEP in `vendor/`.
