---
tags: [decision]
source: pcb/split_boards.md
updated: 2026-11-06
---
# Split single-sided PCBs

**23 Oct:** the control electronics are 3 hand-routed single-sided boards (drivers, power, controller), joined by
straight 1:1 JST-XH cables - made at home by toner transfer. Replaced the v1.0 double-sided JLCPCB board.
Why: single-sided boards are etchable at home; splitting avoids crossings.
Egor will not make new boards: changes are add-on modules and wires ([[Measure everything]]).
No power switch on the boards: known gap ([[Battery left connected drains through the logic regulator]]).
Related: [[Home toner transfer PCB rules]], [[Route PCB traces only at 0, 45 and 90 degrees]], [[Pin map]], [[Electronics]].
