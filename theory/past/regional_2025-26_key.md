# Regional 2025-26 theory: our key (Claude, 30 Oct, not official)

Spoiler: do the paper as a 3-hour mock first.

| Task | Answer | Short solution |
|---|---|---|
| 10-01 vision, 2 p | **1** | ω = 0.15 rad x 30 fps = 4.5 rad/s; fall t = √(2h/g) = √(40/10) = 2 s (2.02 with 9.81); angle 9 rad = 1.43 turns -> 1 full turn |
| 10-02 vision, 4 p | **5152** | area2 = π(100² + 201) = π·101² -> r2 = 101 px; m2 = 5·(101/100)³ = 5.1515 kg = 5152 g |
| 10-03 mechanics, 4 p | **36** | F = mg(sin α + μ cos α): 15 = 20(sin α + 0.2 cos α) -> √1.04·sin(α + 11.31°) = 0.75 -> α = 36.0° |
| 10-04 mechanics, 7 p | **87** | M = mgh sin θ = 1.05 N·m; for balance m·a·h·cos θ = m·g·h·sin θ -> a = g tan θ = 0.875 m/s² -> x100 = 87 |
| 10-05 algorithms, 4 p | **17** | n = 5, numbers 15..20, divisors 5..9; min remainders: 15:0, 16:0, 17:1, 18:0, 19:1, 20:0 -> max 1, smallest is 17 |
| 10-06 algorithms, 4 p | **760** | rect i: half-width 20 - i, half-height 1 + i. For i < j, the narrow tall j crosses the wide low i at 4 points; C(20,2) = 190 pairs -> 760 |
| 10-07 control, 4 p | **50** | max speed when k v² = F: v = √(1000/0.1) = 100 m/s; half = 50 |
| 10-08 control, 7 p | **90** | M(m) = m/(m + 10) - 0.001 m; M' = 10/(m + 10)² - 0.001 = 0 -> m + 10 = 100 -> m = 90 |
| 10-09 navigation, 2 p | **300** | Picture: horizontal chord, entry on the outer circle at 30°, so the chord is at height R sin 30° = √3 = 1.732 km < 1.75: it dips into the blind zone for x in [-0.25, 0.25] (√(1.75² - 3) = 0.25). Chord length 2·√(12 - 3) = 6 km. The beam goes clockwise 30° -> 0° -> ... and sweeps the chord's far end (150°) at t = 240/30 = 8 s, then again at 8 + 12 = 20 s. Slow drone: the beam meets it once on the way; it must be in the blind gap then, and it must leave before the next sweep at 20 s -> v ≥ 6 km/20 s = 300 m/s. Check v = 300: they meet at t = 10 s at x = 0 (in the gap). Gap works for 268..334 m/s, so the minimum is 300 |
| 10-10 humanoid, 2 p | **3366** | sum of 40 unit steps turning 0.05 rad: 100·sin(40·0.025)/sin(0.025) = 100·0.84147/0.0249974 = 3366 mm |
| 10-11 aerial, 2 p | **1** | focus = Σ(S·Cy^α·x)/Σ(S·Cy^α) = (0.08·0.91 + 0.008·1.9)/0.088 = 1.00 m |
| 10-12 manipulators, 2 p | **16** | torque in kg·cm = Σ m·x: 0.2·10 + 0.15·35 + 0.05·55 + 0.1·60 = 2 + 5.25 + 2.75 + 6 = 16 |
| 10-13 wheeled, 2 p | **525** | front wheel 15·50 = 750 N·cm / 4 cm = 187.5 N; rear 15·30 = 450 / 6 = 75 N; 4 wheels: 2·187.5 + 2·75 = 525 N (μ is useless without a mass) |
