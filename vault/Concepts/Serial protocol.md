---
tags: [concept]
source: firmware/README.md
updated: 2026-11-06
---
# Serial protocol

Text lines over USB serial: commands (`gomm x 100`, `linemm 100 200`, `servo 1500`, `mag on`, `wrist 90`, `q ...`, `qrun`),
replies `ok ...` / `err ...`, async `event ...` lines, `json` status. `echo 0` for programs, `wd 1500` + `ping` for the laptop watchdog.
Own `Console` library: line editor + splitter ([[No outside firmware libraries]]).
**Shared contract:** firmware, [[Digital twin]] and [[Run program]] must match - change them together.
Idea: binary protocol with CRC (`docs/ideas.md` #31). Source: `firmware/README.md`.
