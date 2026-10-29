// Magnet - electromagnet through a low-side MOSFET, PWM on an LEDC channel at 20 kHz (no outside library).
// "Peak and hold": full power for kickMs to pull the checker in across the air gap, then holdPct to keep it
// (with the checker touching, much less current holds it, and the coil stays cooler). An on-time guard switches
// it off after maxS seconds. With one low-side MOSFET the current can only be switched off, never reversed, so
// there is no reverse "release" pulse: the SS34 across the coil makes the field decay in a few ms.
#pragma once
#include <Arduino.h>

class Magnet {
public:
  bool begin(uint8_t pin);
  void on(uint16_t kickMs, uint8_t holdPct, uint16_t maxS);
  void off();
  bool update();                     // call often; true once when the on-time guard has switched it off
  bool isOn() const { return on_; }
  uint8_t pct() const { return on_ ? pct_ : 0; }   // present duty %
private:
  void duty(uint8_t pct);
  uint8_t pin_ = 255, pct_ = 0, hold_ = 40;
  bool on_ = false, kick_ = false;
  uint32_t t0_ = 0, kickMs_ = 150, maxMs_ = 30000;
};
