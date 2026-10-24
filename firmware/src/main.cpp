// ETZ plotter firmware v2 - three steppers (X, Y, wrist) through TMC2209 drivers, for the bench and the laptop app.
//  - typed console (echo, Backspace) for a person; "echo 0" + "stream <ms>" + "json" for the laptop program
//  - step pulses from the ESP32's hardware (FastAccelStepper): UART reads of the drivers cannot disturb the motion
//  - watchdog: with "wd <ms>" set, the motors stop if no command / ping arrives in time (laptop gone)
// Wi-Fi and Bluetooth are never started (competition rule): there is no WiFi / BLE code anywhere.
#include <Arduino.h>
#include <TMCStepper.h>
#include <FastAccelStepper.h>
#include "pins.h"

// ---------------------------------------------------------------- settings
constexpr float R_SENSE = 0.11f;          // BIGTREETECH TMC2209 V1.3 sense resistor (ohm)
constexpr uint16_t MICROSTEPS = 16;
constexpr int STEPS_PER_REV = 200 * MICROSTEPS;   // 1.8 deg motors
constexpr uint32_t TELEMETRY_MS = 40;     // one driver read every 40 ms (round robin: each driver every 120 ms)

struct Axis {
  const char *name;
  uint8_t addr;            // UART address set by MS1/MS2 on the driver board: X 0, Y 2, wrist 3
  int step, dir;
  uint16_t mA;             // RMS current (wiring.md section 4)
  bool invert;             // motor plug order 2B 2A 1A 1B may reverse a motor: flip with "dir"
  TMC2209Stepper *drv;
  FastAccelStepper *mot;
  // last telemetry
  bool ok = false, on = true;
  uint32_t drvStatus = 0;
  uint16_t sg = 0;
};

HardwareSerial &TMC_SERIAL = Serial2;
TMC2209Stepper drvX(&TMC_SERIAL, R_SENSE, 0), drvY(&TMC_SERIAL, R_SENSE, 2), drvW(&TMC_SERIAL, R_SENSE, 3);
FastAccelStepperEngine engine;

Axis axes[3] = {
  {"x", 0, PIN_X_STEP, PIN_X_DIR, 900, false, &drvX, nullptr},
  {"y", 2, PIN_Y_STEP, PIN_Y_DIR, 900, false, &drvY, nullptr},
  {"w", 3, PIN_W_STEP, PIN_W_DIR, 600, false, &drvW, nullptr},
};

uint32_t maxSpeed = 3200;    // steps/s (1 rev/s at 16 microsteps)
uint32_t accel = 6400;       // steps/s^2
bool echoOn = true;
uint32_t streamMs = 0, lastStream = 0;     // automatic json status lines
uint32_t wdMs = 0, lastCmd = 0;            // watchdog
bool wdTripped = false;

// ---------------------------------------------------------------- drivers
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
  d.TCOOLTHRS(0xFFFFF);      // StallGuard result valid at all speeds (load reading for the app)
  a.ok = d.version() == 0x21;
  return a.ok;
}

void readTelemetry(Axis &a) {
  uint8_t v = a.drv->version();
  a.ok = v == 0x21;
  if (!a.ok) return;
  a.drvStatus = a.drv->DRV_STATUS();
  a.sg = a.drv->SG_RESULT();
}

long logical(const Axis &a, long p) { return a.invert ? -p : p; }   // positions as the user commands them

// DRV_STATUS bits (TMC2209 datasheet): 0 otpw, 1 ot, 2 s2ga, 3 s2gb, 4 s2vsa, 5 s2vsb, 6 ola, 7 olb, 8 t120, 9 t143,
// 10 t150, 11 t157, 16..20 cs_actual, 31 stst
void printJson() {
  Serial.printf("{\"t\":%lu,\"spd\":%lu,\"acc\":%lu,\"wd\":%lu,\"wdtrip\":%d,\"ax\":[", (unsigned long)millis(),
                (unsigned long)maxSpeed, (unsigned long)accel, (unsigned long)wdMs, wdTripped ? 1 : 0);
  for (int i = 0; i < 3; i++) {
    Axis &a = axes[i];
    uint32_t s = a.drvStatus;
    int temp = (s & (1UL << 11)) ? 157 : (s & (1UL << 10)) ? 150 : (s & (1UL << 9)) ? 143 : (s & (1UL << 8)) ? 120 : 0;
    Serial.printf("%s{\"n\":\"%s\",\"pos\":%ld,\"tgt\":%ld,\"run\":%d,\"ok\":%d,\"on\":%d,\"mA\":%u,\"inv\":%d,"
                  "\"sg\":%u,\"cs\":%lu,\"otpw\":%d,\"ot\":%d,\"s2g\":%d,\"ol\":%d,\"temp\":%d}",
                  i ? "," : "", a.name, logical(a, a.mot->getCurrentPosition()), logical(a, a.mot->targetPos()),
                  a.mot->isRunning() ? 1 : 0, a.ok ? 1 : 0, a.on ? 1 : 0, a.mA, a.invert ? 1 : 0,
                  a.sg, (unsigned long)((s >> 16) & 0x1F), (s & 1) ? 1 : 0, (s & 2) ? 1 : 0,
                  (s & (3UL << 2)) ? 1 : 0, (s & (3UL << 6)) ? 1 : 0, temp);
  }
  Serial.print("]}\r\n");
}

void printStatus(Axis &a) {
  readTelemetry(a);
  Serial.printf("[%s] addr %u  %s", a.name, a.addr, a.ok ? "OK" : "NO ANSWER");
  if (a.ok) {
    uint32_t ds = a.drvStatus;
    Serial.printf("  current %u mA  on %s  load %u  %s%s%s%s", a.drv->rms_current(), a.on ? "yes" : "no", a.sg,
                  (ds & (1UL << 1)) ? "OVERTEMP " : "", (ds & (1UL << 0)) ? "PRE-WARN " : "",
                  (ds & (3UL << 2)) ? "SHORT-GND " : "", (ds & (3UL << 6)) ? "OPEN-LOAD " : "");
  }
  Serial.printf("  pos %ld\r\n", logical(a, a.mot->getCurrentPosition()));
}

Axis *findAxis(const String &s) {
  for (auto &a : axes) if (s == a.name) return &a;
  return nullptr;
}

// ---------------------------------------------------------------- commands
void help() {
  Serial.print(F(
    "\r\nCommands (axis = x, y or w):\r\n"
    "  status              driver answers over UART? current, flags, position\r\n"
    "  m <axis> <steps>    move relative, 3200 steps = 1 turn (16 microsteps)\r\n"
    "  r <axis> <turns>    move relative in turns (can be 0.5, -2 ...)\r\n"
    "  g <axis> <steps>    go to an absolute position\r\n"
    "  zero <axis>         call the present position 0\r\n"
    "  test                each motor: 1 turn forward, 1 back, one after another\r\n"
    "  all <turns>         all three motors at once\r\n"
    "  speed <steps/s>     max speed;  accel <steps/s^2>\r\n"
    "  cur <axis> <mA>     RMS current (X/Y 900, wrist 600 by default; max ~1500)\r\n"
    "  on <axis> / off <axis>   driver output on / off (off = motor turns freely)\r\n"
    "  dir <axis>          reverse this motor's direction\r\n"
    "  stop                stop all motors (decelerate)\r\n"
    "  for programs: json | stream <ms> | wd <ms> | ping | echo 0/1\r\n"));
}

void startMove(Axis &a, long steps) {
  a.mot->move(a.invert ? -steps : steps);
}

void stopAll() { for (auto &a : axes) a.mot->stopMove(); }

void reply(const char *fmt, ...) {          // "ok ..." / "err ..." lines: the app waits for them
  char b[120];
  va_list ap; va_start(ap, fmt); vsnprintf(b, sizeof b, fmt, ap); va_end(ap);
  Serial.print(b); Serial.print("\r\n");
}

void command(String line) {
  line.trim(); line.toLowerCase();
  if (!line.length()) return;
  lastCmd = millis();
  int sp1 = line.indexOf(' ');
  String cmd = sp1 < 0 ? line : line.substring(0, sp1);
  String rest = sp1 < 0 ? "" : line.substring(sp1 + 1); rest.trim();
  int sp2 = rest.indexOf(' ');
  String arg1 = sp2 < 0 ? rest : rest.substring(0, sp2);
  String arg2 = sp2 < 0 ? "" : rest.substring(sp2 + 1); arg2.trim();

  if (cmd == "ping") { wdTripped = false; reply("pong"); return; }
  if (cmd == "json") { printJson(); return; }
  if (cmd == "stream") { streamMs = arg1.toInt(); reply("ok stream %lu", (unsigned long)streamMs); return; }
  if (cmd == "wd") { wdMs = arg1.toInt(); wdTripped = false; reply("ok wd %lu", (unsigned long)wdMs); return; }
  if (cmd == "echo") { echoOn = arg1.toInt() != 0; reply("ok echo %d", echoOn ? 1 : 0); return; }
  if (cmd == "help" || cmd == "?") { help(); return; }
  if (cmd == "status") {
    Serial.printf("speed %lu steps/s, accel %lu steps/s^2\r\n", (unsigned long)maxSpeed, (unsigned long)accel);
    for (auto &a : axes) printStatus(a);
    return;
  }
  if (cmd == "stop") { stopAll(); reply("ok stop"); return; }
  if (cmd == "speed") {
    maxSpeed = constrain(arg1.toInt(), 50, 40000);
    for (auto &a : axes) a.mot->setSpeedInHz(maxSpeed);
    reply("ok speed %lu", (unsigned long)maxSpeed); return;
  }
  if (cmd == "accel") {
    accel = constrain(arg1.toInt(), 100, 200000);
    for (auto &a : axes) a.mot->setAcceleration(accel);
    reply("ok accel %lu", (unsigned long)accel); return;
  }
  if (cmd == "test") {
    for (auto &a : axes) {
      Serial.printf("[%s] 1 turn forward, 1 back\r\n", a.name);
      startMove(a, STEPS_PER_REV);  while (a.mot->isRunning()) delay(5);
      delay(300);
      startMove(a, -STEPS_PER_REV); while (a.mot->isRunning()) delay(5);
      delay(300);
    }
    reply("ok test"); return;
  }
  if (cmd == "all") { long s = lround(arg1.toFloat() * STEPS_PER_REV); for (auto &a : axes) startMove(a, s); reply("ok all"); return; }

  Axis *a = findAxis(arg1);
  if (!a) { reply("err unknown command or axis - type help"); return; }
  if (cmd == "m")    { startMove(*a, arg2.toInt()); reply("ok m %s", a->name); return; }
  if (cmd == "r")    { startMove(*a, lround(arg2.toFloat() * STEPS_PER_REV)); reply("ok r %s", a->name); return; }
  if (cmd == "g")    { long p = arg2.toInt(); a->mot->moveTo(a->invert ? -p : p); reply("ok g %s", a->name); return; }
  if (cmd == "zero") { a->mot->setCurrentPosition(0); reply("ok zero %s", a->name); return; }
  if (cmd == "cur")  { uint16_t mA = constrain(arg2.toInt(), 100, 1500); a->mA = mA; a->drv->rms_current(mA); reply("ok cur %s %u", a->name, mA); return; }
  if (cmd == "on")   { a->drv->toff(4); a->on = true; reply("ok on %s", a->name); return; }
  if (cmd == "off")  { a->mot->forceStop(); a->drv->toff(0); a->on = false; reply("ok off %s", a->name); return; }
  if (cmd == "dir")  { a->invert = !a->invert; reply("ok dir %s %d", a->name, a->invert ? 1 : 0); return; }
  reply("err unknown command - type help");
}

// ---------------------------------------------------------------- console (line editor)
String buf;
void prompt() { if (echoOn) Serial.print("> "); }
void readConsole() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r' || c == '\n') {
      if (c == '\n' && !buf.length()) continue;      // the \n after a \r
      if (echoOn) Serial.print("\r\n");
      if (buf.length()) command(buf);
      buf = "";
      prompt();
    } else if (c == '\b' || c == 0x7f) {              // Backspace / Delete
      if (buf.length()) { buf.remove(buf.length() - 1); if (echoOn) Serial.print("\b \b"); }
    } else if (c == 0x1b) {                           // arrow keys etc. send ESC [ x: ignore them
      uint32_t t = millis();
      while (!Serial.available() && millis() - t < 20) {}
      if (Serial.available() && Serial.peek() == '[') { Serial.read(); t = millis(); while (!Serial.available() && millis() - t < 20) {} if (Serial.available()) Serial.read(); }
    } else if (isprint((unsigned char)c) && buf.length() < 80) {
      buf += c; if (echoOn) Serial.write(c);
    }
  }
}

// ---------------------------------------------------------------- main
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.print(F("\r\nETZ plotter firmware v2 (X, Y, wrist). Radio is never started.\r\n"));
  TMC_SERIAL.begin(115200, SERIAL_8N1, PIN_TMC_RX, PIN_TMC_TX);
  delay(50);
  engine.init();
  for (auto &a : axes) {
    a.mot = engine.stepperConnectToPin(a.step);
    if (!a.mot) { Serial.printf("[%s] step pin %d: no free step generator\r\n", a.name, a.step); continue; }
    a.mot->setDirectionPin(a.dir);
    a.mot->setSpeedInHz(maxSpeed);
    a.mot->setAcceleration(accel);
    bool ok = setupDriver(a);
    Serial.printf("[%s] UART address %u: %s\r\n", a.name, a.addr,
                  ok ? "driver answered, configured" : "NO ANSWER (is the battery / drive power on? cable? address?)");
  }
  help();
  lastCmd = millis();
  prompt();
}

uint8_t telemetryNext = 0;
uint32_t lastTelemetry = 0;
void loop() {
  readConsole();
  uint32_t now = millis();
  if (now - lastTelemetry >= TELEMETRY_MS) {              // one driver read per tick: motion is in hardware anyway
    lastTelemetry = now;
    readTelemetry(axes[telemetryNext]);
    telemetryNext = (telemetryNext + 1) % 3;
  }
  if (streamMs && now - lastStream >= streamMs) { lastStream = now; printJson(); }
  if (wdMs && !wdTripped && now - lastCmd > wdMs) {       // laptop silent: stop everything
    stopAll(); wdTripped = true;
    Serial.print("event watchdog: no ping, motors stopped\r\n");
  }
}
