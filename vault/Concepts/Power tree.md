---
tags: [concept]
source: wiring.md
updated: 2026-11-06
---
# Power tree

4S LiPo -> 5 A fuse -> E-stop contact 1 -> drive bus 14.8 V (TMC2209 VM, servo regulator, green LED, stop sense) ;
-> logic regulator 5 V (ESP32, connector C, magnet via E-stop contact 2) ; battery divider to GPIO2.
All grounds meet at one point. Theory link: [[Electrics for the theory round]].
Related: [[4S LiPo battery]], [[Mini560 Pro regulators]], [[Stop button]], [[Battery left connected drains through the logic regulator]].
