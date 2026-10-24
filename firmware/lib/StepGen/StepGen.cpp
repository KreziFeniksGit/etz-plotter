#include "StepGen.h"
#include "soc/gpio_reg.h"

StepAxis *StepAxis::axes_[4];
uint8_t StepAxis::count_ = 0;
static portMUX_TYPE stepMux = portMUX_INITIALIZER_UNLOCKED;   // main code and the interrupt never change an axis at once
static hw_timer_t *stepTimer = nullptr;

// direct GPIO register writes: fast and safe inside the interrupt
static inline void IRAM_ATTR pinsHigh(bool bank1, uint32_t mask) { REG_WRITE(bank1 ? GPIO_OUT1_W1TS_REG : GPIO_OUT_W1TS_REG, mask); }
static inline void IRAM_ATTR pinsLow(bool bank1, uint32_t mask) { REG_WRITE(bank1 ? GPIO_OUT1_W1TC_REG : GPIO_OUT_W1TC_REG, mask); }

// speed units: steps/tick * 2^32, so a step happens each time the 32-bit phase overflows
void StepAxis::setMaxSpeed(uint32_t sps) {
  if (sps > MAX_SPEED) sps = MAX_SPEED;
  vmax_ = (uint32_t)(((uint64_t)sps << 32) / TICK_HZ);
}

void StepAxis::setAccel(uint32_t a) {
  uint32_t d = (uint32_t)(((uint64_t)a << 32) / ((uint64_t)TICK_HZ * TICK_HZ));
  dvel_ = d ? d : 1;
}

uint32_t StepAxis::speed() const { return (uint32_t)(((uint64_t)vel_ * TICK_HZ) >> 32); }

void StepAxis::moveTo(int32_t t) { target_ = t; }

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
  vel_ = 0; phase_ = 0; stopSteps_ = 0; target_ = pos_; moving_ = false;
  portEXIT_CRITICAL(&stepMux);
}

void StepAxis::setPosition(int32_t p) {
  portENTER_CRITICAL(&stepMux);
  vel_ = 0; phase_ = 0; stopSteps_ = 0; pos_ = p; target_ = p; moving_ = false;
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
  if (dirWait_) { dirWait_ = dirWait_ - 1; return; }               // DIR just changed: let it settle before a step
  int32_t rem = target_ - pos_;
  if (rem == 0) {                                     // at the target (arrives at crawl speed): stand
    vel_ = 0; phase_ = 0; stopSteps_ = 0; moving_ = false;
    return;
  }
  if (vel_ == 0 && (rem > 0) != fwd_) {               // standing and the target is behind: turn DIR round
    fwd_ = rem > 0; setDirPin(); dirWait_ = 2;
    return;
  }
  moving_ = true;
  uint32_t left = rem > 0 ? rem : -rem;
  bool towards = (rem > 0) == fwd_;                   // false = target moved behind us: brake, then reverse
  uint32_t v = vel_;
  if (!towards || stopSteps_ >= left || v > vmax_) v = v > dvel_ ? v - dvel_ : 0;
  else if (v < vmax_) { v += dvel_; if (v > vmax_) v = vmax_; }
  vel_ = v;
  if (v == 0) { stopSteps_ = 0; return; }
  uint32_t old = phase_;
  phase_ = old + v;
  if (phase_ < old) {                                 // overflow: one step
    pinsHigh(highBank_, stepMask_); pulse_ = true;
    pos_ = pos_ + (fwd_ ? 1 : -1);
    stopSteps_ = (uint32_t)(((uint64_t)v * v / dvel_) >> 33);   // v^2 / (2 a), back in steps
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
    axes_[i] = a;
  }
  count_ = count;
  stepTimer = timerBegin(1000000);                    // 1 MHz timer clock
  if (!stepTimer) return false;
  timerAttachInterrupt(stepTimer, &StepAxis::isr);
  timerAlarm(stepTimer, 1000000 / TICK_HZ, true, 0);  // every 25 us, forever
  return true;
}
