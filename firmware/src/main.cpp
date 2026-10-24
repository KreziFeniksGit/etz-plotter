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
  uint32_t spd = 3200, acc = 6400;   // this motor's max speed (steps/s) and acceleration (steps/s^2)
  Axis(const char *n, uint8_t a, uint8_t step, uint8_t dir)
    : name(n), addr(a), drv(Serial2, a, R_SENSE), mot(step, dir), stepPin(step), dirPin(dir) {}
  void setSpeed(uint32_t v) { spd = constrain(v, 50UL, StepAxis::MAX_SPEED); mot.setMaxSpeed(spd); }
  void setAccel(uint32_t v) { acc = constrain(v, 100UL, 200000UL); mot.setAccel(acc); }
};

Axis axes[3] = {
  {"x", 0, PIN_X_STEP, PIN_X_DIR},
  {"y", 2, PIN_Y_STEP, PIN_Y_DIR},
  {"w", 3, PIN_W_STEP, PIN_W_DIR},
};
const uint16_t START_MA[3] = {900, 900, 600};    // RMS current (wiring.md section 4)

Console con(Serial);
uint32_t streamMs = 0, lastStream = 0;     // automatic json status lines
uint32_t wdMs = 0, lastCmd = 0;            // watchdog
bool wdTripped = false;
uint32_t idleMs = 60000;                   // driver off after this long without moving (0 = never)
uint32_t loopHz = 0, loopCount = 0, loopT0 = 0;   // main loop passes per second (how busy the ESP32 is)

// ---------------------------------------------------------------- the ESP32 itself
const char *resetReason() {
  switch (esp_reset_reason()) {
    case ESP_RST_POWERON: return "power on";
    case ESP_RST_SW: return "software restart";
    case ESP_RST_PANIC: return "CRASH (panic)";
    case ESP_RST_INT_WDT: case ESP_RST_TASK_WDT: case ESP_RST_WDT: return "CRASH (watchdog)";
    case ESP_RST_BROWNOUT: return "BROWNOUT (supply voltage dipped)";
    case ESP_RST_EXT: return "reset pin / USB";
    default: return "other";
  }
}

void printMem() {
  Serial.printf("  RAM free %lu bytes of %lu (lowest so far %lu), biggest block %lu\r\n",
                (unsigned long)ESP.getFreeHeap(), (unsigned long)ESP.getHeapSize(),
                (unsigned long)ESP.getMinFreeHeap(), (unsigned long)ESP.getMaxAllocHeap());
  Serial.printf("  PSRAM free %lu bytes of %lu\r\n", (unsigned long)ESP.getFreePsram(), (unsigned long)ESP.getPsramSize());
  Serial.printf("  loop() stack never used: %lu bytes\r\n", (unsigned long)uxTaskGetStackHighWaterMark(nullptr));
  Serial.printf("  flash %lu MB, program %lu kB, CPU %lu MHz, chip %.1f C\r\n",
                (unsigned long)(ESP.getFlashChipSize() >> 20), (unsigned long)(ESP.getSketchSize() >> 10),
                (unsigned long)ESP.getCpuFreqMHz(), temperatureRead());
  Serial.printf("  up %lu s, loop %lu passes/s, last reset: %s\r\n", (unsigned long)(millis() / 1000),
                (unsigned long)loopHz, resetReason());
}

// ---------------------------------------------------------------- drivers
// The drivers lose their settings when the drive power goes off (battery, stop button) and wake up on their
// defaults (pot current, microsteps from the MS pins). So: when a driver starts answering again, or says it was
// reset (GSTAT bit 0), it is set up again here.
void readTelemetry(Axis &a) {
  bool was = a.ok;
  a.ok = a.drv.version() == 0x21;
  if (!a.ok) {
    if (was) Serial.printf("event driver %s: no answer (drive power off?)\r\n", a.name);
    return;
  }
  uint32_t gstat = 0;
  if (!was || (a.drv.readReg(Tmc2209::GSTAT, gstat) && (gstat & 1))) {
    bool on = a.drv.enabled();
    a.ok = a.drv.begin(a.drv.current(), MICROSTEPS);
    if (!on) a.drv.enable(false);           // keep "off" / "sleeping"
    Serial.printf("event driver %s: answered, configured again\r\n", a.name);
  }
  a.drv.readStatus(a.drvStatus);
  a.drv.readLoad(a.sg);
}

// DRV_STATUS bits: see lib/Tmc2209/Tmc2209.h
void printJson() {
  Serial.printf("{\"t\":%lu,\"wd\":%lu,\"wdtrip\":%d,\"idle\":%lu,\"heap\":%lu,\"heapmin\":%lu,\"heapsize\":%lu,"
                "\"loop\":%lu,\"ctemp\":%.1f,\"ax\":[", (unsigned long)millis(), (unsigned long)wdMs, wdTripped ? 1 : 0,
                (unsigned long)idleMs, (unsigned long)ESP.getFreeHeap(), (unsigned long)ESP.getMinFreeHeap(),
                (unsigned long)ESP.getHeapSize(), (unsigned long)loopHz, temperatureRead());
  for (int i = 0; i < 3; i++) {
    Axis &a = axes[i];
    uint32_t s = a.drvStatus;
    int temp = (s & (1UL << 11)) ? 157 : (s & (1UL << 10)) ? 150 : (s & (1UL << 9)) ? 143 : (s & (1UL << 8)) ? 120 : 0;
    Serial.printf("%s{\"n\":\"%s\",\"pos\":%ld,\"tgt\":%ld,\"run\":%d,\"ok\":%d,\"on\":%d,\"mA\":%u,\"inv\":%d,\"sleep\":%d,"
                  "\"spd\":%lu,\"acc\":%lu,\"v\":%lu,"
                  "\"sg\":%u,\"cs\":%lu,\"otpw\":%d,\"ot\":%d,\"s2g\":%d,\"ol\":%d,\"temp\":%d}",
                  i ? "," : "", a.name, (long)a.mot.position(), (long)a.mot.target(), a.mot.running() ? 1 : 0,
                  a.ok ? 1 : 0, a.drv.enabled() ? 1 : 0, a.drv.current(), a.mot.inverted() ? 1 : 0, a.sleeping ? 1 : 0,
                  (unsigned long)a.spd, (unsigned long)a.acc, (unsigned long)a.mot.speed(),
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
  Serial.printf("  speed %lu accel %lu  pos %ld\r\n", (unsigned long)a.spd, (unsigned long)a.acc, (long)a.mot.position());
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
    "  speed [axis] <steps/s>   max speed (up to 16000), one motor or all;  accel [axis] <steps/s^2>\r\n"
    "  mem                 ESP32 memory, CPU, temperature, uptime, why it last restarted\r\n"
    "  cur <axis> <mA>     RMS current (X/Y 900, wrist 600 by default; max ~1500)\r\n"
    "  on <axis> / off <axis>   driver output on / off (off = motor turns freely)\r\n"
    "  dir <axis>          reverse this motor's direction (when it stands)\r\n"
    "  stop                stop all motors (decelerate)\r\n"
    "  idle <s>            driver off after s seconds standing (default 60, 0 = never); wakes by itself\r\n"
    "  checks: pulse <axis> <steps> [us]   plain even pulses from the main loop, no timer, no acceleration\r\n"
    "          reg <axis>                  driver registers (did our UART writes arrive?)\r\n"
    "          pins <axis>                 does the driver see our STEP / DIR pins?\r\n"
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
  if (con.is(0, "status")) { for (auto &a : axes) printStatus(a); return; }
  if (con.is(0, "mem")) { printMem(); return; }
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
  if (con.is(0, "pins")) {                  // check: does the driver see our STEP and DIR pins? (IOIN bit 7 STEP, bit 9 DIR)
    Axis *a = findAxis(con.word(1));
    if (!a || a->mot.running()) { con.reply("err pins <axis>, motor standing"); return; }
    uint32_t v;
    struct { const char *what; uint8_t pin; int level; uint8_t bit; } t[] = {
      {"STEP high", a->stepPin, HIGH, 7}, {"STEP low ", a->stepPin, LOW, 7},
      {"DIR high ", a->dirPin, HIGH, 9}, {"DIR low  ", a->dirPin, LOW, 9}};
    for (auto &c : t) {
      digitalWrite(c.pin, c.level); delay(2);
      bool ok = a->drv.readReg(Tmc2209::IOIN, v);
      Serial.printf("  GPIO%-2u %s -> driver sees %s%s", c.pin, c.what,
                    ok ? ((v >> c.bit) & 1 ? "HIGH" : "LOW") : "no answer",
                    ok && (((v >> c.bit) & 1) != (c.level == HIGH)) ? "   <-- WRONG" : "");
      Serial.print("\r\n");
    }
    a->mot.setInvert(a->mot.inverted());    // DIR pin back where StepGen expects it
    con.reply("ok pins %s", a->name); return;
  }
  if (con.is(0, "reg")) {                   // check: read back what the driver holds
    Axis *a = findAxis(con.word(1));
    if (!a) { con.reply("err reg <axis>"); return; }
    const struct { const char *n; uint8_t r; } regs[] = {
      {"GCONF", Tmc2209::GCONF}, {"GSTAT", Tmc2209::GSTAT}, {"IFCNT", Tmc2209::IFCNT}, {"IOIN", Tmc2209::IOIN},
      {"CHOPCONF", Tmc2209::CHOPCONF}, {"DRV_STATUS", Tmc2209::DRV_STATUS}, {"PWMCONF", Tmc2209::PWMCONF}, {"MSCNT", 0x6A}};
    for (auto &g : regs) {
      uint32_t v;
      if (a->drv.readReg(g.r, v)) Serial.printf("  %-10s 0x%08lX\r\n", g.n, (unsigned long)v);
      else Serial.printf("  %-10s no answer\r\n", g.n);
    }
    a->drv.version();
    Serial.printf("  raw bytes back for a read (%u):", a->drv.lastRxLen());
    for (uint8_t i = 0; i < a->drv.lastRxLen(); i++) Serial.printf(" %02X", a->drv.lastRx()[i]);
    Serial.print("\r\n  0 bytes = nothing on the wire (RX/TX pins, 1k resistor, cable); 4 bytes = only our echo, the driver"
                 " is silent (drive power off? address?); 12 = echo + answer\r\n");
    Serial.print("  expect GCONF 0x000001C0, CHOPCONF 0x14028054 (900 mA) or 0x14008054, IFCNT = writes accepted\r\n");
    return;
  }
  if (con.is(0, "speed") || con.is(0, "accel")) {   // "speed 3200" = all motors, "speed x 3200" = only X
    bool isSpeed = con.is(0, "speed");
    Axis *one = findAxis(con.word(1));
    long v = con.argInt(one ? 2 : 1);
    for (auto &a : axes) {
      if (one && one != &a) continue;
      if (isSpeed) a.setSpeed(v); else a.setAccel(v);
    }
    Axis &shown = one ? *one : axes[0];
    con.reply("ok %s %s %lu", con.word(0), one ? one->name : "all", (unsigned long)(isSpeed ? shown.spd : shown.acc));
    return;
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
    a.setSpeed(a.spd);
    a.setAccel(a.acc);
    motors[i] = &a.mot;
    a.ok = a.drv.begin(START_MA[i], MICROSTEPS);
    Serial.printf("[%s] UART address %u: %s\r\n", a.name, a.addr,
                  a.ok ? "driver answered, configured" : "NO ANSWER (is the battery / drive power on? cable? address?)");
  }
  if (!StepAxis::begin(motors, 3)) Serial.print("err step timer did not start\r\n");
  Serial.printf("last reset: %s\r\n", resetReason());
  help();
  lastCmd = millis();
  con.prompt();
}

uint8_t telemetryNext = 0;
uint32_t lastTelemetry = 0;
void loop() {
  if (con.poll()) { command(); con.prompt(); }
  uint32_t now = millis();
  loopCount++;
  if (now - loopT0 >= 1000) { loopHz = loopCount * 1000 / (now - loopT0); loopCount = 0; loopT0 = now; }
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
