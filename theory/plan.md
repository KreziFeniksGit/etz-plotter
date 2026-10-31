# Theory round plan (VsOSh informatics, Robotics profile, regional, grade 11)

Exam: **Sat 24 Jan 2027**, day 2, 240 min, **45 of 100 points**. 6-8 calculation tasks (answer typed into the
system, no live check, a typo is NOT fixed) + **2 programming tasks** (C++/Python, auto-tested, results shown live).
Engineering calculator allowed (not programmable). Rules: `vsosh_robotics_regional_2026-27.txt` section 5, topics
in Приложение 1.

Egor's input (30 Oct): electrics fairly strong (not 100%), **mechanics weak**, 7+ h/week,
wants short explanations + daily problem sets + mock tests. **Rule (31 Oct): all tasks, tests and explanations in Russian.**

## What the real tasks look like (main source: `past/`)

The 2025-26 regional and final papers (see `past/README.md`) are the best guide to the calculation part. That was
the first year of this profile in informatics. Of 26 tasks: 8 mechanics/dynamics, 5 geometry/navigation,
4 algorithm puzzles, 4 vision, 2 optimisation ("control"), 3 specialised. **No electrics, logic or MCU tasks at all.**
The tasks are physics-olympiad style with a robot story: read carefully, find the model, often one trick.

## Ranking

| # | Area | Seen 2025-26 | Egor | Priority |
|---|---|---|---|---|
| 1 | Mechanics: statics, friction, incline, dynamics, rotation, inertia through a gearbox, power, drag | 8 / 26 | weak | **top** |
| 2 | Geometry + trig + navigation (bearings, chords, odometry with turns, linkages) | 5 / 26 | ? | **top** |
| 3 | Programming (2 tasks in 2026-27, new) + algorithm puzzles | 4 / 26 + 2 new | ? | **high, every week** |
| 4 | Vision geometry (Hough line, RANSAC, pixel areas, scaling) | 4 / 26 | ? | high |
| 5 | Optimisation with derivatives, terminal speed; P/PID basics | 2 / 26 | ? | medium |
| 6 | Specialised: pick **one** track and train only it (manipulators or wheeled fit you best) | 1 of 4 | - | medium |
| 7 | Electrics, sensors, logic, MCU (in the topic list, absent from 2025-26) | 0 / 26 | strong-ish | low: one quick pass |

Doubt: you didn't pick coding practice, but the 2 programming tasks are new for 2026-27 and are probably worth
10-15 of the 45 points, with results shown live (easy points if you're fast). I keep 1-2 coding tasks a week.

## Week plan (about 1 h a day)

| Week | Dates | Topics | Mock |
|---|---|---|---|
| 1 | 30 Oct - 5 Nov | **Mock 0 = regional 2025-26** (3 h, diagnostic); statics: torque, levers, arm holding torque, incline + friction | Mock 0 |
| 2 | 6 - 12 Nov | Dynamics: F = ma on an incline, traction limit μN, wheel force from motor torque x gearbox, tipping, balancing robot | |
| 3 | 13 - 19 Nov | Rotation: ω, rpm, moment of inertia, reduced inertia J/i², power M·ω, efficiency; drag k·v², rolling resistance, terminal speed | |
| 4 | 20 - 26 Nov | Geometry toolkit: law of cosines/sines, areas, point-line distance, vectors; navigation: bearings, radar, odometry with turns | Mini mock (2 h) |
| 5 | 27 Nov - 3 Dec | Kinematics: differential drive, arcs, 2-link arm FK/IK, leg IK, linkages; motors (DC, servo, stepper) | |
| 6 | 4 - 10 Dec | Algorithm puzzles: remainders, counting, combinatorics, graphs (hypercube, BFS), prefix sums, operation counting | |
| 7 | 11 - 17 Dec | Vision: pixels, colour, threshold, centroid, Hough (rho, theta), RANSAC + RMS, scaling laws, pinhole camera | **Mock 1 (240 min)** |
| 8 | 18 - 24 Dec | Optimisation with derivatives; P/PID, filters, sensor error | |
| 9 | 25 - 31 Dec | Specialised track deep dive; quick pass over electrics / ADC / PWM / bits | |
| 10 | 1 - 7 Jan | Programming speed: 2 timed tasks per session | **Mock 2** |
| 11 | 8 - 14 Jan | Repair the worst error types from `progress.md` | **Mock 3** |
| 12 | 15 - 23 Jan | Mock 4 early in the week, then light review of the formula sheet only | **Mock 4** |

Daily session: 10 min explanation + worked example, 35-45 min problems (3-5), 5 min check and log errors.
Mocks 1-4 = 6-8 calculation tasks in 2025-26 style + 2 programming tasks, 240 min.

## Formula sheet (must know without looking)

**Maths.** sin/cos/tan of 30/45/60; law of cosines c² = a² + b² - 2ab cos C; law of sines; triangle area
½ab sin C; arc s = Rφ (rad); rad = deg·π/180; a sin x + b cos x = √(a² + b²)·sin(x + atan(b/a));
point-line distance |ax0 - y0 + b|/√(a² + 1) for y = ax + b; RMS = √(Σd²/n);
sum of n equal steps each turned by δ: |S| = L·sin(nδ/2)/sin(δ/2); max/min: f'(x) = 0, then check integers nearby.

**Statics.** G = mg (g as the task says, often 10); torque M = F·l (perpendicular arm); equilibrium ΣF = 0, ΣM = 0;
"torque in kg·cm" = Σ m·x (no g); centre of mass x_c = Σm_i x_i / Σm_i; friction F ≤ μN;
incline: along it mg sin α, normal mg cos α; tips when the vertical through the CoM leaves the support.

**Dynamics.** F = ma; on an incline up: F_drive = m a + mg(sin α + μ cos α); max drive force of a wheel = μN on
that wheel; balancing robot: a = g tan θ; free fall h = gt²/2; centripetal F = mω²R = mv²/R.

**Rotation and power.** ω = 2πn/60 (n in rpm), v = ωR, ε = a/R; J of a point mass = mL²;
J reduced to the motor = J_load/i²; M = J·ε; work A = F·s, P = F·v = M·ω; efficiency = P_out/P_in;
drag F = ½CₓρAv² (or kv²): terminal speed when drive force = drag; rolling resistance F = μ_roll·mg.

**Gears.** i = z_driven/z_driver = ω_in/ω_out; stages multiply; M_out = M_in·i·η; n_out = n_in/i; idler: direction
only; worm: i = z_wheel/starts; belt: i = D_driven/D_driver; screw: v = lead·n; rack: v = ωr;
wheel force = M_motor·i·η / R_wheel.

**Kinematics.** Differential drive, track B: v = (vR + vL)/2, ω = (vR - vL)/B; turn in place by α: each wheel travels
πBα/360; encoder distance s = πD·ticks/ticks_per_rev; odometry x += d cos θ, y += d sin θ;
2-link arm x = L1 cos t1 + L2 cos(t1 + t2), y = L1 sin t1 + L2 sin(t1 + t2); IK via the law of cosines.

**Vision.** Image size W·H·channels; area ∝ r², mass ∝ r³; line (ρ, θ): x cos θ + y sin θ = ρ;
diagonal raster line pixel count = max(Δx, Δy) + 1 (check the key's convention); pinhole size_px = f·size/distance;
RANSAC: inliers = points closer than a threshold; gray = 0.299R + 0.587G + 0.114B.

**Electrics / MCU (quick pass).** U = IR, series/parallel, divider U·R2/(R1 + R2), P = UI; ADC code = U/U_ref·2ⁿ;
PWM mean = duty·U; battery Wh = V·Ah, t = capacity/I.

**Control.** e = setpoint - measured; P: u = Kp·e; PID: u = Kp·e + Ki·Σe·dt + Kd·Δe/dt.

## Answer-entry rules (transfer errors are not fixed)

Units the task asks for (N·cm, kg·cm, mm, g); "x100" / "x(-1)" last; round only at the end, normally; a small
value may round to 0, and that is a valid answer; re-type the number from the draft, then read it back once.
In the 2025-26 regional paper, some given data was not needed (a distractor).

## Sources

- **Main:** `past/` = 2025-26 regional (conditions) and final (conditions + solutions), from Egor.
- Older technology-olympiad robotics keys (different organiser, more electronics, use only for extra drill):
  [grade 11 regional 2023-24](https://tasks.olimpiada.ru/upload/files/tasks/92/2023/krit-techrobo-11-teor-reg-23-24.pdf),
  [grade 10](https://tasks.olimpiada.ru/upload/files/tasks/92/2023/krit-techrobo-10-teor-reg-23-24.pdf),
  [grade 9 2022-23](https://vos.olimpiada.ru/upload/files/Arhive_tasks/2022-23/reg/tech/ans-techrobo-9-teor-reg-22-23.pdf).
- For physics drill in the same style: past regional physics olympiad mechanics tasks (olimpiada.ru), to be picked per topic.
