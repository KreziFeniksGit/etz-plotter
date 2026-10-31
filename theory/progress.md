# Theory prep progress

## Sessions

| Date | Set | Topics | Score | Notes |
|---|---|---|---|---|
| 30 Oct | `sets/01_diagnostic.md` | mixed basics (made before seeing the real papers; optional warm-up now) | - | given |
| 31 Oct | Mock 0 = `past/regional_2025-26_tasks.pdf`, tasks 01-08 | regional paper, part 1 | **19 / 33** (02, 03, 07, 08 right; 01, 04, 05, 06 wrong) | 59 min for 8 tasks: fast. 09 + one specialised still to do |

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

## Error types (count, update after each set)

| Type | Count | Example |
|---|---|---|
| Units / what is asked (turns vs rad, etc.) | 1 | Mock 0 / 01 |
| Rounding / answer entry | 0 | |
| Formula not known (method) | 2 | 03 a sin + b cos (solved anyway), 07 terminal speed |
| Wrong model (geometry of forces, torque vs force) | 1 | 04 |
| Misread the condition (indexing from 0) | 1 | 05 |
| Counting off by one | 1 | 06 (summed 4·(1..20) instead of 4·(0..19)) |
| Careless step (extra factor) | 1 | 01 (x2 for no reason) |
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
| Programming tasks | not seen |
