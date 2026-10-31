# Set 02: torque, lever arms, tipping (week 1)

## 10-minute theory

**Torque / момент силы:** M = F · d, where d (плечо) = the **perpendicular** distance from the axis to the line of the force.

- Gravity is vertical, so its arm is the **horizontal** distance from the axis to the centre of mass.
- A horizontal force (inertia, a push) has a **vertical** arm.
- A link raised by angle α: horizontal arm = L·cos α (so the torque is biggest when the link is horizontal).

**Equilibrium / равновесие:** ΣF = 0 and ΣM = 0 about **any** point. Pick the point where the unknown force acts,
so it drops out.

**Tipping / опрокидывание:** the body pivots about the **edge** of its support (the front wheel, for example).
It tips when the torque that tips it about that edge > the torque that holds it.

**"Torque in kg·cm"** = Σ m·x (mass x arm, no g). 1 kg·cm ≈ 0.098 N·m (with g = 10: 0.1 N·m).

**Units habit:** write the unit on every line.

Example: a servo holds a horizontal link 20 cm long, 100 g, with a 50 g load at the end.
M = 0.1·10 + 0.05·20 = 2 kg·cm (= 0.2 N·m with g = 10).

## Problems (g = 10 m/s², answers rounded to integers, about 60 min)

1. **(2 p)** A servo holds a straight link 25 cm long, mass 120 g (centre of mass in the middle), with a gripper + part
   of 80 g at the end. The link is raised **30° above the horizontal** and is not moving. Holding torque in **N·cm**?

2. **(2 p)** A gripper finger is a lever. The servo rod pushes it with 6 N at 2 cm from the pivot; the fingertip is 5 cm
   from the pivot on the other side. Two such fingers squeeze a part from both sides, friction coefficient 0.5.
   What is the largest part mass in **grams** that the gripper can hold (vertical fingers, part hangs between them)?

3. **(4 p)** A mobile manipulator. Wheels touch the floor at x = 0 and x = 20 cm. The base (3 kg) has its centre of
   mass at x = 10 cm. A mast stands at x = 15 cm; a horizontal arm (0.5 kg, centre of mass 15 cm from the mast)
   points forward (+x). A 1 kg load hangs at the end of the arm, at distance L from the mast. Max L in **cm**
   before the robot tips over the front wheel?

4. **(4 p)** A 2 kg wheeled robot drives **up** a 20° slope at constant speed. Two driven wheels, diameter 6 cm, each
   with its own motor through a gearbox i = 30, efficiency 0.8. Rolling resistance is negligible. Torque needed
   on **one motor shaft**, in **N·mm**?

5. **(7 p)** A balancing two-wheeled robot: mass 4 kg (point mass at the centre of mass), centre of mass 0.3 m above
   the wheel axle, wheel radius 5 cm. Each of the 2 wheel motors gives up to 0.6 N·m at the wheel. Friction
   coefficient wheel/floor 0.5. What is the largest tilt from the vertical, in **degrees**, at which the robot can
   still stop the fall (hold the angle)?

6. **(optional, code, 15 min)** Write a program for regional task 10-05 for any n: input n, output the number from
   3n to 4n whose smallest remainder (divisors n + 0 .. n + (n - 1)) is the largest (smallest such number on ties).
   Check: n = 5 -> 17. Then run n = 7 and n = 100 and send me the outputs.
