#include "SlewServo.h"

static constexpr uint32_t FREQ = 50, BITS = 14;           // 20 ms period, 16384 counts = 1.22 us per count
static constexpr float PERIOD_US = 1000000.0f / FREQ;

bool SlewServo::begin(uint8_t pin) {
  pin_ = pin;
  bool ok = ledcAttach(pin, FREQ, BITS);
  ledcWrite(pin, 0);                                     // no pulse until the first command
  return ok;
}

void SlewServo::write(float us) {
  ledcWrite(pin_, (uint32_t)lroundf(us * ((1 << BITS) - 1) / PERIOD_US));
}

uint16_t SlewServo::set(uint16_t us, uint16_t lo, uint16_t hi, uint16_t usPerSec) {
  us = constrain(us, lo, hi);
  rate_ = max<uint16_t>(usPerSec, 1);
  tgt_ = us;
  last_ = millis();
  if (!on_) {                                            // first move: unknown start, jump
    on_ = true; cur_ = us;
    jumpEnd_ = last_ + (uint32_t)(fabsf(us - 1500.0f) * 1000.0f / 3000.0f) + 200;   // ~3000 us/s + settle
  } else jumpEnd_ = 0;
  busy_ = true;
  write(cur_);
  return us;
}

void SlewServo::off() {
  on_ = busy_ = false;
  if (pin_ != 255) ledcWrite(pin_, 0);
}

bool SlewServo::update() {
  if (!on_ || !busy_) return false;
  uint32_t now = millis();
  if (jumpEnd_) {
    if ((int32_t)(now - jumpEnd_) < 0) return false;
    jumpEnd_ = 0; busy_ = false;
    return true;
  }
  float step = rate_ * (now - last_) / 1000.0f;
  if (step < 1.0f) return false;                         // less than 1 us: wait (keeps the pulse steady)
  last_ = now;
  float d = tgt_ - cur_;
  if (fabsf(d) <= step) cur_ = tgt_;
  else cur_ += d > 0 ? step : -step;
  write(cur_);
  if (cur_ == tgt_) { busy_ = false; return true; }
  return false;
}
