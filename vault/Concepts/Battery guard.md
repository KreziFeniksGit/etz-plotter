---
tags: [concept]
updated: 2026-11-06
---
# Battery guard

Firmware v5: battery read every 100 ms on GPIO2, averaged; `event battery low` < 14.8 V, `battery stop` < 14.0 V (motors stop,
moves refused until > 15.1 V). Under 5 V = no battery (USB bench) -> guard off.
Bench trap: the board reads 11.8 V -> every move refused; `set batstop 0` until the [[4S LiPo battery]] is checked
([[Verify ADC readings with a multimeter]]). Related: [[Measure everything]], [[Firmware]].
