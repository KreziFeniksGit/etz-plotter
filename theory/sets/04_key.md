# Set 04 key (spoiler, for checking)

1. **3**: a = 0.6/0.4 = 1.5 m/s², F = 2·1.5 = 3 N
2. **300**: F = 0.5·(0.6·4·10) = 12 N, a = 12/4 = 3 m/s² = 300 cm/s² (trap: full weight -> 500)
3. **213**: a = g·tan 12° = 2.126 m/s²
4. **220**: motors 4·0.02·30·0.8/0.03 = 64 N, grip 0.4·1.5·10·cos 10° = 5.91 N -> the smaller, 5.91 N;
   a = (5.91 - 15·sin 10°)/1.5 = (5.91 - 2.60)/1.5 = 2.20 m/s² (trap: 64 N -> motors are not the limit)
5. **429**: moments about the front contact: N_rear·20 = m·g·10 + m·a·10 -> N_rear = m(5 + 0.5a);
   m·a = 0.6·N_rear -> a = 3 + 0.3a -> a = 4.286 m/s². Front N = m(5 - 0.5a) = m·2.86 > 0, stays down.
   Mass does not matter (distractor). Without weight transfer it would be 300.
A. p[r] - p[l-1]; sample 10, 2, 3. Fast input (sys.stdin), one print.
B. window sums p[i+k-1] - p[i-1], strict < to keep the smallest index; sample 4 (3+4+2 = 9).
C. 2D prefix, count windows with sum 0; sample 5. (n-k+1)(m-k+1) windows x 4 operations.
