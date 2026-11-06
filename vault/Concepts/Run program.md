---
tags: [concept]
source: laptop/run.py
updated: 2026-11-06
---
# Run program

`laptop/run.py`, the competition run (ETZ cycle): choose task + params -> red LED -> wait Start -> set speeds -> home ->
scan -> fit the sheet ([[Field transform]]) -> plan ([[Route planner]]) -> one [[Move queue]] per move -> park -> LED off.
Any crash / hot / watchdog / battery event -> safe abort and park.
Tested end to end on the [[Digital twin]] (debug tasks, 30/30 random tasks, fault injection).
Lessons: [[Do not react to your own abort messages]], [[Firmware defaults must meet the rules]].
Related: [[Competition day]], [[Laptop Software]].
