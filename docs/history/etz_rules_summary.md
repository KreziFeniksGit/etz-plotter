# ETZ 2026-27 rules: what matters for the design

Source: the short version of the unified technical task (VsOSh informatics, robotics profile), prepared 02.10.2026 from the 01.10.26 full text. The full version applies if they differ. This is my paraphrase of the Russian text, grade 11 final.

## Task
- The device finds checkers on a 250 x 330 mm operating field, picks them up, moves them and places them in the cells given by the task. Task number and parameters are entered before start.
- Final stage (grade 11) adds: colour detection, reading ArUco / AprilTag / QR on the stickers, stacking up to 5 checkers, taking the top checker from a stack, recognising pictures on stickers, rotating the held checker by any angle 0 to 360 degrees.
- Checker: 26 mm diameter, 5 mm high, 0.8 mm lid, steel M8 washer inside, about 7 g, lid up. Colours red, green, blue, yellow, magenta (others possible). Any gripping method allowed.
- Field: A4 sheet, grid 9 x 6 cells of 28 mm, buffer column, three ArUco marks (DICT_4X4_50, ids 27, 28, 29, 18 mm). Origin is the centre of mark 27.
- Placement tolerance: checker centre within 10 mm of the cell centre. Manipulator speed at least 100 mm/s.

## Footprint (grades 10 and 11)
- Polygon 600 x 500 mm. Zone 1 is 350 x 500 mm, zone 2 is two strips of 250 x 80 mm.
- The device may rest only on zone 1, free standing on its own weight. Before and after the run its projection must lie inside zones 1 and 2 (parts may be above zone 2). During the run parts may leave the polygon, but only the gripper and the held checker may touch the field.
- Height is unlimited. Edges rounded, base clean (no glue or smudging coatings), all wires fixed.

## Electronics and control
- Drives powered from batteries on the device only, nominal voltage at most 16 V. No mains adapters. Microcontrollers, cameras and sensors may be powered from the laptop over USB.
- Stop button (latching) must cut power to all drives. Green LED = drives powered. Red LED = program running (starts after the task number is entered, goes out at the finish). Start button on the device is the only action allowed while red is on.
- Control system must be your own, on general purpose boards (ATmega, STM32, RP2040 and similar, or a single board computer, or the laptop).
- Forbidden: 3D printer and CNC boards (RAMPS, MKS, SKR and so on) with any firmware; GRBL, Marlin, Klipper, Mach3, LinuxCNC; G-code control; ready-made arms with their own controller.
- Allowed: driver modules (A4988, DRV8825, TMC2208, L298N, DRV8833), PCA9685, servos, general libraries (Servo, AccelStepper, OpenCV) if the solving algorithms are your own.
- Laptop link only by wire (also during the run), laptop fully offline, Wi-Fi and Bluetooth off on every controller, computer and laptop.
- Connectors on the body at 2.54 mm pitch: A analog (SIG, V, GND), B digital (SIG, V, GND, 5 V tolerant), C UART 9600 8-N-1 (TX, RX, V = 5 V +/-5 % at 200 mA or more, GND). A fixed solderless breadboard next to them: at least 170 contacts (regional), at least 400 (final).

## Consequences for our design (found 10 Oct)
- The tolerance of 10 mm is much looser than our accuracy budget (5.5 mm worst case as built, 1.6 mm calibrated). Encoders and heavy calibration are not needed to meet it.
- Homing: the device starts every run parked in the placement zone, so a mechanical park pose with stops or switches is enough.
- The wrist (rotation of the held checker 0 to 360 degrees) is needed for the final, so keep it.
- Z stroke needed is only about 40 to 50 mm (stack of 5 is 25 mm). Tr8x2 at 10 to 15 mm/s may be too slow against the 100 mm/s manipulator speed. Check against the full text.
- Missing from the plan: Start button, red and green LEDs, latching stop button, connectors A, B, C, breadboard with 400 contacts, rounded edges, clean base. GRBL / G-code ideas are banned.
- ESP32-S3 has radio hardware. It is allowed only if Wi-Fi and Bluetooth are off. Ask the organisers, or use an RP2040 or STM32.
- Plan items about a bench supply apply to development only: at the competition the supply must be batteries.
