---
tags: [hub]
source: docs/status.md
updated: 2026-11-06
---
# ETZ Plotter

The project-round device: a Cartesian XY plotter that finds checkers with a camera, picks them with an electromagnet,
turns them (wrist) and stacks them up to 5 on the official field. Not built yet (Nov 2026); everything is tested in CAD and on the [[Digital twin]].

- Why this shape: [[Cartesian plotter instead of SCARA]]
- [[Mechanics]] - frame, axes, wrist, lift
- [[Electronics]] - power, boards, pins
- [[Firmware]] - ESP32-S3, own libraries
- [[Laptop Software]] - twin, planner, run program, vision
- [[CAD Pipeline]] - FreeCAD scripts and checks
- [[Bring-up]] and [[Competition day]]
- Known risks: [[X reach shortfall]], [[ETZ speed minimum]], [[Magnet release]]
- Rules it must meet: [[Competition Rules]]

Source: `docs/status.md` (version history, open items), `README.md`.
