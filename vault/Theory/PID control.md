---
tags: [theory]
updated: 2026-11-06
---
# PID control

Open loop vs closed loop; setpoint, error e; P: u = Kp·e; PID adds ∫e (removes steady error) and de/dt (damps);
too much gain -> oscillation. On the practical round's line follower this is the core.
Plotter link: our axes are open loop ([[No encoders]]); the battery guard uses hysteresis (on < 14.0, off > 15.1) - [[Battery guard]].
Related: [[Optimisation and terminal speed]], [[Theory Prep]].
