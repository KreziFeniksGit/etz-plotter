// SlewServo - hobby servo (MG996R lift) on an LEDC channel, 50 Hz, with a speed limit (no outside library).
// The servo itself has no feedback to us, so "done" is an estimate: the commanded pulse walks towards the
// target at slew us per second, and the move counts as finished when the pulse reaches it. The MG996R turns
// about 60 deg in 0.17-0.2 s (~3000+ us/s), so with a slower slew the real arm keeps up with the estimate.
// Before the first command no pulse is sent (servo limp, we do not know where it is); the first move is a jump,
// its "done" is estimated as a full-speed move from the middle (1500 us).
#pragma once
#include <Arduino.h>

class SlewServo {
public:
  bool begin(uint8_t pin);
  // new target in us (clamped to lo..hi); returns the value used
  uint16_t set(uint16_t us, uint16_t lo, uint16_t hi, uint16_t usPerSec);
  void off();                                   // no pulses: servo goes limp
  bool update();                                // call often; true once when a move has just finished
  uint16_t us() const { return on_ ? (uint16_t)lroundf(cur_) : 0; }   // present commanded pulse, 0 = off
  uint16_t target() const { return on_ ? tgt_ : 0; }
  bool moving() const { return on_ && busy_; }
private:
  void write(float us);
  uint8_t pin_ = 255;
  bool on_ = false, busy_ = false;
  float cur_ = 1500, rate_ = 1500;              // us, us per second
  uint16_t tgt_ = 1500;
  uint32_t last_ = 0, jumpEnd_ = 0;
};
