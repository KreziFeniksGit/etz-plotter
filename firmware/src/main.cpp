// ETZ plotter firmware v4 - three steppers (X, Y, wrist) through TMC2209 drivers, for the bench and the laptop app.
// No outside libraries: only the Arduino core and our own libraries in lib/:
//   Tmc2209  - driver setup and status over the single-wire UART
//   StepGen  - step pulses from a timer interrupt, trapezoid or S-curve, coordinated XY lines
//   Console  - line editor (echo, Backspace) and command splitter
//   Settings - settings profiles kept in flash (NVS)
//   BlackBox - last 64 events, survive a crash restart (copied to flash after a crash)
//   Guard    - motor heat model and crash (stall) detector
// Protection that always runs (service()): heat guard, crash detection, idle switch-off, laptop watchdog.
// Protocol (used by laptop/esp_dashboard.py): typed commands, replies "ok ..." / "err ...", events "event ...",
// "echo 0" + "stream <ms>" + "json" status lines, "wd <ms>" + "ping" watchdog (motors stop if the laptop goes quiet).
// Wi-Fi and Bluetooth are never started (competition rule): there is no WiFi / BLE code anywhere.
#include <Arduino.h>
#include <Tmc2209.h>
#include <StepGen.h>
#include <Console.h>
#include <Settings.h>
#include <BlackBox.h>
#include <Guard.h>
#include "pins.h"

// ---------------------------------------------------------------- fixed settings
constexpr float R_SENSE = 0.11f;          // BIGTREETECH TMC2209 V1.3 sense resistor (ohm)
constexpr uint16_t MICROSTEPS = 16;
constexpr int STEPS_PER_REV = 200 * MICROSTEPS;   // 1.8 deg motors
constexpr uint32_t TELEMETRY_MS = 100;    // one driver status read every 100 ms while nothing moves
constexpr uint32_t LOAD_MS = 5;           // one load (StallGuard) read every 5 ms while moving: crash detection
constexpr float AMBIENT_C = 25.0f;        // room temperature for the motor heat model
constexpr float VBAT_SCALE = (100.0f + 15.0f) / 15.0f;   // battery divider 100 k / 15 k (wiring.md)
constexpr float VBAT_MIN = 14.0f;         // 4S LiPo: stop the run below this

// ---------------------------------------------------------------- settings kept in flash (profiles)
struct Cfg {
  uint32_t magic, size;
  struct Ax { uint32_t spd, acc; uint16_t jerk, mA, ratedmA, tau; uint8_t inv, hold, crashPct, pad; } ax[3];
  uint32_t idleS;
  uint8_t warnC, limitC, pad[2];
};
constexpr uint32_t CFG_MAGIC = 0xE7202604;
// motors (wiring.md section 4): X/Y StepperOnline 17HS16-2004S1 rated 2.0 A, wrist 17HS4023S rated 0.7 A.
// tau = thermal time constant in s (VERIFY: not in the datasheets, typical NEMA17 10-15 min, pancake less)
const Cfg DEFAULTS = {CFG_MAGIC, sizeof(Cfg), {
  {3200, 6400, 0, 900, 2000, 900, 0, 50, 30, 0},
  {3200, 6400, 0, 900, 2000, 900, 0, 50, 30, 0},
  {3200, 6400, 0, 600, 700, 600, 0, 50, 30, 0}},
  60, 70, 90, {0, 0}};
Cfg cfg = DEFAULTS;
char profileName[16] = "defaults";

struct Axis {
  const char *name;
  uint8_t addr;            // UART address set by MS1/MS2 on the driver board: X 0, Y 2, wrist 3
  Tmc2209 drv;
  StepAxis mot;
  uint8_t stepPin, dirPin;
  Cfg::Ax *c = nullptr;    // this motor's settings
  HeatModel heat;
  CrashDetector crash;
  bool ok = false;         // driver answers over UART
  bool sleeping = false;   // turned off by the idle timer or after cooling: wakes by itself on the next move
  bool warm = false, hot = false;   // heat guard state
  bool lost = false;       // position not trusted any more (crash, driver off by hand): home before real work
  bool otpwSeen = false;
  uint32_t lastActive = 0, drvStatus = 0, lastLoad = 0;
  uint16_t sg = 0;
  Axis(const char *n, uint8_t a, uint8_t step, uint8_t dir)
    : name(n), addr(a), drv(Serial2, a, R_SENSE), mot(step, dir), stepPin(step), dirPin(dir) {}
  float temp() const { return heat.temp(AMBIENT_C); }
};

Axis axes[3] = {
  {"x", 0, PIN_X_STEP, PIN_X_DIR},
  {"y", 2, PIN_Y_STEP, PIN_Y_DIR},
  {"w", 3, PIN_W_STEP, PIN_W_DIR},
};
Axis &AX = axes[0], &AY = axes[1];

Console con(Serial);
uint32_t streamMs = 0, lastStream = 0;     // automatic json status lines
uint32_t wdMs = 0, lastCmd = 0;            // laptop watchdog
bool wdTripped = false;
uint32_t loopHz = 0, loopCount = 0, loopT0 = 0;
const char *busy = nullptr;                // name of the long command running (self-test, tune ...), else nullptr
bool abortReq = false;                     // "stop" / watchdog / crash during a long command
uint32_t crashes = 0;

// ---------------------------------------------------------------- small helpers
void event(const char *fmt, ...) {         // "event ..." line for the laptop + the black box
  char b[120];
  va_list ap; va_start(ap, fmt); vsnprintf(b, sizeof b, fmt, ap); va_end(ap);
  Serial.printf("event %s\r\n", b);
  BlackBox::add("%s", b);
}

Axis *findAxis(const char *s) {
  for (auto &a : axes) if (strcmp(s, a.name) == 0) return &a;
  return nullptr;
}

bool anyMoving() { for (auto &a : axes) if (a.mot.running()) return true; return false; }
void stopAll() { for (auto &a : axes) a.mot.stop(); }           // decelerate to a stop
void haltAll() { for (auto &a : axes) a.mot.halt(); }           // stop at once

float batteryVolts() { return analogReadMilliVolts(PIN_VBAT_SENSE) * VBAT_SCALE / 1000.0f; }
bool drivePowerOn() { return digitalRead(PIN_STOP_SENSE) == HIGH; }

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
bool crashedLastTime() {
  esp_reset_reason_t r = esp_reset_reason();
  return r == ESP_RST_PANIC || r == ESP_RST_INT_WDT || r == ESP_RST_TASK_WDT || r == ESP_RST_WDT || r == ESP_RST_BROWNOUT;
}

// ---------------------------------------------------------------- settings -> hardware
void applyAxis(Axis &a) {
  Cfg::Ax &c = *a.c;
  a.mot.setMaxSpeed(c.spd);
  a.mot.setAccel(c.acc);
  a.mot.setJerk(c.jerk);
  if (!a.mot.running() && a.mot.inverted() != (bool)c.inv) a.mot.setInvert(c.inv);
  a.heat.setup(c.ratedmA, c.tau);
  a.crash.pct = c.crashPct;
  if (a.ok) {
    a.drv.setCurrent(c.mA);
    a.drv.setHoldPercent(a.warm ? min<uint8_t>(c.hold, 20) : c.hold);
  }
}
void applyAll() { for (auto &a : axes) applyAxis(a); }

bool loadProfile(const char *name) {
  Cfg c;
  if (!Settings::load(name, &c, sizeof c) || c.magic != CFG_MAGIC || c.size != sizeof c) return false;
  cfg = c;
  strlcpy(profileName, name, sizeof profileName);
  applyAll();
  return true;
}

// ---------------------------------------------------------------- the ESP32 itself
void printMem() {
  Serial.printf("  RAM free %lu bytes of %lu (lowest so far %lu), biggest block %lu\r\n",
                (unsigned long)ESP.getFreeHeap(), (unsigned long)ESP.getHeapSize(),
                (unsigned long)ESP.getMinFreeHeap(), (unsigned long)ESP.getMaxAllocHeap());
  Serial.printf("  PSRAM free %lu bytes of %lu\r\n", (unsigned long)ESP.getFreePsram(), (unsigned long)ESP.getPsramSize());
  Serial.printf("  loop() stack never used: %lu bytes\r\n", (unsigned long)uxTaskGetStackHighWaterMark(nullptr));
  Serial.printf("  flash %lu MB, program %lu kB, CPU %lu MHz, chip %.1f C\r\n",
                (unsigned long)(ESP.getFlashChipSize() >> 20), (unsigned long)(ESP.getSketchSize() >> 10),
                (unsigned long)ESP.getCpuFreqMHz(), temperatureRead());
  Serial.printf("  up %lu s, loop %lu passes/s, boot no. %lu, last reset: %s\r\n", (unsigned long)(millis() / 1000),
                (unsigned long)loopHz, (unsigned long)BlackBox::boots(), resetReason());
}

// ---------------------------------------------------------------- drivers
// The drivers lose their settings when the drive power goes off (battery, stop button) and wake up on their
// defaults. So when a driver starts answering again, or says it was reset (GSTAT bit 0), it is set up again.
void readTelemetry(Axis &a) {
  bool was = a.ok;
  a.ok = a.drv.version() == 0x21;
  if (!a.ok) {
    if (was) event("driver %s: no answer (drive power off?)", a.name);
    return;
  }
  uint32_t gstat = 0;
  if (!was || (a.drv.readReg(Tmc2209::GSTAT, gstat) && (gstat & 1))) {
    bool on = a.drv.enabled();
    a.ok = a.drv.begin(a.c->mA, MICROSTEPS);
    applyAxis(a);
    if (!on) a.drv.enable(false);           // keep "off" / "sleeping"
    event("driver %s: answered, configured", a.name);
  }
  a.drv.readStatus(a.drvStatus);
  a.drv.readLoad(a.sg);
  if ((a.drvStatus & 1) && !a.otpwSeen) { a.otpwSeen = true; event("driver %s chip hot (pre-warning)", a.name); }
  if (!(a.drvStatus & 1)) a.otpwSeen = false;
}

// ---------------------------------------------------------------- moves
// every move goes through here: refuses a motor that is too hot, wakes a sleeping one, arms the crash detector
bool prepMove(Axis &a) {
  if (a.hot) {
    con.reply("err %s too hot (about %.0f C) - wait until it cools below %u C", a.name, a.temp(), cfg.warnC - 5);
    return false;
  }
  a.lastActive = millis();
  if (a.sleeping) {
    a.drv.enable(true); a.sleeping = false;
    delay(5);                                  // coils back on before the first step
    event("idle %s: driver back on", a.name);
  }
  a.crash.startMove();
  return true;
}

void onCrash(Axis &a) {
  haltAll();
  a.lost = true; crashes++;
  if (busy) abortReq = true;
  event("CRASH %s: load %u (normal %u) at %lu steps/s, pos %ld - all motors stopped, position not trusted",
        a.name, a.sg, a.crash.average(), (unsigned long)a.mot.speed(), (long)a.mot.position());
}

// straight XY line: both axes get the same speed profile shape, so they start and arrive together
bool lineTo(int32_t x, int32_t y) {
  if (!prepMove(AX) || !prepMove(AY)) return false;
  float dx = fabsf((float)(x - AX.mot.position())), dy = fabsf((float)(y - AY.mot.position()));
  float L = sqrtf(dx * dx + dy * dy);
  if (L < 1) return true;
  float ux = dx / L, uy = dy / L;
  float V = 1e9f, A = 1e9f;                  // path speed / accel that keeps each axis within its own limits
  if (ux > 0.001f) { V = min(V, AX.c->spd / ux); A = min(A, AX.c->acc / ux); }
  if (uy > 0.001f) { V = min(V, AY.c->spd / uy); A = min(A, AY.c->acc / uy); }
  uint32_t jerk = max(AX.c->jerk, AY.c->jerk);
  StepAxis::lock();                          // both start in the same interrupt tick
  AX.mot.moveWith(x, max(1.0f, V * ux), max(1.0f, A * ux), jerk);
  AY.mot.moveWith(y, max(1.0f, V * uy), max(1.0f, A * uy), jerk);
  StepAxis::unlock();
  return true;
}

// ---------------------------------------------------------------- always-running protection
void heatGuard(float dt) {
  for (auto &a : axes) {
    float mA = !a.drv.enabled() ? 0 : a.mot.running() ? a.c->mA : a.c->mA * a.drv.holdPercent() / 100.0f;
    a.heat.update(mA, dt);
    float t = a.temp();
    if (t >= cfg.limitC && !a.hot) {
      a.hot = true;
      a.mot.halt(); a.drv.enable(false);
      if (busy) abortReq = true;
      event("HOT %s: about %.0f C - driver off until it cools", a.name, t);
    } else if (t >= cfg.warnC && !a.warm) {
      a.warm = true;
      a.drv.setHoldPercent(min<uint8_t>(a.c->hold, 20));
      event("warm %s: about %.0f C - standing current lowered to 20%%", a.name, t);
    }
    if (a.hot && t < cfg.warnC - 5) {
      a.hot = false; a.sleeping = true;        // driver comes back on with the next move
      event("cooled %s: about %.0f C - can move again", a.name, t);
    }
    if (a.warm && t < cfg.warnC - 10) {
      a.warm = false;
      a.drv.setHoldPercent(a.c->hold);
    }
  }
}

uint8_t telemetryNext = 0, loadNext = 0;
uint32_t lastTelemetry = 0, lastLoad = 0, lastHeat = 0;
void printJson();

void service() {
  uint32_t now = millis();
  loopCount++;
  if (now - loopT0 >= 1000) { loopHz = loopCount * 1000 / (now - loopT0); loopCount = 0; loopT0 = now; }
  if (anyMoving()) {
    if (now - lastLoad >= LOAD_MS) {                 // crash detection: load of the moving motors, one per call
      lastLoad = now;
      for (int k = 0; k < 3; k++) {
        Axis &a = axes[(loadNext + k) % 3];
        if (!a.mot.running() || !a.ok) continue;
        loadNext = (loadNext + k + 1) % 3;
        if (a.drv.readLoad(a.sg) && a.crash.sample(a.sg, a.mot.speed())) onCrash(a);
        break;
      }
    }
  } else if (now - lastTelemetry >= TELEMETRY_MS) {
    lastTelemetry = now;
    readTelemetry(axes[telemetryNext]);
    telemetryNext = (telemetryNext + 1) % 3;
  }
  if (now - lastHeat >= 100) { heatGuard((now - lastHeat) / 1000.0f); lastHeat = now; }
  for (auto &a : axes) {                             // idle timer
    if (a.mot.running()) a.lastActive = now;
    else if (cfg.idleS && a.drv.enabled() && !a.sleeping && now - a.lastActive > cfg.idleS * 1000UL) {
      a.drv.enable(false); a.sleeping = true;
      event("idle %s: not used for %lu s, driver off", a.name, (unsigned long)cfg.idleS);
    }
  }
  if (streamMs && now - lastStream >= streamMs) { lastStream = now; printJson(); }
  if (wdMs && !wdTripped && now - lastCmd > wdMs) {  // laptop silent: stop everything
    stopAll(); wdTripped = true;
    if (busy) abortReq = true;
    event("watchdog: no ping, motors stopped");
  }
}

// while a long command runs: answer ping / json, "stop" aborts, everything else is refused
void busyPoll() {
  if (!con.poll()) return;
  lastCmd = millis();
  if (con.is(0, "ping")) { wdTripped = false; con.reply("pong"); }
  else if (con.is(0, "json")) printJson();
  else if (con.is(0, "stop")) { stopAll(); abortReq = true; con.reply("ok stop"); }
  else con.reply("err busy (%s) - send stop to abort", busy);
}

bool waitMoves() {                            // false = aborted (stop, watchdog, crash, heat)
  while (anyMoving()) { service(); busyPoll(); if (abortReq) { stopAll(); break; } }
  while (anyMoving()) { service(); busyPoll(); }
  return !abortReq;
}
bool waitMs(uint32_t ms) {
  uint32_t t = millis();
  while (millis() - t < ms) { service(); busyPoll(); }
  return !abortReq;
}

// ---------------------------------------------------------------- status output
void printJson() {
  Serial.printf("{\"t\":%lu,\"wd\":%lu,\"wdtrip\":%d,\"idle\":%lu,\"heap\":%lu,\"heapmin\":%lu,\"heapsize\":%lu,"
                "\"loop\":%lu,\"ctemp\":%.1f,\"vbat\":%.2f,\"drive\":%d,\"busy\":\"%s\",\"prof\":\"%s\",\"crashes\":%lu,"
                "\"warn\":%u,\"limit\":%u,\"ax\":[",
                (unsigned long)millis(), (unsigned long)wdMs, wdTripped ? 1 : 0, (unsigned long)cfg.idleS * 1000UL,
                (unsigned long)ESP.getFreeHeap(), (unsigned long)ESP.getMinFreeHeap(), (unsigned long)ESP.getHeapSize(),
                (unsigned long)loopHz, temperatureRead(), batteryVolts(), drivePowerOn() ? 1 : 0, busy ? busy : "",
                profileName, (unsigned long)crashes, cfg.warnC, cfg.limitC);
  for (int i = 0; i < 3; i++) {
    Axis &a = axes[i];
    uint32_t s = a.drvStatus;
    int temp = (s & (1UL << 11)) ? 157 : (s & (1UL << 10)) ? 150 : (s & (1UL << 9)) ? 143 : (s & (1UL << 8)) ? 120 : 0;
    Serial.printf("%s{\"n\":\"%s\",\"pos\":%ld,\"tgt\":%ld,\"run\":%d,\"ok\":%d,\"on\":%d,\"mA\":%u,\"inv\":%d,\"sleep\":%d,"
                  "\"spd\":%lu,\"acc\":%lu,\"jerk\":%u,\"v\":%lu,\"hold\":%u,\"mt\":%.1f,\"warm\":%d,\"hot\":%d,\"lost\":%d,"
                  "\"cpct\":%u,\"sgavg\":%u,"
                  "\"sg\":%u,\"cs\":%lu,\"otpw\":%d,\"ot\":%d,\"s2g\":%d,\"ol\":%d,\"temp\":%d}",
                  i ? "," : "", a.name, (long)a.mot.position(), (long)a.mot.target(), a.mot.running() ? 1 : 0,
                  a.ok ? 1 : 0, a.drv.enabled() ? 1 : 0, a.c->mA, a.mot.inverted() ? 1 : 0, a.sleeping ? 1 : 0,
                  (unsigned long)a.c->spd, (unsigned long)a.c->acc, a.c->jerk, (unsigned long)a.mot.speed(),
                  a.drv.holdPercent(), a.temp(), a.warm ? 1 : 0, a.hot ? 1 : 0, a.lost ? 1 : 0,
                  a.c->crashPct, a.crash.average(),
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
    Serial.printf("  %u mA (hold %u%%)  on %s  load %u  %s%s%s%s", a.c->mA, a.drv.holdPercent(),
                  a.drv.enabled() ? "yes" : "no", a.sg,
                  (ds & (1UL << 1)) ? "OVERTEMP " : "", (ds & (1UL << 0)) ? "PRE-WARN " : "",
                  (ds & (3UL << 2)) ? "SHORT-GND " : "", (ds & (3UL << 6)) ? "OPEN-LOAD " : "");
  }
  Serial.printf("\r\n     speed %lu accel %lu jerk %u ms  pos %ld%s  motor ~%.0f C%s%s  crash at %u%%\r\n",
                (unsigned long)a.c->spd, (unsigned long)a.c->acc, a.c->jerk, (long)a.mot.position(),
                a.lost ? " (NOT TRUSTED)" : "", a.temp(), a.hot ? " HOT" : a.warm ? " warm" : "",
                a.sleeping ? "  sleeping" : "", a.c->crashPct);
}

// ---------------------------------------------------------------- checks
void pulses(Axis &a, long n, long us) {       // plain even step pulses from here (no timer, no acceleration)
  digitalWrite(a.dirPin, (n > 0) != a.mot.inverted() ? HIGH : LOW);
  delayMicroseconds(50);
  for (long i = 0; i < labs(n); i++) {
    digitalWrite(a.stepPin, HIGH); delayMicroseconds(5);
    digitalWrite(a.stepPin, LOW);  delayMicroseconds(us);
  }
  a.mot.setInvert(a.mot.inverted());          // put the DIR pin back where StepGen expects it
}

// does the driver see our STEP and DIR pins? (IOIN bit 7 STEP, bit 9 DIR). Returns the number of wrong lines.
int pinCheck(Axis &a, bool print) {
  struct { const char *what; uint8_t pin; int level; uint8_t bit; } t[] = {
    {"STEP high", a.stepPin, HIGH, 7}, {"STEP low ", a.stepPin, LOW, 7},
    {"DIR high ", a.dirPin, HIGH, 9}, {"DIR low  ", a.dirPin, LOW, 9}};
  int wrong = 0;
  for (auto &c : t) {
    digitalWrite(c.pin, c.level); delay(2);
    uint32_t v;
    bool ok = a.drv.readReg(Tmc2209::IOIN, v);
    bool bad = !ok || (((v >> c.bit) & 1) != (c.level == HIGH));
    wrong += bad;
    if (print) Serial.printf("  GPIO%-2u %s -> driver sees %s%s\r\n", c.pin, c.what,
                             ok ? ((v >> c.bit) & 1 ? "HIGH" : "LOW") : "no answer", bad ? "   <-- WRONG" : "");
  }
  a.mot.setInvert(a.mot.inverted());
  return wrong;
}

int fails, warns;
void result(int level, const char *fmt, ...) {   // level 0 PASS, 1 WARN, 2 FAIL
  char b[140];
  va_list ap; va_start(ap, fmt); vsnprintf(b, sizeof b, fmt, ap); va_end(ap);
  Serial.printf("  %s  %s\r\n", level == 0 ? "PASS" : level == 1 ? "WARN" : "FAIL", b);
  if (level == 1) warns++;
  if (level == 2) fails++;
}

// one command that checks everything that can be checked from the board (laptop adds the camera)
void selfTest() {
  fails = warns = 0;
  Serial.print("self-test\r\n");
  float v = batteryVolts();
  bool power = drivePowerOn();
  result(power ? 0 : 2, "drive power (stop button sense): %s", power ? "on" : "OFF - stop button pressed or battery off");
  result(v >= 14.8f ? 0 : v >= VBAT_MIN ? 1 : 2, "battery %.2f V (4S: full 16.8, stop below %.1f)", v, VBAT_MIN);
  result(ESP.getFreeHeap() > 100000 ? 0 : 1, "RAM free %lu bytes", (unsigned long)ESP.getFreeHeap());
  result(temperatureRead() < 65 ? 0 : 1, "ESP32 chip %.0f C", temperatureRead());
  result(crashedLastTime() ? 1 : 0, "last restart: %s%s", resetReason(), crashedLastTime() ? " (see: log crash)" : "");
  for (auto &a : axes) {
    readTelemetry(a);
    if (!a.ok) { result(2, "[%s] driver does not answer on UART address %u", a.name, a.addr); continue; }
    result(0, "[%s] driver answers (address %u)", a.name, a.addr);
    uint32_t g = 0, ch = 0;
    a.drv.readReg(Tmc2209::GCONF, g);
    a.drv.readReg(Tmc2209::CHOPCONF, ch);
    bool cfgOk = (g & 0x1C5) == 0x1C0 && ((ch >> 24) & 0xF) == 4;
    result(cfgOk ? 0 : 2, "[%s] settings arrived (GCONF 0x%03lX, 16 microsteps %s)", a.name, (unsigned long)g,
           ((ch >> 24) & 0xF) == 4 ? "yes" : "NO");
    int wrong = pinCheck(a, false);
    result(wrong ? 2 : 0, "[%s] driver sees STEP and DIR from GPIO %u / %u%s", a.name, a.stepPin, a.dirPin,
           wrong ? " - NO: cable / plug crossed? (pins x)" : "");
    bool wasOn = a.drv.enabled();
    if (!wasOn) { a.drv.enable(true); delay(5); }
    uint32_t m0 = 0, m1 = 0, m2 = 0;
    a.drv.readReg(0x6A, m0); pulses(a, 16, 1500); a.drv.readReg(0x6A, m1);
    pulses(a, -16, 1500); a.drv.readReg(0x6A, m2);
    if (!wasOn) a.drv.enable(false);
    uint32_t d = (m1 - m0) & 1023;
    result((d == 256 || d == 768) && m2 == m0 ? 0 : 2, "[%s] driver counts our steps (16 steps -> %lu of 256, back %s)",
           a.name, (unsigned long)(d == 768 ? 256 : d), m2 == m0 ? "ok" : "WRONG");
    uint32_t s = a.drvStatus;
    if (s & (3UL << 2)) result(2, "[%s] SHORT to ground on a motor wire", a.name);
    if (s & 2) result(2, "[%s] driver OVERHEATED", a.name);
    result(a.temp() < cfg.warnC ? 0 : 1, "[%s] motor about %.0f C (estimate)", a.name, a.temp());
    if (a.lost) result(1, "[%s] position not trusted (crash / off): home it", a.name);
  }
  pinMode(PIN_X_HOME, INPUT_PULLUP); pinMode(PIN_Y_HOME, INPUT_PULLUP);
  result(0, "home switches: X %s, Y %s (pressed = at home or broken wire)",
         digitalRead(PIN_X_HOME) ? "free" : "PRESSED", digitalRead(PIN_Y_HOME) ? "free" : "PRESSED");
  BlackBox::add("selftest: %d fail, %d warn", fails, warns);
  if (fails) con.reply("err selftest FAIL %d, WARN %d", fails, warns);
  else con.reply("ok selftest PASS (%d warnings)", warns);
}

// auto-tune: faster and faster back-and-forth moves until the load reading shows the motor slipping;
// then the same for the acceleration. Uses 70 % of the last good values. The axis needs `dist` steps of room.
void tune(Axis &a, long dist) {
  Cfg::Ax keep = *a.c;
  uint8_t keepPct = a.crash.pct;
  a.crash.pct = 40;
  long start = a.mot.position();
  uint32_t goodSpd = 0, goodAcc = 0;
  bool stalled = false;
  Serial.printf("tune %s: back and forth over %ld steps, speed first (send stop to abort)\r\n", a.name, dist);
  for (uint32_t s = 1600; s <= StepAxis::MAX_SPEED && !abortReq; s += 1600) {
    a.mot.setMaxSpeed(s);
    if (!prepMove(a)) break;
    a.mot.moveTo(start + dist);
    bool ok = waitMoves();
    Serial.printf("  speed %5lu  load normal %3u, lowest %3u  %s\r\n", (unsigned long)s, a.crash.average(),
                  a.crash.minSeen, ok ? "ok" : "SLIPPED / stopped");
    if (!ok) { stalled = true; break; }
    goodSpd = s;
    prepMove(a); a.mot.moveTo(start);
    if (!waitMoves()) { stalled = true; break; }
  }
  bool aborted = abortReq && !stalled;
  abortReq = false;
  a.mot.setMaxSpeed(keep.spd);                // slowly back to the start, whatever happened
  if (a.mot.position() != start) { a.lost = false; prepMove(a); a.mot.moveTo(start); waitMoves(); }
  uint32_t useSpd = goodSpd ? goodSpd * 7 / 10 : keep.spd;
  if (!aborted && goodSpd) {
    Serial.printf("acceleration at speed %lu\r\n", (unsigned long)useSpd);
    a.mot.setMaxSpeed(useSpd);
    for (uint32_t ac = 3200; ac <= 204800 && !abortReq; ac *= 2) {
      a.mot.setAccel(ac);
      prepMove(a); a.mot.moveTo(start + dist);
      bool ok = waitMoves();
      Serial.printf("  accel %6lu  load lowest %3u  %s\r\n", (unsigned long)ac, a.crash.minSeen, ok ? "ok" : "SLIPPED / stopped");
      if (!ok) break;
      goodAcc = ac;
      prepMove(a); a.mot.moveTo(start);
      if (!waitMoves()) break;
    }
    abortReq = false;
    a.mot.setAccel(keep.acc);
    if (a.mot.position() != start) { a.lost = false; prepMove(a); a.mot.moveTo(start); waitMoves(); }
  }
  a.crash.pct = keepPct;
  if (aborted || !goodSpd) {
    *a.c = keep; applyAxis(a);
    con.reply("err tune %s %s - settings unchanged", a.name, aborted ? "aborted" : "found nothing that works");
    return;
  }
  a.c->spd = useSpd;
  a.c->acc = goodAcc ? goodAcc * 7 / 10 : keep.acc;
  applyAxis(a);
  Serial.printf("  %s\r\n", stalled ? "slipped above the last good speed" :
                "no slip up to the maximum: the limit is the firmware's 16000 steps/s, not the motor");
  BlackBox::add("tune %s: speed %lu accel %lu", a.name, (unsigned long)a.c->spd, (unsigned long)a.c->acc);
  con.reply("ok tune %s speed %lu accel %lu (70%% of the last good; 'save' keeps them)", a.name,
            (unsigned long)a.c->spd, (unsigned long)a.c->acc);
}

// ---------------------------------------------------------------- commands
void help() {
  Serial.print(
    "\r\nCommands (axis = x, y or w):\r\n"
    "  status              each driver: answers? current, flags, position, motor temperature\r\n"
    "  m <axis> <steps>    move relative, 3200 steps = 1 turn (16 microsteps)\r\n"
    "  r <axis> <turns>    move relative in turns (can be 0.5, -2 ...)\r\n"
    "  g <axis> <steps>    go to an absolute position\r\n"
    "  line <x> <y>        X and Y together in a straight line to absolute steps (arrive at the same time)\r\n"
    "  zero <axis>         call the present position 0 (also: position trusted again)\r\n"
    "  test                each motor: 1 turn forward, 1 back, one after another\r\n"
    "  all <turns>         all three motors at once\r\n"
    "  stop                stop all motors (decelerate); also aborts a long command\r\n"
    "settings (each motor its own; 'save' keeps them in flash):\r\n"
    "  speed [axis] <steps/s>   max speed (up to 16000);  accel [axis] <steps/s^2>\r\n"
    "  jerk [axis] <ms>    S-curve: acceleration builds up over this time (0 = trapezoid); gentle on a stack\r\n"
    "  cur <axis> <mA>     RMS current (limited to the motor's rating);  hold <axis> <%>  current standing\r\n"
    "  dir <axis>          reverse this motor's direction (when it stands)\r\n"
    "  idle <s>            driver off after s seconds standing (0 = never); wakes by itself\r\n"
    "  crash [axis] <%>    stop everything if the load falls below this % of normal (0 = off)\r\n"
    "  heat [axis <rated mA> <tau s>] | heat limits <warn C> <off C>   motor heat model\r\n"
    "  save [name] | load [name] | profiles | forget <name> | defaults   (no name = 'boot', loaded at power-on)\r\n"
    "protection and checks:\r\n"
    "  selftest            check everything: power, battery, drivers, pins, step counting, switches\r\n"
    "  tune <axis> [steps] find the fastest reliable speed and acceleration (needs that much room)\r\n"
    "  log | log crash | log clear   black box: last 64 events (crash copy survives power-off)\r\n"
    "  mem                 ESP32 memory, CPU, temperature, uptime, why it last restarted\r\n"
    "  on <axis> / off <axis>   driver output on / off (off = motor turns freely)\r\n"
    "  pulse <axis> <steps> [us] | reg <axis> | pins <axis>   low-level driver checks\r\n"
    "  for programs: json | stream <ms> | wd <ms> | ping | echo 0/1\r\n");
}

void listProfile(const char *name) { if (strcmp(name, "crashlog")) Serial.printf("  %s\r\n", name); }

// "speed 3200" = all motors, "speed x 3200" = only X; same shape for accel, jerk, crash
bool perAxisSetting(const char *what) {
  Axis *one = findAxis(con.word(1));
  long v = con.argInt(one ? 2 : 1);
  for (auto &a : axes) {
    if (one && one != &a) continue;
    Cfg::Ax &c = *a.c;
    if (!strcmp(what, "speed")) c.spd = constrain(v, 50L, (long)StepAxis::MAX_SPEED);
    else if (!strcmp(what, "accel")) c.acc = constrain(v, 100L, 400000L);
    else if (!strcmp(what, "jerk")) c.jerk = constrain(v, 0L, 500L);
    else if (!strcmp(what, "crash")) c.crashPct = constrain(v, 0L, 90L);
    applyAxis(a);
  }
  Axis &shown = one ? *one : axes[0];
  long val = !strcmp(what, "speed") ? shown.c->spd : !strcmp(what, "accel") ? shown.c->acc
           : !strcmp(what, "jerk") ? shown.c->jerk : shown.c->crashPct;
  con.reply("ok %s %s %ld", what, one ? one->name : "all", val);
  return true;
}

void command() {
  lastCmd = millis();
  if (con.is(0, "ping")) { wdTripped = false; con.reply("pong"); return; }
  if (con.is(0, "json")) { printJson(); return; }
  if (!con.is(0, "log")) BlackBox::add("> %s %s %s", con.word(0), con.word(1), con.word(2));
  if (con.is(0, "stream")) { streamMs = con.argInt(1); con.reply("ok stream %lu", (unsigned long)streamMs); return; }
  if (con.is(0, "wd")) { wdMs = con.argInt(1); wdTripped = false; con.reply("ok wd %lu", (unsigned long)wdMs); return; }
  if (con.is(0, "echo")) { con.setEcho(con.argInt(1) != 0); con.reply("ok echo %d", con.echo() ? 1 : 0); return; }
  if (con.is(0, "help") || con.is(0, "?")) { help(); return; }
  if (con.is(0, "status")) { for (auto &a : axes) printStatus(a); return; }
  if (con.is(0, "mem")) { printMem(); return; }
  if (con.is(0, "stop")) { stopAll(); con.reply("ok stop"); return; }
  if (con.is(0, "idle")) { cfg.idleS = con.argInt(1); con.reply("ok idle %lu", (unsigned long)cfg.idleS); return; }
  if (con.is(0, "speed") || con.is(0, "accel") || con.is(0, "jerk") || con.is(0, "crash")) {
    if (con.is(0, "crash") && con.words() == 1) {
      for (auto &a : axes) Serial.printf("  [%s] stop below %u%% of normal load (normal now %u), crashes so far %lu\r\n",
                                         a.name, a.c->crashPct, a.crash.average(), (unsigned long)crashes);
      return;
    }
    perAxisSetting(con.word(0)); return;
  }
  if (con.is(0, "heat")) {
    if (con.is(1, "limits")) {
      cfg.warnC = constrain(con.argInt(2), 40L, 120L); cfg.limitC = constrain(con.argInt(3), cfg.warnC + 5L, 130L);
      con.reply("ok heat limits warn %u off %u", cfg.warnC, cfg.limitC); return;
    }
    Axis *a = findAxis(con.word(1));
    if (a && con.words() >= 4) {
      a->c->ratedmA = constrain(con.argInt(2), 100L, 3000L); a->c->tau = constrain(con.argInt(3), 30L, 7200L);
      applyAxis(*a);
    }
    for (auto &x : axes)
      Serial.printf("  [%s] motor ~%.1f C (rated %u mA, tau %u s, running %u mA, standing %u%%)%s\r\n", x.name, x.temp(),
                    x.c->ratedmA, x.c->tau, x.c->mA, x.drv.holdPercent(), x.hot ? " HOT" : x.warm ? " warm" : "");
    con.reply("ok heat (warn %u C: standing current to 20%%, %u C: driver off)", cfg.warnC, cfg.limitC);
    return;
  }
  if (con.is(0, "save")) {
    const char *n = con.words() > 1 ? con.word(1) : "boot";
    if (strlen(n) > 15 || !strcmp(n, "crashlog")) { con.reply("err name: up to 15 letters, not crashlog"); return; }
    bool ok = Settings::save(n, &cfg, sizeof cfg);
    if (ok) strlcpy(profileName, n, sizeof profileName);
    con.reply(ok ? "ok save %s" : "err save %s failed", n); return;
  }
  if (con.is(0, "load")) {
    const char *n = con.words() > 1 ? con.word(1) : "boot";
    if (anyMoving()) { con.reply("err stop the motors first"); return; }
    con.reply(loadProfile(n) ? "ok load %s" : "err no profile %s (see: profiles)", n); return;
  }
  if (con.is(0, "defaults")) {
    if (anyMoving()) { con.reply("err stop the motors first"); return; }
    cfg = DEFAULTS; strlcpy(profileName, "defaults", sizeof profileName); applyAll();
    con.reply("ok defaults (not saved: 'save' to make them the power-on settings)"); return;
  }
  if (con.is(0, "profiles")) { Settings::list(listProfile); con.reply("ok profiles (now: %s)", profileName); return; }
  if (con.is(0, "forget")) { con.reply(Settings::remove(con.word(1)) ? "ok forget %s" : "err no profile %s", con.word(1)); return; }
  if (con.is(0, "log")) {
    if (con.is(1, "clear")) { BlackBox::clear(); con.reply("ok log clear"); return; }
    if (con.is(1, "crash")) {
      static BlackBox::Log l;                  // 3 kB: not on the stack
      if (!Settings::load("crashlog", &l, sizeof l)) { con.reply("ok log crash: no crash recorded"); return; }
      Serial.print("black box copied after the last crash:\r\n");
      BlackBox::print(Serial, &l);
      con.reply("ok log crash"); return;
    }
    Serial.printf("black box (boot no. %lu now):\r\n", (unsigned long)BlackBox::boots());
    BlackBox::print(Serial);
    con.reply("ok log"); return;
  }
  if (con.is(0, "selftest")) {
    if (anyMoving()) { con.reply("err stop the motors first"); return; }
    busy = "selftest"; abortReq = false; selfTest(); busy = nullptr; return;
  }
  if (con.is(0, "test")) {
    busy = "test"; abortReq = false;
    for (auto &a : axes) {
      Serial.printf("[%s] 1 turn forward, 1 back\r\n", a.name);
      if (!prepMove(a)) continue;
      a.mot.move(STEPS_PER_REV);  if (!waitMoves()) break;
      waitMs(300);
      a.mot.move(-STEPS_PER_REV); if (!waitMoves()) break;
      waitMs(300);
    }
    busy = nullptr;
    con.reply(abortReq ? "err test stopped" : "ok test"); abortReq = false; return;
  }
  if (con.is(0, "all")) {
    long s = lroundf(con.argFloat(1) * STEPS_PER_REV);
    for (auto &a : axes) if (prepMove(a)) a.mot.move(s);
    con.reply("ok all"); return;
  }
  if (con.is(0, "line")) {
    if (con.words() < 3) { con.reply("err line <x steps> <y steps>"); return; }
    con.reply(lineTo(con.argInt(1), con.argInt(2)) ? "ok line" : "err line"); return;
  }

  Axis *a = findAxis(con.word(1));
  if (!a) { con.reply("err unknown command or axis - type help"); return; }
  if (con.is(0, "m"))    { if (prepMove(*a)) { a->mot.move(con.argInt(2)); con.reply("ok m %s", a->name); } return; }
  if (con.is(0, "r"))    { if (prepMove(*a)) { a->mot.move(lroundf(con.argFloat(2) * STEPS_PER_REV)); con.reply("ok r %s", a->name); } return; }
  if (con.is(0, "g"))    { if (prepMove(*a)) { a->mot.moveTo(con.argInt(2)); con.reply("ok g %s", a->name); } return; }
  if (con.is(0, "zero")) { a->mot.setPosition(0); a->lost = false; con.reply("ok zero %s", a->name); return; }
  if (con.is(0, "tune")) {
    if (anyMoving()) { con.reply("err stop the motors first"); return; }
    busy = "tune"; abortReq = false;
    tune(*a, con.words() > 2 ? constrain(con.argInt(2), 400L, 100000L) : STEPS_PER_REV);
    busy = nullptr; abortReq = false; return;
  }
  if (con.is(0, "cur"))  {
    uint16_t mA = constrain(con.argInt(2), 100L, (long)a->c->ratedmA);
    a->c->mA = mA; applyAxis(*a);
    con.reply("ok cur %s %u%s", a->name, mA, con.argInt(2) > a->c->ratedmA ? " (limited to the motor's rating)" : ""); return;
  }
  if (con.is(0, "hold")) {
    a->c->hold = constrain(con.argInt(2), 0L, 100L); applyAxis(*a);
    con.reply("ok hold %s %u", a->name, a->c->hold); return;
  }
  if (con.is(0, "on"))   {
    if (a->hot) { con.reply("err %s too hot", a->name); return; }
    a->drv.enable(true); a->sleeping = false; a->lastActive = millis(); con.reply("ok on %s", a->name); return;
  }
  if (con.is(0, "off"))  { a->mot.halt(); a->drv.enable(false); a->sleeping = false; a->lost = true; con.reply("ok off %s", a->name); return; }
  if (con.is(0, "dir"))  {
    if (a->mot.running()) { con.reply("err %s is moving - stop it first", a->name); return; }
    a->c->inv = !a->c->inv; applyAxis(*a); con.reply("ok dir %s %d", a->name, a->c->inv); return;
  }
  if (con.is(0, "pulse")) {
    if (a->mot.running()) { con.reply("err motor moving"); return; }
    long us = con.words() > 3 ? constrain(con.argInt(3), 100L, 100000L) : 1000L;   // 1000 us = 1000 steps/s
    pulses(*a, con.argInt(2), us);
    con.reply("ok pulse %s %ld", a->name, con.argInt(2)); return;
  }
  if (con.is(0, "pins")) {
    if (a->mot.running()) { con.reply("err motor moving"); return; }
    int w = pinCheck(*a, true);
    con.reply(w ? "err pins %s: %d wrong" : "ok pins %s", a->name, w); return;
  }
  if (con.is(0, "reg")) {
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
    con.reply("ok reg %s", a->name); return;
  }
  con.reply("err unknown command - type help");
}

// ---------------------------------------------------------------- main
void setup() {
  Serial.setTxBufferSize(4096);           // status lines go out in the background
  Serial.begin(115200);
  delay(500);
  BlackBox::begin();
  Settings::begin();
  Serial.print("\r\nETZ plotter firmware v4 (X, Y, wrist), no outside libraries. Radio is never started.\r\n");
  Serial.printf("last reset: %s, boot no. %lu\r\n", resetReason(), (unsigned long)BlackBox::boots());
  if (crashedLastTime()) {                 // keep the black box from before the crash, also through a power-off
    Settings::save("crashlog", &BlackBox::live(), sizeof(BlackBox::Log));
    Serial.print("the last run ended in a crash / brownout: 'log crash' shows what happened before it\r\n");
  }
  BlackBox::add("boot: %s", resetReason());
  pinMode(PIN_STOP_SENSE, INPUT);
  for (int i = 0; i < 3; i++) axes[i].c = &cfg.ax[i];
  if (loadProfile("boot")) Serial.print("settings: profile 'boot' from flash\r\n");
  else Serial.print("settings: defaults (nothing saved yet)\r\n");
  Serial2.begin(115200, SERIAL_8N1, PIN_TMC_RX, PIN_TMC_TX);
  delay(50);
  StepAxis *motors[3];
  for (int i = 0; i < 3; i++) {
    Axis &a = axes[i];
    motors[i] = &a.mot;
    a.ok = a.drv.begin(a.c->mA, MICROSTEPS);
    applyAxis(a);
    Serial.printf("[%s] UART address %u: %s\r\n", a.name, a.addr,
                  a.ok ? "driver answered, configured" : "NO ANSWER (is the battery / drive power on? cable? address?)");
  }
  if (!StepAxis::begin(motors, 3)) Serial.print("err step timer did not start\r\n");
  Serial.print("type help for the commands\r\n");
  lastCmd = millis();
  for (auto &a : axes) a.lastActive = millis();
  con.prompt();
}

void loop() {
  if (con.poll()) { command(); con.prompt(); }
  service();
}
