# Set 01: diagnostic (about 90 min, calculator allowed)

Goal: find what you know, not a score. Skip a task you can't start, write "skip" (that's useful information too).
Give a number + unit for each. Use g = 9.81 m/s^2.

1. **Энкодер / encoder.** Wheel diameter 56 mm, encoder 360 ticks per wheel revolution. The robot drove straight
   for 1000 ticks. Distance in mm, rounded to 0.1?

2. **Момент силы / torque.** A servo holds a light arm horizontally. Servo torque 0.9 N·m, a load hangs at
   150 mm from the axis. Max load mass in kg (0.01), arm mass ignored?

3. **Редуктор / gearbox.** Motor 3000 rpm, 0.05 N·m. Stage 1: gear 12 teeth (on the motor) drives gear 36.
   Stage 2: gear 10 on the same shaft as the 36 drives gear 40. No losses. Output speed (rpm) and output torque (N·m)?

4. **Трение / friction.** Robot of 2 kg, 4 wheels, weight shared equally, only the 2 rear wheels are driven.
   Friction coefficient tyre/floor 0.4. Max acceleration without wheel slip, m/s^2 (0.01)?

5. **Поворот на месте / turn in place.** Differential robot, track (distance between wheel centres) 150 mm,
   wheel diameter 50 mm. It turns 90° in place. How many degrees does each wheel turn?

6. **Манипулятор / 2-link arm.** Link 1 = 100 mm, link 2 = 80 mm. Joint 1 at the origin, angle 30° from the X axis;
   joint 2 is 60° relative to link 1 (same direction). End point (x, y) in mm, 0.1?

7. **Делитель + АЦП / divider + ADC.** Battery 7.4 V -> R1 = 10 kOhm (top) -> pin -> R2 = 4.7 kOhm -> GND.
   12-bit ADC, U_ref = 3.3 V, code = floor(U / U_ref * 4096). Pin voltage (V, 0.001) and ADC code?

8. **ШИМ / PWM.** Motor driver from a 12 V supply, 8-bit PWM (0..255). Which PWM value gives a mean of 9 V
   (round down)?

9. **Биты / bits.** x = 0b10110110. Compute (x & 0x3C) >> 2 in decimal.

10. **П-регулятор / P controller.** Line follower: target sensor value 50, current reading 35, Kp = 2,
    base speed 40. u = Kp·(target - reading); left = base + u, right = base - u. Left and right speeds?

11. **Гироскоп / gyro.** A gyro has a constant bias of 0.5 °/s, the robot stands still and integrates the gyro for
    2 minutes. Heading error in degrees?

12. **Изображение / image.** Grayscale 5x5 image (row 0 on top, column 0 on the left):

    ```
    10  20 200 210  15
    12 220 230 240  18
     9 205 250 215  11
    14  16 190  20  13
     8  10  12  11   9
    ```

    Object = pixels with brightness > 180. (a) object area in pixels, (b) centroid (column, row) to 0.01,
    (c) bounding-box width x height in pixels.

13. **Код / code (optional, 15 min).** Input: N, then N integers (encoder ticks every 10 ms). Output the largest
    absolute change between two neighbouring readings. Python or C++. Example: `5` / `0 3 10 8 20` -> `12`.
