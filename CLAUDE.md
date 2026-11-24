# ETZ plotter - instructions for Claude

You are continuing Egor's olympiad robotics project with him. Read `docs/status.md` first (where we are, decisions,
open items). Competition rules: `docs/etz_rules_summary.md` (official PDF `docs/etz_kratko_26_27.pdf`).
Per-area rules load by themselves from `.claude/rules/` (cad, firmware, laptop, pcb) when you open files there.
Knowledge graph (Obsidian vault, Egor's and Claude's shared knowledge): `vault/Home.md`. Before work in an area, open its
hub and the lessons it links. After a surprise or a correction, add a `lesson` note; when a decision changes, update its
note. Rules for notes: `vault/How to use this vault.md`.

## Who and what
- Egor, grade 11, VsOSh (all-Russian olympiad) informatics, robotics profile, ETZ 2026-27 final stage.
- The device: a Cartesian XY plotter that picks checkers (26 x 5 mm, steel washer inside) with an electromagnet,
  rotates them (wrist) and stacks them up to 5, on a 600 x 500 polygon. Designed here as parametric FreeCAD Python
  scripts; ESP32-S3 firmware; laptop programs (digital twin, planner, run program, vision).
- Egor writes in English: answer in English, plainly, short. He is not a mechanical engineer: explain what a thing
  is for when it is not obvious, and show pictures (renders) when it helps.
- He works on Windows (PC, laptop) and his phone; sessions may run locally or in the cloud. The plotter is not
  built yet (29 Oct): hardware results come from the twin and the checks until bring-up (`docs/bringup.md`).

## Standing instructions
- STEP only, never STL files (not even as an extra): his slicer opens STEP. A stop hook also checks for `*.stl`.
- Keep `README.md`, `docs/status.md`, `components.csv`, `wiring.md` true after each change.
- `docs/print_log.md` tracks what Egor has printed: update it when he reports a print; when you change a printed
  part's geometry, mark it REPRINT there and tell him.
- Commit with a clear message and push right after every finished change whose checks are clean, without asking.
  Why: a session can die mid-way (on 16 Oct a finished MG996R revert sat uncommitted for days) and his other devices
  pull from GitHub. A stop hook reminds you when tracked changes are left uncommitted or unpushed.
- Say plainly what is a placeholder, not modelled, only compiled, or only tested on the twin.

## How to work (Egor's request, 27 Oct)
For new features, design choices and bought parts (not for small fixes, where this only costs time):
- **Doubt the request.** If it looks wrong, wasteful or risky for this project, say so and why, before doing it.
- **Compare options.** List the possible solutions briefly (pros / cons for our case), pick one and say why.
- **Research first.** Look for existing solutions (projects, datasheets, app notes, forum fixes), adapt the good ones,
  name the sources. Firmware still uses no outside libraries: adapt ideas, write the code ourselves.
- **Find the risks.** What can fail, what is not tested, what depends on an unverified number.

## Check your own work
- Every area has its own checks (see `.claude/rules/`); run the ones that cover the change before saying it is done,
  and report the result honestly (paste the failing line).
- After a commit, confirm it landed: `git status` clean and `git log -1 --stat` shows the files. A failed command in
  a `&&` chain silently skips the rest (on 29 Oct three doc edits were lost that way).
- On Windows the Bash tool is Git Bash: heredocs and `sed -i` mangle CRLF files and non-ASCII (Cyrillic) text. Edit
  files with the Edit / Write tools, not shell tricks.
- When Egor corrects the same thing twice, add a one-line rule here or in the right `.claude/rules/` file.

## Repository map
| Path | What |
|---|---|
| `wrist/` | `wrist_module.py` (tolerance constants in section 1, bought-part data, 9 printed parts, `pose()`), `dfm.py` (print-rule checks), `review.py` (interference + DFM) |
| `frame/` | `frame.py` (base, axes, carriage, post, boom, panel, trays, electronics), `chains.py`, `cables.py`, `fasteners.py` (`bom()`) |
| `assembly.py` | `world(PYC, PXB, h, wrist_deg, ...)` places everything; all whole-device checks -> `out/assembly_review.json` |
| `export_gui.py` | Coloured, grouped STEP + FCStd and `out/printed/*.step` (needs the FreeCAD GUI) |
| `tools/` | `stability.py`, `fea.py` (see `docs/stiffness_review.md`), `render_pose.py`, `assembly_sim.py`, `anim_export.py`, `plywood_dxf.py` |
| `camera_stand/` | Printed test stand for the webcam board (no plotter needed); program `laptop/cam_stand.py` |
| `wrist_stand/` | Printed test stand that holds the real wrist module at its real height (servo, magnet, wrist stepper tests without rails) |
| `tolerance/` | 11 tolerance test coupons; `tolerance/README.md` = how to test |
| `pcb/` | 3 split single-sided hand-routed boards (`build_drivers.py`, `build_power.py`, `build_controller.py`), see `pcb/split_boards.md`; `docs/pcb_guide.md` |
| `firmware/` | ESP32-S3 firmware, own libs in `firmware/lib/`; commands in `firmware/README.md` |
| `laptop/` | `field.py` (official field), `machine.py`, `twin.py`, `tasks.py`, `route_planner.py`, `run.py`, `esp_dashboard.py`, `esp_link.py`, vision |
| `docs/` | `status.md`, `bringup.md`, `competition.md`, `ideas.md`, `design_rules.md`, `history/` (old SCARA design etc., history only) |
| `vendor/` | Real STEP models of bought parts (Egor's downloads), swapped in by `world(detail=True)` |
| `components.csv`, `wiring.md` | Every bought component and why; power, pin map, harnesses, driver currents |

Machine coordinates: X along the 600 mm side, Y along 500, Z up from the table, mm. Since v2.17 the polygon starts at
machine x 13 (`frame.FIELD_DX`): zone 1 x 13..363, field from x 363; polygon x = machine x - 13.
Y-carriage parts are built at PYC0 = 40 and moved by (0, PYC-40, 0); wrist parts are built in module coordinates
(x from PXB, y from PYC, absolute z) and moved by `W.pose()` then (PXB, PYC, 0). Travel: PYC 40..376, PXB 287..452,
magnet face h 5..40 mm, wrist any angle. Groups: base, ycar, wm_xcar, wm_armT, wm_armB, wm_end, wm_wrist, chainX, chainY.
The ETZ field frame (laptop) is different: see `laptop/field.py` and `laptop/machine.py`.
