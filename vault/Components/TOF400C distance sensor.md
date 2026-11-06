---
tags: [component, decision]
source: wiring.md
updated: 2026-11-06
---
# TOF400C distance sensor

VL53L1X laser time-of-flight under the wrist shelf (**Egor, 16 Oct**). Counts checkers in a stack: levels =
round((field − reading) / 5 mm). Needs >= 40 mm, so it reads with the magnet up (~74 mm to the field, 49 to a 5-stack).
I2C GPIO40/39. Not in firmware yet (idea: stack height check). Related: [[Vision pipeline]], [[Pin map]], [[Mechanics]].
