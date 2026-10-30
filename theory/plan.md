# Theory round plan (VsOSh informatics, Robotics profile, regional, grade 11)

Exam: **Sat 24 Jan 2027**, day 2, 240 min, **45 of 100 points**. 8-10 tasks: 6-8 calculation/analysis
(answer typed into the system, no live check, a typo is NOT fixed) + 2 programming (C++/Python, auto-tested,
results shown live). Engineering calculator allowed (not programmable). Source: `vsosh_robotics_regional_2026-27.txt`
section 5 and Приложение 1 (topics).

Egor's input (30 Oct): electrics fairly strong (not 100%), **mechanics weak**, 7+ h/week,
wants short explanations + daily problem sets + mock tests.

## Ranking: where the points are

Points per task are not published. Past regional theory papers (technology olympiad, robotics profile, 2022-24;
links below) mix 0.5-2 point items. Most of them need mechanics, gears, kinematics, dividers + ADC, and geometry.
Priority = likely points x weakness:

| # | Area (Приложение 1 sections) | Likely weight | Egor | Priority |
|---|---|---|---|---|
| 1 | Mechanics, gears, actuators (2, 3, 10) | high | weak | **top** |
| 2 | Robot kinematics, odometry, manipulators (4, 13) | high | ? | **top** |
| 3 | Programming tasks (11): 2 of the 8-10 tasks | high | ? | high, every week |
| 4 | Sensors, error, filtering; control P/PID (9, 12) | medium | ? | high |
| 5 | Maths basics: trig, vectors, units (1) | under everything | ? | high, inside other topics |
| 6 | Electrics, electronics, MCU: ADC/PWM/I2C (5, 6, 8) | medium-high | strong-ish | medium: polish |
| 7 | Digital logic, number systems, bits (7) | medium | ? | medium |
| 8 | Vision + AI basics (14, 15) | medium | ? | medium |

Doubt: Egor did not pick coding practice, but 2 tasks are programming, scored on tests, maybe 10-15 of the 45 points.
Plan keeps one coding task a week, plus two in every mock.

## Week plan (about 1 h a day)

| Week | Dates | Topics | Mock |
|---|---|---|---|
| 1 | 30 Oct - 5 Nov | Diagnostic set; units, trig, vectors; force, torque, levers, equilibrium | |
| 2 | 6 - 12 Nov | Friction, centre of mass, tipping; work, power, energy; gears, belts, worm, screw/rack | |
| 3 | 13 - 19 Nov | DC motor (torque-speed line), servo, stepper; choosing a motor + gearbox | |
| 4 | 20 - 26 Nov | Wheeled robot kinematics (differential drive, turns, arcs), odometry; 2-link arm FK/IK | Mini mock (2 h) |
| 5 | 27 Nov - 3 Dec | Electrics polish: dividers, power, batteries mAh/Wh, runtime; RC, diode, transistor switch | |
| 6 | 4 - 10 Dec | Number systems, bitwise ops, logic, truth tables; MCU: ADC, PWM, UART/I2C/SPI | |
| 7 | 11 - 17 Dec | Sensors: encoders, gyro/accel, error, calibration, filters (mean, median, exponential) | **Mock 1 (240 min)** |
| 8 | 18 - 24 Dec | Control: open/closed loop, P, PI, PID (discrete), line follower, tuning, stability | |
| 9 | 25 - 31 Dec | Navigation: maze rules, grid maps, BFS/Dijkstra/A*; algorithms, complexity, state machines | |
| 10 | 1 - 7 Jan | Vision + AI: pixels, RGB/HSV/gray, threshold, centroid, bbox, lines, pinhole camera, detection errors | **Mock 2** |
| 11 | 8 - 14 Jan | Repair the worst error types from `progress.md`; coding speed | **Mock 3** |
| 12 | 15 - 23 Jan | Mock 4 early in the week, then light review of the formula sheet only | **Mock 4** |

Daily session: 10 min explanation + worked example, 35-45 min problems (3-5), 5 min check and log errors.

## Formula sheet (must know without looking)

**Maths.** sin/cos/tan of 30/45/60; law of cosines c^2 = a^2 + b^2 - 2ab cos C; law of sines;
arc s = R*phi (phi in rad); rad = deg*pi/180; vector length, dot product, rotation
x' = x cos a - y sin a, y' = x sin a + y cos a; atan2; relative error = |dx|/x.

**Mechanics.** F = m a; weight G = m g (g = 9.81 unless the task says 10); torque M = F * l (arm = perpendicular
distance); equilibrium: sum F = 0 and sum M = 0; friction F <= mu N; centre of mass x_c = sum(m_i x_i)/sum(m_i);
tips over when the vertical through the centre of mass leaves the support area; work A = F s cos a;
power P = A/t = F v = M w; w = 2 pi n/60 (n in rpm); kinetic energy m v^2/2; potential m g h; efficiency = P_out/P_in.

**Gears (передачи).** ratio i = z_driven/z_driver = w_in/w_out; chain of stages: i = i1*i2*...;
torque M_out = M_in * i * efficiency; speed n_out = n_in / i; idler gear does not change i, only the direction;
worm: i = z_wheel/number of worm starts; belt: i = D_driven/D_driver; screw: v = lead * n; rack: v = w * r.

**Actuators.** DC motor: speed falls linearly with load, n = n0 (1 - M/M_stall); max power at half the stall
torque; I rises with load; reverse = H-bridge; speed = PWM. Servo: 50 Hz, 1-2 ms pulse (about 0.5-2.5 ms for 180 deg).
Stepper: steps/rev = 360/step angle (1.8 deg -> 200), x microstep; linear: mm/step = lead / (200*microstep).

**Kinematics.** Differential drive, track (колея) B, wheel speeds vL, vR: v = (vR + vL)/2,
w = (vR - vL)/B, R = B/2 * (vR + vL)/(vR - vL). Turn in place by angle a: each wheel travels pi*B*a/360, opposite
directions. Distance from encoder: s = pi*D*ticks/ticks_per_rev. Odometry step:
x += d cos th, y += d sin th, th += dth. 2-link arm: x = L1 cos t1 + L2 cos(t1 + t2), y = L1 sin t1 + L2 sin(t1 + t2).

**Electrics.** U = I R; series R = R1 + R2; parallel 1/R = 1/R1 + 1/R2; divider U_out = U R2/(R1 + R2);
P = U I = I^2 R = U^2/R; battery: Wh = V * Ah, runtime t = capacity/current; LED resistor R = (U - U_led)/I;
RC time constant tau = R C (63 % after tau, about 99 % after 5 tau); Kirchhoff current/voltage laws.

**MCU.** ADC code = U/U_ref * 2^n (watch 2^n vs 2^n - 1: read the task!); U = code * U_ref / 2^n;
PWM duty = t_on/T, mean voltage = duty * U; UART time per byte = 10 bits/baud; I2C = SDA + SCL, addresses, pull-ups;
SPI = MOSI/MISO/SCK/CS.

**Logic.** Conversions 2/8/10/16; AND OR NOT XOR, shifts (<< 1 = x2); masks: set |, clear & ~, test &;
De Morgan; truth table -> sum of products.

**Sensors.** Resolution = range/2^n; calibration y = (x - x_min)/(x_max - x_min) * scale;
gyro angle = sum(w * dt), a bias b gives drift b*t; mean of N, median, exponential y = a x + (1 - a) y;
absolute and relative error; ultrasonic distance = v_sound * t / 2.

**Control.** e = setpoint - measured; P: u = Kp e; PID: u = Kp e + Ki sum(e dt) + Kd (e - e_prev)/dt;
too big Kp -> oscillation; I removes the steady-state error; D damps.

**Vision.** Gray = 0.299 R + 0.587 G + 0.114 B (or the plain average, if the task says so); image size bytes = W*H*channels;
threshold -> mask; area = pixel count; centroid = mean of x and y; pinhole: size_px = f * size / distance;
precision = TP/(TP+FP), recall = TP/(TP+FN).

## Answer-entry rules (transfer errors are not fixed)

Units the task asks for (mm vs m, rpm vs rad/s); rounding exactly as asked; decimal point vs comma as the system
wants; re-type the number from the draft, then read it back once.

## Sources for past tasks

- Regional theory key, technology/robotics grade 11, 2023-24: https://tasks.olimpiada.ru/upload/files/tasks/92/2023/krit-techrobo-11-teor-reg-23-24.pdf
- Grade 10, same year: https://tasks.olimpiada.ru/upload/files/tasks/92/2023/krit-techrobo-10-teor-reg-23-24.pdf
- Regional key grade 9, 2022-23: https://vos.olimpiada.ru/upload/files/Arhive_tasks/2022-23/reg/tech/ans-techrobo-9-teor-reg-22-23.pdf
- Moscow robotics olympiad final, theory grades 10-11, 2023-24: https://mos.olimpiada.ru/upload/files/Archive_tasks_2013-.../2023-24/robo/ans-robo-10-11-teor-final-23-24.pdf
- Municipal 10-11, Nizhny Novgorod, 2023-24: https://tasks.olimpiada.ru/upload/files/tasks/92/2023/tasks-tech-10-11-teor-robo-mun-nn-23-24.pdf
- MCKO teacher guide on robotics theory: https://im.mcko.ru/docs/2022/mr/ИТ_Робототехника_теория_методрекомендации.pdf
- Archive search: tasks.olimpiada.ru, subject 92 (technology), files with "teor robo".

Note: those are the old technology olympiad (robotics profile). The informatics-robotics profile is new, but its topic
list covers the same ground, and the 2023-24 grade 11 key has a divider + 12-bit ADC task, a robot-turn task
and a geometry task.
