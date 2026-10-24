// ETZ plotter - bench test firmware: three steppers (X, Y, wrist) through TMC2209 drivers.
// Type commands in the PlatformIO serial monitor (115200). "help" lists them.
// Wi-Fi and Bluetooth are never started (competition rule): no WiFi / BLE code anywhere.
#include <Arduino.h>
#include <TMCStepper.h>
#include <AccelStepper.h>
#include "pins.h"

// ---------------------------------------------------------------- settings
constexpr float R_SENSE = 0.11f;          // BIGTREETECH TMC2209 V1.3 sense resistor (ohm)
constexpr uint16_t MICROSTEPS = 16;
constexpr int STEPS_PER_REV = 200 * MICROSTEPS;   // 1.8 deg motors

struct Axis {
  const char *name;
  uint8_t addr;            // UART address set by MS1/MS2 on the driver board: X 0, Y 2, wrist 3
  int step, dir;
  uint16_t mA;             // RMS current (wiring.md section 4)
  bool invert;             // motor plug order 2B 2A 1A 1B may reverse a motor: flip with "dir"
  TMC2209Stepper *drv;
  AccelStepper *mot;
};

HardwareSerial &TMC_SERIAL = Serial2;
TMC2209Stepper drvX(&TMC_SERIAL, R_SENSE, 0), drvY(&TMC_SERIAL, R_SENSE, 2), drvW(&TMC_SERIAL, R_SENSE, 3);
AccelStepper motX(AccelStepper::DRIVER, PIN_X_STEP, PIN_X_DIR);
AccelStepper motY(AccelStepper::DRIVER, PIN_Y_STEP, PIN_Y_DIR);
AccelStepper motW(AccelStepper::DRIVER, PIN_W_STEP, PIN_W_DIR);

Axis axes[3] = {
  {"x", 0, PIN_X_STEP, PIN_X_DIR, 900, false, &drvX, &motX},
  {"y", 2, PIN_Y_STEP, PIN_Y_DIR, 900, false, &drvY, &motY},
  {"w", 3, PIN_W_STEP, PIN_W_DIR, 600, false, &drvW, &motW},
};

float maxSpeed = 3200;     // steps/s (1 rev/s at 16 microsteps)
float accel = 6400;        // steps/s^2

// ---------------------------------------------------------------- driver setup / check
bool setupDriver(Axis &a) {
  TMC2209Stepper &d = *a.drv;
  d.begin();
  d.pdn_disable(true);       // PDN_UART pin is the UART, not power-down
  d.I_scale_analog(false);   // current from the register, not the board's pot
  d.mstep_reg_select(true);  // microsteps from the register, not MS1/MS2 (those set the address)
  d.toff(4);                 // driver on
  d.blank_time(24);
  d.rms_current(a.mA);
  d.microsteps(MICROSTEPS);
  d.en_spreadCycle(false);   // StealthChop: quiet
  d.pwm_autoscale(true);
  uint8_t v = d.version();   // 0x21 = TMC2209 answered
  return v == 0x21;
}

void printStatus(Axis &a) {
  TMC2209Stepper &d = *a.drv;
  uint8_t v = d.version();
  Serial.printf("[%s] addr %u  version 0x%02X %s", a.name, a.addr, v, v == 0x21 ? "OK" : "NO ANSWER");
  if (v == 0x21) {
    uint32_t ds = d.DRV_STATUS();
    Serial.printf("  current %u mA  usteps %u  on %s  %s%s%s%s",
                  d.rms_current(), d.microsteps(), d.toff() ? "yes" : "no",
                  (ds & (1UL << 1)) ? "OVERTEMP " : "", (ds & (1UL << 0)) ? "PRE-WARN " : "",
                  (ds & (3UL << 2)) ? "SHORT-GND " : "", (ds & (3UL << 6)) ? "OPEN-LOAD " : "");
  }
  Serial.printf("  pos %ld\n", a.mot->currentPosition());
}

Axis *findAxis(const String &s) {
  for (auto &a : axes) if (s == a.name) return &a;
  return nullptr;
}

// ---------------------------------------------------------------- commands
void help() {
  Serial.println(F(
    "\nCommands (axis = x, y or w):\n"
    "  status              driver answers over UART? current, flags, position\n"
    "  m <axis> <steps>    move relative, 3200 steps = 1 turn (16 microsteps)\n"
    "  r <axis> <turns>    move relative in turns (can be 0.5, -2 ...)\n"
    "  test                each motor: 1 turn forward, 1 back, one after another\n"
    "  all <turns>         all three motors at once\n"
    "  speed <steps/s>     max speed (now shown by 'status'); accel <steps/s^2>\n"
    "  cur <axis> <mA>     RMS current (X/Y 900, wrist 600 by default; max ~1500)\n"
    "  on <axis> / off <axis>   driver output on / off (off = motor turns freely)\n"
    "  dir <axis>          reverse this motor's direction\n"
    "  stop                stop all motors (decelerate)\n"));
}

void startMove(Axis &a, long steps) {
  a.mot->move(a.invert ? -steps : steps);
}

void command(String line) {
  line.trim(); line.toLowerCase();
  if (!line.length()) return;
  int sp1 = line.indexOf(' ');
  String cmd = sp1 < 0 ? line : line.substring(0, sp1);
  String rest = sp1 < 0 ? "" : line.substring(sp1 + 1); rest.trim();
  int sp2 = rest.indexOf(' ');
  String arg1 = sp2 < 0 ? rest : rest.substring(0, sp2);
  String arg2 = sp2 < 0 ? "" : rest.substring(sp2 + 1); arg2.trim();

  if (cmd == "help" || cmd == "?") { help(); return; }
  if (cmd == "status") {
    Serial.printf("speed %.0f steps/s, accel %.0f steps/s^2\n", maxSpeed, accel);
    for (auto &a : axes) printStatus(a);
    return;
  }
  if (cmd == "stop") { for (auto &a : axes) a.mot->stop(); Serial.println("stopping"); return; }
  if (cmd == "speed") { maxSpeed = arg1.toFloat(); for (auto &a : axes) a.mot->setMaxSpeed(maxSpeed); Serial.printf("speed %.0f\n", maxSpeed); return; }
  if (cmd == "accel") { accel = arg1.toFloat(); for (auto &a : axes) a.mot->setAcceleration(accel); Serial.printf("accel %.0f\n", accel); return; }
  if (cmd == "test") {
    for (auto &a : axes) {
      Serial.printf("[%s] 1 turn forward, 1 back\n", a.name);
      startMove(a, STEPS_PER_REV);  while (a.mot->distanceToGo()) a.mot->run();
      delay(300);
      startMove(a, -STEPS_PER_REV); while (a.mot->distanceToGo()) a.mot->run();
      delay(300);
    }
    Serial.println("test done");
    return;
  }
  if (cmd == "all") { long s = lround(arg1.toFloat() * STEPS_PER_REV); for (auto &a : axes) startMove(a, s); return; }

  Axis *a = findAxis(arg1);
  if (!a) { Serial.println("unknown command or axis - type help"); return; }
  if (cmd == "m")   { startMove(*a, arg2.toInt()); return; }
  if (cmd == "r")   { startMove(*a, lround(arg2.toFloat() * STEPS_PER_REV)); return; }
  if (cmd == "cur") { uint16_t mA = constrain(arg2.toInt(), 100, 1500); a->mA = mA; a->drv->rms_current(mA); Serial.printf("[%s] %u mA\n", a->name, mA); return; }
  if (cmd == "on")  { a->drv->toff(4); Serial.printf("[%s] on\n", a->name); return; }
  if (cmd == "off") { a->drv->toff(0); Serial.printf("[%s] off (free)\n", a->name); return; }
  if (cmd == "dir") { a->invert = !a->invert; Serial.printf("[%s] direction %s\n", a->name, a->invert ? "reversed" : "normal"); return; }
  Serial.println("unknown command - type help");
}

// ---------------------------------------------------------------- main
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println(F("\nETZ plotter bench test (X, Y, wrist). Radio is never started."));
  TMC_SERIAL.begin(115200, SERIAL_8N1, PIN_TMC_RX, PIN_TMC_TX);
  delay(50);
  for (auto &a : axes) {
    bool ok = setupDriver(a);
    a.mot->setMaxSpeed(maxSpeed);
    a.mot->setAcceleration(accel);
    Serial.printf("[%s] UART address %u: %s\n", a.name, a.addr,
                  ok ? "driver answered, configured" : "NO ANSWER (is the battery / drive power on? cable? address?)");
  }
  help();
}

// Line editor: the ESP32 echoes what you type, Backspace erases, Enter runs the command.
String buf;
void readConsole() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r' || c == '\n') {
      if (c == '\n' && !buf.length()) continue;      // the \n after a \r
      Serial.print("\r\n");
      if (buf.length()) command(buf);
      buf = "";
      Serial.print("> ");
    } else if (c == '\b' || c == 0x7f) {              // Backspace / Delete
      if (buf.length()) { buf.remove(buf.length() - 1); Serial.print("\b \b"); }
    } else if (c == 0x1b) {                           // arrow keys etc. send ESC [ x: ignore them
      while (!Serial.available()) {}
      if (Serial.read() == '[') { while (!Serial.available()) {} Serial.read(); }
    } else if (isprint((unsigned char)c) && buf.length() < 80) {
      buf += c; Serial.write(c);
    }
  }
}

void loop() {
  for (auto &a : axes) a.mot->run();          // step pulses (keep loop() fast)
  readConsole();
}
