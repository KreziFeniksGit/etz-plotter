// ETZ plotter firmware v3 - three steppers (X, Y, wrist) through TMC2209 drivers, for the bench and the laptop app.
// No outside libraries: only the Arduino core and our own libraries in lib/:
//   Tmc2209 - driver setup and status over the single-wire UART
//   StepGen - step pulses with acceleration from a hardware timer interrupt (loop() can never disturb them)
//   Console - line editor (echo, Backspace) and command splitter
// Protocol (unchanged from v2, used by laptop/esp_dashboard.py): typed commands, replies "ok ..." / "err ...",
// "echo 0" + "stream <ms>" + "json" status lines, "wd <ms>" + "ping" watchdog (motors stop if the laptop goes quiet).
// Wi-Fi and Bluetooth are never started (competition rule): there is no WiFi / BLE code anywhere.
#include <Arduino.h>
#include <Tmc2209.h>
#include <StepGen.h>
#include <Console.h>
#include "pins.h"

// ---------------------------------------------------------------- settings
constexpr float R_SENSE = 0.11f;          // BIGTREETECH TMC2209 V1.3 sense resistor (ohm)
constexpr uint16_t MICROSTEPS = 16;
constexpr int STEPS_PER_REV = 200 * MICROSTEPS;   // 1.8 deg motors
constexpr uint32_t TELEMETRY_MS = 100;    // one driver read every 100 ms, round robin

struct Axis {
  const char *name;
  uint8_t addr;            // UART address set by MS1/MS2 on the driver board: X 0, Y 2, wrist 3
  Tmc2209 drv;
  StepAxis mot;
  // last telemetry
  bool ok = false;
  bool sleeping = false;   // driver turned off by the idle timer (wakes by itself on the next move)
  uint32_t lastActive = 0; // millis() when it last moved or was commanded
  uint32_t drvStatus = 0;
  uint16_t sg = 0;
  uint8_t stepPin, dirPin;
  Axis(const char *n, uint8_t a, uint8_t step, uint8_t dir)
    : name(n), addr(a), drv(Serial2, a, R_SENSE), mot(step, dir), stepPin(step), dirPin(dir) {}
};

Axis axes[3] = {
  {"x", 0, PIN_X_STEP, PIN_X_DIR},
  {"y", 2, PIN_Y_STEP, PIN_Y_DIR},
  {"w", 3, PIN_W_STEP, PIN_W_DIR},
};
const uint16_t START_MA[3] = {900, 900, 600};    // RMS current (wiring.md section 4)

Console con(Serial);
uint32_t maxSpeed = 3200;    // steps/s (1 rev/s at 16 microsteps)
uint32_t accel = 6400;       // steps/s^2
uint32_t streamMs = 0, lastStream = 0;     // automatic json status lines
uint32_t wdMs = 0, lastCmd = 0;            // watchdog
bool wdTripped = false;
uint32_t idleMs = 60000;                   // driver off after this long without moving (0 = never)

// ---------------------------------------------------------------- drivers
void readTelemetry(Axis &a) {
  a.ok = a.drv.version() == 0x21;
  if (!a.ok) return;
  a.drv.readStatus(a.drvStatus);
  a.drv.readLoad(a.sg);
}

// DRV_STATUS bits: see lib/Tmc2209/Tmc2209.h
void printJson() {
  Serial.printf("{\"t\":%lu,\"spd\":%lu,\"acc\":%lu,\"wd\":%lu,\"wdtrip\":%d,\"idle\":%lu,\"ax\":[", (unsigned long)millis(),
                (unsigned long)maxSpeed, (unsigned long)accel, (unsigned long)wdMs, wdTripped ? 1 : 0, (unsigned long)idleMs);
  for (int i = 0; i < 3; i++) {
    Axis &a = axes[i];
    uint32_t s = a.drvStatus;
    int temp = (s & (1UL << 11)) ? 157 : (s & (1UL << 10)) ? 150 : (s & (1UL << 9)) ? 143 : (s & (1UL << 8)) ? 120 : 0;
    Serial.printf("%s{\"n\":\"%s\",\"pos\":%ld,\"tgt\":%ld,\"run\":%d,\"ok\":%d,\"on\":%d,\"mA\":%u,\"inv\":%d,\"sleep\":%d,"
                  "\"sg\":%u,\"cs\":%lu,\"otpw\":%d,\"ot\":%d,\"s2g\":%d,\"ol\":%d,\"temp\":%d}",
                  i ? "," : "", a.name, (long)a.mot.position(), (long)a.mot.target(), a.mot.running() ? 1 : 0,
                  a.ok ? 1 : 0, a.drv.enabled() ? 1 : 0, a.drv.current(), a.mot.inverted() ? 1 : 0, a.sleeping ? 1 : 0,
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
    Serial.printf("  current %u mA  on %s  load %u  %s%s%s%s", a.drv.current(), a.drv.enabled() ? "yes" : "no", a.sg,
                  (ds & (1UL << 1)) ? "OVERTEMP " : "", (ds & (1UL << 0)) ? "PRE-WARN " : "",
                  (ds & (3UL << 2)) ? "SHORT-GND " : "", (ds & (3UL << 6)) ? "OPEN-LOAD " : "");
  }
  Serial.printf("  pos %ld\r\n", (long)a.mot.position());
}

Axis *findAxis(const char *s) {
  for (auto &a : axes) if (strcmp(s, a.name) == 0) return &a;
  return nullptr;
}

void stopAll() { for (auto &a : axes) a.mot.stop(); }           // decelerate to a stop
bool anyMoving() { for (auto &a : axes) if (a.mot.running()) return true; return false; }
void waitStill(StepAxis &m) { while (m.running()) delay(1); }

// idle timer: a driver that has not moved for idleMs is turned off (cool, no hold current); the next move
// turns it back on first. Careful: while off, the motor can be turned by hand and the position may be lost.
StepAxis &wake(Axis &a) {
  a.lastActive = millis();
  if (a.sleeping) {
    a.drv.enable(true); a.sleeping = false;
    delay(5);                                  // coils back on before the first step
    Serial.printf("event idle %s: driver back on\r\n", a.name);
  }
  return a.mot;
}

// ---------------------------------------------------------------- commands
void help() {
  Serial.print(
    "\r\nCommands (axis = x, y or w):\r\n"
    "  status              driver answers over UART? current, flags, position\r\n"
    "  m <axis> <steps>    move relative, 3200 steps = 1 turn (16 microsteps)\r\n"
    "  r <axis> <turns>    move relative in turns (can be 0.5, -2 ...)\r\n"
    "  g <axis> <steps>    go to an absolute position\r\n"
    "  zero <axis>         call the present position 0\r\n"
    "  test                each motor: 1 turn forward, 1 back, one after another\r\n"
    "  all <turns>         all three motors at once\r\n"
    "  speed <steps/s>     max speed (up to 16000);  accel <steps/s^2>\r\n"
    "  cur <axis> <mA>     RMS current (X/Y 900, wrist 600 by default; max ~1500)\r\n"
    "  on <axis> / off <axis>   driver output on / off (off = motor turns freely)\r\n"
    "  dir <axis>          reverse this motor's direction (when it stands)\r\n"
    "  stop                stop all motors (decelerate)\r\n"
    "  idle <s>            driver off after s seconds standing (default 60, 0 = never); wakes by itself\r\n"
    "  checks: pulse <axis> <steps> [us]   plain even pulses from the main loop, no timer, no acceleration\r\n"
    "          reg <axis>                  driver registers (did our UART writes arrive?)\r\n"
    "  for programs: json | stream <ms> | wd <ms> | ping | echo 0/1\r\n");
}

void command() {
  lastCmd = millis();
  if (con.is(0, "ping")) { wdTripped = false; con.reply("pong"); return; }
  if (con.is(0, "json")) { printJson(); return; }
  if (con.is(0, "stream")) { streamMs = con.argInt(1); con.reply("ok stream %lu", (unsigned long)streamMs); return; }
  if (con.is(0, "wd")) { wdMs = con.argInt(1); wdTripped = false; con.reply("ok wd %lu", (unsigned long)wdMs); return; }
  if (con.is(0, "echo")) { con.setEcho(con.argInt(1) != 0); con.reply("ok echo %d", con.echo() ? 1 : 0); return; }
  if (con.is(0, "help") || con.is(0, "?")) { help(); return; }
  if (con.is(0, "status")) {
    Serial.printf("speed %lu steps/s, accel %lu steps/s^2\r\n", (unsigned long)maxSpeed, (unsigned long)accel);
    for (auto &a : axes) printStatus(a);
    return;
  }
  if (con.is(0, "idle")) { idleMs = con.argInt(1) * 1000UL; con.reply("ok idle %lu", (unsigned long)(idleMs / 1000)); return; }
  if (con.is(0, "stop")) { stopAll(); con.reply("ok stop"); return; }
  if (con.is(0, "pulse")) {                 // check: steps made by hand, like the simplest possible program
    Axis *a = findAxis(con.word(1));
    if (!a || a->mot.running()) { con.reply("err pulse <axis> <steps> [us between steps], motor standing"); return; }
    long n = con.argInt(2);
    long us = con.words() > 3 ? constrain(con.argInt(3), 100L, 100000L) : 1000L;   // 1000 us = 1000 steps/s
    digitalWrite(a->dirPin, (n > 0) != a->mot.inverted() ? HIGH : LOW);
    delayMicroseconds(50);
    for (long i = 0; i < labs(n); i++) {
      digitalWrite(a->stepPin, HIGH); delayMicroseconds(5);
      digitalWrite(a->stepPin, LOW);  delayMicroseconds(us);
    }
    a->mot.setInvert(a->mot.inverted());    // put the DIR pin back where StepGen expects it
    con.reply("ok pulse %s %ld", a->name, n); return;
  }
  if (con.is(0, "reg")) {                   // check: read back what the driver holds
    Axis *a = findAxis(con.word(1));
    if (!a) { con.reply("err reg <axis>"); return; }
    const struct { const char *n; uint8_t r; } regs[] = {
      {"GCONF", Tmc2209::GCONF}, {"GSTAT", Tmc2209::GSTAT}, {"IFCNT", Tmc2209::IFCNT}, {"IOIN", Tmc2209::IOIN},
      {"CHOPCONF", Tmc2209::CHOPCONF}, {"DRV_STATUS", Tmc2209::DRV_STATUS}, {"PWMCONF", Tmc2209::PWMCONF}};
    for (auto &g : regs) {
      uint32_t v;
      if (a->drv.readReg(g.r, v)) Serial.printf("  %-10s 0x%08lX\r\n", g.n, (unsigned long)v);
      else Serial.printf("  %-10s no answer\r\n", g.n);
    }
    Serial.print("  expect GCONF 0x000001C0, CHOPCONF 0x14028054 (900 mA) or 0x14008054, IFCNT = writes accepted\r\n");
    return;
  }
  if (con.is(0, "speed")) {
    maxSpeed = constrain(con.argInt(1), 50L, (long)StepAxis::MAX_SPEED);
    for (auto &a : axes) a.mot.setMaxSpeed(maxSpeed);
    con.reply("ok speed %lu", (unsigned long)maxSpeed); return;
  }
  if (con.is(0, "accel")) {
    accel = constrain(con.argInt(1), 100L, 200000L);
    for (auto &a : axes) a.mot.setAccel(accel);
    con.reply("ok accel %lu", (unsigned long)accel); return;
  }
  if (con.is(0, "test")) {
    for (auto &a : axes) {
      Serial.printf("[%s] 1 turn forward, 1 back\r\n", a.name);
      wake(a).move(STEPS_PER_REV);  waitStill(a.mot); delay(300);
      wake(a).move(-STEPS_PER_REV); waitStill(a.mot); delay(300);
    }
    con.reply("ok test"); return;
  }
  if (con.is(0, "all")) {
    long s = lroundf(con.argFloat(1) * STEPS_PER_REV);
    for (auto &a : axes) wake(a).move(s);
    con.reply("ok all"); return;
  }

  Axis *a = findAxis(con.word(1));
  if (!a) { con.reply("err unknown command or axis - type help"); return; }
  if (con.is(0, "m"))    { wake(*a).move(con.argInt(2)); con.reply("ok m %s", a->name); return; }
  if (con.is(0, "r"))    { wake(*a).move(lroundf(con.argFloat(2) * STEPS_PER_REV)); con.reply("ok r %s", a->name); return; }
  if (con.is(0, "g"))    { wake(*a).moveTo(con.argInt(2)); con.reply("ok g %s", a->name); return; }
  if (con.is(0, "zero")) { a->mot.setPosition(0); con.reply("ok zero %s", a->name); return; }
  if (con.is(0, "cur"))  {
    uint16_t mA = constrain(con.argInt(2), 100L, 1500L);
    a->drv.setCurrent(mA); con.reply("ok cur %s %u", a->name, mA); return;
  }
  if (con.is(0, "on"))   { a->drv.enable(true); a->sleeping = false; a->lastActive = millis(); con.reply("ok on %s", a->name); return; }
  if (con.is(0, "off"))  { a->mot.halt(); a->drv.enable(false); a->sleeping = false; con.reply("ok off %s", a->name); return; }
  if (con.is(0, "dir"))  {
    if (a->mot.running()) { con.reply("err %s is moving - stop it first", a->name); return; }
    a->mot.setInvert(!a->mot.inverted()); con.reply("ok dir %s %d", a->name, a->mot.inverted() ? 1 : 0); return;
  }
  con.reply("err unknown command - type help");
}

// ---------------------------------------------------------------- main
void setup() {
  Serial.setTxBufferSize(4096);           // status lines go out in the background
  Serial.begin(115200);
  delay(500);
  Serial.print("\r\nETZ plotter firmware v3 (X, Y, wrist), no outside libraries. Radio is never started.\r\n");
  Serial2.begin(115200, SERIAL_8N1, PIN_TMC_RX, PIN_TMC_TX);
  delay(50);
  StepAxis *motors[3];
  for (int i = 0; i < 3; i++) {
    Axis &a = axes[i];
    a.mot.setMaxSpeed(maxSpeed);
    a.mot.setAccel(accel);
    motors[i] = &a.mot;
    a.ok = a.drv.begin(START_MA[i], MICROSTEPS);
    Serial.printf("[%s] UART address %u: %s\r\n", a.name, a.addr,
                  a.ok ? "driver answered, configured" : "NO ANSWER (is the battery / drive power on? cable? address?)");
  }
  if (!StepAxis::begin(motors, 3)) Serial.print("err step timer did not start\r\n");
  help();
  lastCmd = millis();
  con.prompt();
}

uint8_t telemetryNext = 0;
uint32_t lastTelemetry = 0;
void loop() {
  if (con.poll()) { command(); con.prompt(); }
  uint32_t now = millis();
  if (!anyMoving() && now - lastTelemetry >= TELEMETRY_MS) {   // like v1: no UART traffic while a motor moves
    lastTelemetry = now;
    readTelemetry(axes[telemetryNext]);
    telemetryNext = (telemetryNext + 1) % 3;
  }
  if (streamMs && now - lastStream >= streamMs) { lastStream = now; printJson(); }
  for (auto &a : axes) {                          // idle timer
    if (a.mot.running()) a.lastActive = now;
    else if (idleMs && a.drv.enabled() && now - a.lastActive > idleMs) {
      a.drv.enable(false); a.sleeping = true;
      Serial.printf("event idle %s: not used for %lu s, driver off\r\n", a.name, (unsigned long)(idleMs / 1000));
    }
  }
  if (wdMs && !wdTripped && now - lastCmd > wdMs) {       // laptop silent: stop everything
    stopAll(); wdTripped = true;
    Serial.print("event watchdog: no ping, motors stopped\r\n");
  }
}
