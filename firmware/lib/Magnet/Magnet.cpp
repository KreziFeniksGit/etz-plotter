#include "Magnet.h"

static constexpr uint32_t FREQ = 20000, BITS = 10;          // 20 kHz: above hearing; 1024 steps

bool Magnet::begin(uint8_t pin) {
  pin_ = pin;
  bool ok = ledcAttach(pin, FREQ, BITS);
  duty(0);
  return ok;
}

void Magnet::duty(uint8_t pct) {
  pct_ = pct;
  if (pin_ != 255) ledcWrite(pin_, pct >= 100 ? (1 << BITS) : (uint32_t)pct * ((1 << BITS) - 1) / 100);
}

void Magnet::on(uint16_t kickMs, uint8_t holdPct, uint16_t maxS) {
  hold_ = min<uint8_t>(holdPct, 100);
  kickMs_ = kickMs;
  maxMs_ = (uint32_t)maxS * 1000UL;
  t0_ = millis();
  on_ = true; kick_ = kickMs > 0;
  duty(kick_ ? 100 : hold_);
}

void Magnet::off() {
  on_ = kick_ = false;
  duty(0);
}

bool Magnet::update() {
  if (!on_) return false;
  uint32_t t = millis() - t0_;
  if (kick_ && t >= kickMs_) { kick_ = false; duty(hold_); }
  if (maxMs_ && t >= maxMs_) { off(); return true; }
  return false;
}
