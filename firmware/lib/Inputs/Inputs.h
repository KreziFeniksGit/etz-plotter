// Inputs - small helpers for buttons and slow analog readings (no outside library).
#pragma once
#include <Arduino.h>

// a button / switch that must stay at a new level for ms before it counts (contact bounce)
class Debounce {
public:
  Debounce(uint16_t ms = 30) : ms_(ms) {}
  // raw level now; true when the stable level has just changed (read it with level())
  bool update(bool raw) {
    uint32_t now = millis();
    if (raw != raw_) { raw_ = raw; t_ = now; return false; }
    if (raw_ != stable_ && now - t_ >= ms_) { stable_ = raw_; return true; }
    return false;
  }
  void reset(bool level) { raw_ = stable_ = level; t_ = millis(); }
  bool level() const { return stable_; }
private:
  uint16_t ms_;
  bool raw_ = true, stable_ = true;   // pull-up inputs: idle HIGH
  uint32_t t_ = 0;
};

// exponential moving average: each new reading moves the value 1/n of the way (n = 8 -> about the last 8 readings)
class Ema {
public:
  explicit Ema(float n) : k_(1.0f / n) {}
  float add(float v) { val_ = first_ ? v : val_ + (v - val_) * k_; first_ = false; return val_; }
  void reset() { first_ = true; val_ = 0; }
  float value() const { return val_; }
private:
  float k_, val_ = 0;
  bool first_ = true;
};
