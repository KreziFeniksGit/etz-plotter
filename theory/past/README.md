# Past papers: VsOSh informatics, Robotics profile, 2025-26 (first year in informatics)

From Egor (30 Oct). The `.txt` files are pdftotext extracts. Formulas inside the final-stage solutions are partly broken
in the text, so check the PDF for those. Pictures: PyMuPDF is installed (`python -m pip install pymupdf`), and
`pymupdf.open(f)[page].get_pixmap(dpi=90).save("p.png")` renders a page.

| File | What |
|---|---|
| `regional_2025-26_tasks.pdf/.txt` | Regional stage, theory, grades 10-11: conditions only, no key |
| `final_2025-26_solutions.pdf/.txt` | Final stage, theory, grades 10-11: conditions + answers + solutions |
| `regional_2025-26_key.md` | Our own solutions for the regional paper. **Don't open before you've done it as a mock.** |
| `regional_2025-26_official_key.pdf/.txt` | Official regional answers + solutions (from Egor, 31 Oct). Matches our key on all 13 |

## What the 2025-26 format looked like

- Regional: 180 min, 13 tasks = 9 common + 4 specialised (humanoid, aerial, manipulators, wheeled). You solve all
  common tasks and **one** specialised task. Answering two specialised tasks zeroes them. Max 40 points.
- Points: regional 2 / 4 / 7 per task; final 1 / 2 / 3 / 5. All or nothing, no partial credit.
- Answer = **integer only**, rounded normally, no units. The written solution must match. Answers are on a paper
  form with a checksum (sum of all answers).
- No programming tasks, and no electrics / logic / MCU tasks at all.

## What changes in 2026-27 (official rules, `../vsosh_robotics_regional_2026-27.txt` section 5)

240 min, 45 points, answers typed into a testing system, 6-8 calculation tasks + **2 programming tasks**
(auto-tested on test sets). The answer format is "as the task says", so it is not necessarily an integer.

## Task types seen (both papers, 26 tasks)

| Kind | Examples | Count |
|---|---|---|
| Mechanics / dynamics | incline + friction, balancing robot, reduced inertia through a gearbox, cutter power M·ω, rolling + air drag power, 3-link arm holding torque, tug robot wheel force | 8 |
| Geometry / trig / navigation | radar + chord, beacon bearings, humanoid steps with turns, lidar + accelerating object, linkage inversion | 5 |
| Algorithm puzzles (math) | min remainder over divisors, hypercube walk (Gray code), prefix sums cost, counting intersections | 4 |
| Vision | Hough line (rho, theta) pixel count, RANSAC RMS, area ~ r^2 -> mass ~ r^3, falling camera rotation | 4 |
| "Control" = optimisation | terminal speed F = k v^2, maximise a metric over m (derivative) | 2 |
| Specialised: aero / humanoid IK | focus of wing + tail, max lift/drag, 2-link leg IK | 3 |

## Traps seen in the keys

- Rounding to an integer can give **0** (final 10-09: 0.47 -> 0; 10-12: 0.42 N·m -> 0). Keep the unit the task asks for.
- "Multiply by 100 and round" or "multiply by -1": do it last.
- Odd units: N·cm, kg·cm (torque as mass x arm, no g), km and m/s mixed.
- Some given data is not needed (regional 10-13 gives μ but no mass).
- The final-stage key table is shifted by one row against the task numbers. Trust the solution text.
