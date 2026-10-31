# Set 03 key (spoiler, for checking)

1. **7**: cos 60° · (0.3·20 + 0.2·40) = 0.5 · 14 = 7 kg·cm
2. **42**: v = π·D·n/60 = π·4·200/60 = 41.9 cm/s (trap: diameter, rpm -> per second)
3. **34**: tips back when the vertical through the CoM passes the rear axle: tan α = (20/2)/15 -> 33.7°
4. **18**: motors 4·0.15·20·0.75/0.05 = 180 N, friction 0.6·3·10 = 18 N -> the smaller, 18 N
5. **202**: a = (12 - 25 sin 15° - 0.02·25 cos 15°)/2.5 = (12 - 6.47 - 0.48)/2.5 = 2.019 m/s² -> 202 cm/s²
6. **529**: moments about the front wheel (x = 20, floor), braking -> inertial forces forward:
   holding 5·10·10 = 500 N·cm; tipping: load weight 1·10·5 = 50, inertia 5·a·8 + 1·a·45 = 85a
   -> 500 = 50 + 85a -> a = 5.294 m/s² = 529 cm/s²
7. 2D prefix sums: P[i][j] = sum of the top-left i x j block; rectangle = P[r2][c2] - P[r1-1][c2] - P[r2][c1-1] + P[r1-1][c1-1];
   mean = sum // area. Naive worst case 10^5 · 10^6 = 10^11 operations: too slow. Prefix: 10^6 + 4·10^5. Sample -> 3, 9.
   In Python read input fast (sys.stdin).
