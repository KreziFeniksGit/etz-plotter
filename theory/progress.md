# Theory prep progress

## Sessions

| Date | Set | Topics | Score | Notes |
|---|---|---|---|---|
| 30 Oct | `sets/01_diagnostic.md` | mixed basics (made before seeing the real papers; optional warm-up now) | - | given |
| 31 Oct | `sets/02_torque.md` 1-5 | torque, lever, tipping, motor -> gearbox -> wheel, traction limit | 1, 2 right; 3, 4, 5 with hints (5 solved himself after the step order) | 3: g on one side only, arm from the wrong point (mast, not wheel), divided instead of subtracting; 4: gearbox upside down (M/(i·η)), forgot 2 wheels, then diameter instead of radius; 5: M·r instead of M/r, thought 2 motors and μ cancel, equated motor torque to gravity torque; understood: two separate limits, take the smaller |
| 31 Oct | `sets/03_mechanics.md` | mechanics without hints + 2D prefix sums | **10 / 23** (2, 3, 5 right; 1, 4, 6 wrong; 5, 6 after hints) | 1: sin 60° instead of cos 60° (12, key 7); 4: 162 = 180 − 18, subtracted friction instead of taking the min (key 18); 5: did not know rolling resistance, then 202 ✓; 6: forgot masses in the inertial force, then answer in m/s² (key 529 cm/s²); 7: naive code correct on the sample, but 20 full-grid queries = 2.7 s, 10^5 queries far too slow -> prefix sums explained |
| 31 Oct | Mock 0 = `past/regional_2025-26_tasks.pdf` | full regional paper | **21 / 40** (02, 03, 07, 08, 12 right; 01, 04, 05, 06, 09 wrong) | 59 min for 01-08: fast. Most losses = reading / units, real gap = 04 |

### Mock 0 details

| Task | Egor | Key | Pts | Time | What went wrong |
|---|---|---|---|---|---|
| 01 vision | 18 | 1 | 0/2 | 2 min | got 4.5 rad/s x 2 s = 9 rad, then an extra x2 "for no reason", and never converted rad -> turns (9/(2π) = 1.43 -> 1). Fix: write units on every line |
| 02 vision | 5152 | 5152 | 4/4 | 3 min | - |
| 03 mechanics | 36 | 36 | 4/4 | 10 min | right equation, solved by trial; learn a·sin x + b·cos x = √(a² + b²)·sin(x + φ) |
| 04 mechanics | 26 | 87 | 0/7 | 6 min | arm of gravity is h·sin θ, not h·cos θ; set torque equal to force (F = M); missing: inertial force m·a at the CoM with arm h·cos θ -> a = g tan θ |
| 05 algorithms | 15 | 17 | 0/4 | 6 min | method right; misread the numbering: robots are 0th..4th ("0-й, 1-й"), divisors 5..9. He used 1..5 (divisors 6..10), and with that reading 15 would be right |
| 06 algorithms | 840 | 760 | 0/4 | 12 min | off by one: widths 40, 38 .. 2 = 20 rectangles, not 21 (4·C(21,2) = 840) |
| 07 control | 50 | 50 | 4/4 | 9 min | guessed; idea = terminal speed when drive force = drag |
| 08 control | 90 | 90 | 7/7 | 11 min | - |
| 12 manipulators (specialised) | 16 | 16 | 2/2 | - | - |
| 09 navigation | 29, then 15 | 300 | 0/2 | - | first misread: beam starts ON the drone (30° = entry point); with hints the reasoning was right (600° -> 20 s, meet at M in the blind gap), then 6000 m / 20 s = 300 m/s divided by 20 again (units slip) |

## Error types (count, update after each set)

| Type | Count | Example |
|---|---|---|
| Units / what is asked (turns vs rad, etc.) | 2 | Mock 0 / 01, set 03 / 6 (m/s² instead of cm/s²) |
| sin vs cos (angle above horizon: arm = L cos α) | 1 | set 03 / 1 |
| Limits: subtracted instead of taking the min | 1 | set 03 / 4 |
| Inertial force without the mass (m·a) | 1 | set 03 / 6 |
| Code too slow (no operation count before writing) | 1 | set 03 / 7 |
| Rounding / answer entry | 0 | |
| Formula not known (method) | 2 | 03 a sin + b cos (solved anyway), 07 terminal speed |
| Wrong model (geometry of forces, torque vs force) | 1 | 04 |
| Misread the condition (indexing from 0) | 1 | 05 |
| Counting off by one | 1 | 06 (summed 4·(1..20) instead of 4·(0..19)) |
| Careless step (extra factor / no units written) | 2 | 01 (x2 for no reason), 09 (/20 twice) |
| Diameter vs radius | 1 | set 02 / 4 |
| Lever arm from the wrong point | 1 | set 02 / 3 (mast instead of wheel) |
| Gearbox direction (i multiplies torque) | 1 | set 02 / 4 |
| Mixing limits into one formula (μ x motor torque) | 2 | set 02 / 5, set 03 / 4 |
| Arithmetic | 0 | |

## Topic status

Not seen / seen / ok / solid.

| Topic | Status |
|---|---|
| Statics, torque arm | **weak** (04) |
| Incline + friction | ok (03, method by trial) |
| Dynamics, inertial force, balancing | **weak** (04) |
| Drag, terminal speed | seen (07, guessed) |
| Optimisation with derivatives | ok (08) |
| Scaling laws (area, mass) | ok (02) |
| Rotation, rad vs turns | **weak** (01) |
| Algorithm puzzles: reading min/max | **weak** (05) |
| Counting (fenceposts, pairs) | **weak** (06) |
| Geometry / navigation | not seen yet (09) |
| Vision geometry (Hough, RANSAC) | not seen |
| Electrics, MCU, logic | not seen (low priority) |
| Programming tasks | seen (correct logic; speed / prefix sums not yet) |
