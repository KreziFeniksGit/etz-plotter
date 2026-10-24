// Guard - protection for the motors (no outside library, plain maths).
//
// HeatModel: the motor has no temperature sensor, so its temperature is estimated from the current.
//   A stepper heats like a first-order system: steady rise = (rated rise) * (I / I_rated)^2, reached with the
//   thermal time constant tau. Rated rise ~80 K at rated current is the usual NEMA17 figure (VERIFY per motor);
//   tau ~10-15 min for a NEMA17 (VERIFY). Coil resistance cancels out, so only I_rated and tau are needed.
//
// CrashDetector: the TMC2209 reports the motor load (StallGuard, SG_RESULT 0..510, lower = harder to turn).
//   While moving at a steady speed the value is learnt (running average); a sudden drop to pct% of it, or to 0,
//   means the axis hit something (or the motor is about to slip): stop.
#pragma once
#include <Arduino.h>

class HeatModel {
public:
  float ratedRise = 80.0f;       // K at rated current (typical NEMA17 datasheet value, VERIFY)
  void setup(uint16_t ratedMilliAmps, uint16_t tauSeconds) { ratedmA_ = ratedMilliAmps; tau_ = tauSeconds; }
  void update(float milliAmps, float dtSeconds) {     // call every ~100 ms with the present coil current
    float r = milliAmps / ratedmA_;
    float steady = ratedRise * r * r;
    rise_ += (steady - rise_) * dtSeconds / tau_;
  }
  float temp(float ambient) const { return ambient + rise_; }
  uint16_t ratedmA() const { return ratedmA_; }
  uint16_t tau() const { return tau_; }
private:
  uint16_t ratedmA_ = 1000, tau_ = 600;
  float rise_ = 0;
};

class CrashDetector {
public:
  uint8_t pct = 30;              // trip when the load reading falls below pct % of the learnt value; 0 = off
  uint32_t minSpeed = 800;       // steps/s: below this StallGuard is not reliable, so it is not used
  void startMove() { n_ = 0; low_ = 0; }
  // one load sample while moving; returns true = crash
  bool sample(uint16_t sg, uint32_t speed) {
    if (!pct || speed < minSpeed) return false;
    if (n_ >= LEARN && (sg == 0 || sg * 100UL < (uint32_t)avg_ * pct)) {
      if (++low_ >= 2) return true;               // two low readings in a row: not noise
      return false;
    }
    low_ = 0;
    avg_ = n_ ? (avg_ * 7 + sg) / 8 : sg;          // running average of the normal load
    if (n_ < 255) n_++;
    minSeen = n_ == 1 ? sg : min(minSeen, sg);
    return false;
  }
  uint16_t average() const { return avg_; }
  uint16_t minSeen = 0;          // lowest normal reading in this move (for auto-tune)
private:
  static constexpr uint8_t LEARN = 6;
  uint16_t avg_ = 0;
  uint8_t n_ = 0, low_ = 0;
};
