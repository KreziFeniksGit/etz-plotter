#include "StepGen.h"
#include "soc/gpio_reg.h"

StepAxis *StepAxis::axes_[4];
uint8_t StepAxis::count_ = 0;
static portMUX_TYPE stepMux = portMUX_INITIALIZER_UNLOCKED;   // main code and the interrupt never change an axis at once
static hw_timer_t *stepTimer = nullptr;

// direct GPIO register writes: fast and safe inside the interrupt
static inline void IRAM_ATTR pinsHigh(bool bank1, uint32_t mask) { REG_WRITE(bank1 ? GPIO_OUT1_W1TS_REG : GPIO_OUT_W1TS_REG, mask); }
static inline void IRAM_ATTR pinsLow(bool bank1, uint32_t mask) { REG_WRITE(bank1 ? GPIO_OUT1_W1TC_REG : GPIO_OUT_W1TC_REG, mask); }

static uint32_t IRAM_ATTR isqrt64(uint64_t n) {        // integer square root (bit by bit)
  uint64_t r = 0, bit = 1ULL << 62;
  while (bit > n) bit >>= 2;
  while (bit) {
    if (n >= r + bit) { n -= r + bit; r = (r >> 1) + bit; }
    else r >>= 1;
    bit >>= 2;
  }
  return (uint32_t)r;
}

// Steps needed to stop from speed v with acceleration a (S-curve: a must first ramp down to -A).
// Units: v in steps/tick * 2^32, a and A in that per tick, J in that per tick^2. Result in steps.
static uint32_t IRAM_ATTR stopDistance(uint32_t v, int32_t a, uint32_t A, uint32_t J) {
  if (!J) return (uint32_t)(((uint64_t)v * v / A) >> 33);          // trapezoid: v^2 / 2A
  uint64_t s = 0, vv = v;
  if (a > 0) {                                                       // still speeding up: ramp a down to 0 first
    uint64_t t1 = (uint64_t)a / J;
    s = vv * t1 + (uint64_t)a * t1 * t1 / 2 - (uint64_t)J * t1 * t1 * t1 / 6;
    vv += (uint64_t)a * a / (2 * J);
  }
  if (vv * J >= (uint64_t)A * A) s += vv * (vv / A + A / J) / 2;     // reaches full deceleration
  else s += vv * isqrt64(vv / J);                                    // short: deceleration ramps up and down only
  return (uint32_t)(s >> 32);
}

// speed units: steps/tick * 2^32, so a step happens each time the 32-bit phase overflows
StepAxis::Profile StepAxis::profile(uint32_t sps, uint32_t acc, uint32_t rampMs) {
  Profile p;
  if (sps > MAX_SPEED) sps = MAX_SPEED;
  if (sps < 1) sps = 1;
  if (acc < 1) acc = 1;
  p.vmax = (uint32_t)(((uint64_t)sps << 32) / TICK_HZ);
  uint32_t d = (uint32_t)(((uint64_t)acc << 32) / ((uint64_t)TICK_HZ * TICK_HZ));
  p.dvel = d ? d : 1;
  uint32_t rampTicks = rampMs * (TICK_HZ / 1000);
  p.djerk = rampTicks ? (p.dvel / rampTicks ? p.dvel / rampTicks : 1) : 0;
  return p;
}

void StepAxis::setMaxSpeed(uint32_t sps) { sps_ = sps > MAX_SPEED ? MAX_SPEED : sps; }
void StepAxis::setAccel(uint32_t a) { acc_ = a; }
void StepAxis::setJerk(uint32_t ms) { rampMs_ = ms; }

uint32_t StepAxis::speed() const { return (uint32_t)(((uint64_t)vel_ * TICK_HZ) >> 32); }

void StepAxis::moveWith(int32_t t, uint32_t sps, uint32_t acc, uint32_t rampMs) {
  Profile p = profile(sps, acc, rampMs);
  portENTER_CRITICAL(&stepMux);
  vmax_ = p.vmax; dvel_ = p.dvel; djerk_ = p.djerk;
  target_ = t;
  portEXIT_CRITICAL(&stepMux);
}

void StepAxis::moveTo(int32_t t) { moveWith(t, sps_, acc_, rampMs_); }

void StepAxis::lock() { portENTER_CRITICAL(&stepMux); }
void StepAxis::unlock() { portEXIT_CRITICAL(&stepMux); }

void StepAxis::stop() {
  portENTER_CRITICAL(&stepMux);
  int32_t s = (int32_t)stopSteps_ + 1;
  int32_t ahead = fwd_ ? target_ - pos_ : pos_ - target_;   // steps to the old target in the running direction
  if (!vel_) target_ = pos_;
  else if (ahead <= 0 || ahead > s) target_ = pos_ + (fwd_ ? s : -s);   // else the old target is nearer: keep it
  portEXIT_CRITICAL(&stepMux);
}

void StepAxis::halt() {
  portENTER_CRITICAL(&stepMux);
  vel_ = 0; a_ = 0; phase_ = 0; stopSteps_ = 0; target_ = pos_; moving_ = false;
  portEXIT_CRITICAL(&stepMux);
}

void StepAxis::setPosition(int32_t p) {
  portENTER_CRITICAL(&stepMux);
  vel_ = 0; a_ = 0; phase_ = 0; stopSteps_ = 0; pos_ = p; target_ = p; moving_ = false;
  portEXIT_CRITICAL(&stepMux);
}

void StepAxis::setDirPin() {
  if (fwd_ != inv_) pinsHigh(highBank_, dirMask_);
  else pinsLow(highBank_, dirMask_);
}

void StepAxis::setInvert(bool inv) {
  portENTER_CRITICAL(&stepMux);
  inv_ = inv; setDirPin(); dirWait_ = 2;
  portEXIT_CRITICAL(&stepMux);
}

// one tick of one axis (inside the interrupt)
void IRAM_ATTR StepAxis::tick() {
  if (pulse_) { pinsLow(highBank_, stepMask_); pulse_ = false; }
  if (dirWait_) { dirWait_ = dirWait_ - 1; return; }   // DIR just changed: let it settle before a step
  int32_t rem = target_ - pos_;
  if (rem == 0) {                                     // at the target (arrives at crawl speed): stand
    vel_ = 0; a_ = 0; phase_ = 0; stopSteps_ = 0; moving_ = false;
    return;
  }
  if (vel_ == 0 && (rem > 0) != fwd_) {               // standing and the target is behind: turn DIR round
    fwd_ = rem > 0; setDirPin(); dirWait_ = 2;
    return;
  }
  moving_ = true;
  uint32_t left = rem > 0 ? rem : -rem;
  bool towards = (rem > 0) == fwd_;                   // false = target moved behind us: brake, then reverse
  uint32_t v = vel_, vmax = vmax_, dv = dvel_, dj = djerk_;
  int want;                                           // -1 brake, 0 hold speed, +1 speed up
  if (!towards || stopSteps_ >= left || v > vmax) want = -1;
  else if (v >= vmax) want = 0;
  else want = 1;
  if (!dj) {                                          // trapezoid
    if (want < 0) v = v > dv ? v - dv : 0;
    else if (want > 0) { v += dv; if (v > vmax) v = vmax; }
  } else {                                            // S-curve: the acceleration moves towards its goal by dj
    int32_t a = a_;
    if (want > 0 && a > 0 && v + (uint64_t)a * a / (2 * dj) >= vmax) want = 0;   // ease into the cruise speed
    int32_t goal = want * (int32_t)dv;
    if (a < goal) { a += dj; if (a > goal) a = goal; }
    else if (a > goal) { a -= dj; if (a < goal) a = goal; }
    if (a >= 0) { v += a; if (v > vmax && want >= 0) v = vmax; }
    else { uint32_t d = -a; v = v > d ? v - d : 0; }
    if (v == 0) a = 0;
    a_ = a;
  }
  vel_ = v;
  if (v == 0) { stopSteps_ = 0; return; }
  uint32_t old = phase_;
  phase_ = old + v;
  if (phase_ < old) {                                 // overflow: one step
    pinsHigh(highBank_, stepMask_); pulse_ = true;
    pos_ = pos_ + (fwd_ ? 1 : -1);
    stopSteps_ = stopDistance(v, a_, dv, dj) + 1;
  }
}

void IRAM_ATTR StepAxis::isr() {
  portENTER_CRITICAL_ISR(&stepMux);
  for (uint8_t i = 0; i < count_; i++) axes_[i]->tick();
  portEXIT_CRITICAL_ISR(&stepMux);
}

bool StepAxis::begin(StepAxis **axes, uint8_t count) {
  if (count > 4) count = 4;
  for (uint8_t i = 0; i < count; i++) {
    StepAxis *a = axes[i];
    pinMode(a->stepPin_, OUTPUT); digitalWrite(a->stepPin_, LOW);
    pinMode(a->dirPin_, OUTPUT);
    a->highBank_ = a->stepPin_ >= 32;                 // both pins of an axis must be in the same bank
    a->stepMask_ = 1UL << (a->stepPin_ & 31);
    a->dirMask_ = 1UL << (a->dirPin_ & 31);
    a->setDirPin();
    Profile p = profile(a->sps_, a->acc_, a->rampMs_);
    a->vmax_ = p.vmax; a->dvel_ = p.dvel; a->djerk_ = p.djerk;
    axes_[i] = a;
  }
  count_ = count;
  stepTimer = timerBegin(1000000);                    // 1 MHz timer clock
  if (!stepTimer) return false;
  timerAttachInterrupt(stepTimer, &StepAxis::isr);
  timerAlarm(stepTimer, 1000000 / TICK_HZ, true, 0);  // every 25 us, forever
  return true;
}
