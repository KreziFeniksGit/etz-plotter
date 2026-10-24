// StepGen - our own step pulse generator with trapezoid acceleration (no outside library).
// One hardware timer interrupt runs at TICK_HZ and serves every axis. Each tick an axis:
//   - ends the step pulse it started on the tick before (pulse = 1 tick = 25 us, the TMC2209 needs 0.1 us),
//   - speeds up or slows down by the acceleration (decides from "steps still to go" vs "steps needed to stop"),
//   - adds its speed to a 32-bit phase counter and makes a step when the counter overflows.
// Only integer maths in the interrupt (the ESP32 FPU must not be used there). Because the steps come from the
// timer, nothing in loop() (UART reads of the drivers, printing) can disturb the motion.
#pragma once
#include <Arduino.h>

class StepAxis {
public:
  static constexpr uint32_t TICK_HZ = 40000;           // interrupt rate
  static constexpr uint32_t MAX_SPEED = TICK_HZ * 2 / 5;  // 16000 steps/s: at least 2.5 ticks between steps

  StepAxis(uint8_t stepPin, uint8_t dirPin) : stepPin_(stepPin), dirPin_(dirPin) {}

  void setMaxSpeed(uint32_t stepsPerSec);              // steps/s
  void setAccel(uint32_t stepsPerSec2);                // steps/s^2
  void moveTo(int32_t target);                         // absolute target, steps
  void move(int32_t steps) { moveTo(target_ + steps); }  // relative to the present target
  void stop();                                         // slow down to a stop (target = where it can stop)
  void halt();                                         // stop at once, no deceleration
  void setPosition(int32_t pos);                       // call the present position "pos" (only when standing)
  void setInvert(bool inv);                            // reverse the DIR pin (only when standing)
  bool inverted() const { return inv_; }

  int32_t position() const { return pos_; }
  int32_t target() const { return target_; }
  bool running() const { return moving_ || target_ != pos_; }
  uint32_t speed() const;                              // present speed, steps/s

  // start the timer for these axes (call once in setup)
  static bool begin(StepAxis **axes, uint8_t count);

private:
  void tick();
  void setDirPin();
  static void isr();

  uint8_t stepPin_, dirPin_;
  uint32_t stepMask_ = 0, dirMask_ = 0;
  bool highBank_ = false;                              // pin >= 32: second GPIO register bank
  volatile int32_t pos_ = 0, target_ = 0;
  volatile uint32_t vel_ = 0;                          // speed in steps/tick * 2^32
  volatile uint32_t vmax_ = 0, dvel_ = 1;              // max speed, speed change per tick (same units)
  volatile uint32_t phase_ = 0, stopSteps_ = 0;
  volatile bool fwd_ = true, inv_ = false, pulse_ = false, moving_ = false;
  volatile uint8_t dirWait_ = 0;

  static StepAxis *axes_[4];
  static uint8_t count_;
};
