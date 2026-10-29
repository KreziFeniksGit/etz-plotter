// MoveQueue - a list of command lines run one after another (no outside library, fixed memory: 128 x 48 bytes).
// The laptop sends a whole pick-and-place sequence ("q ..."), then "qrun"; the firmware starts the next line
// only when the previous motion / servo move / wait has finished, so the timing does not depend on the USB link.
#pragma once
#include <Arduino.h>

class MoveQueue {
public:
  static constexpr uint16_t CAP = 128;
  static constexpr uint8_t LEN = 48;              // longest line kept (e.g. "linemm 143.00 336.00" is 20)
  bool push(const char *line) {
    if (n_ >= CAP || strlen(line) >= LEN) return false;
    strlcpy(buf_[(head_ + n_) % CAP], line, LEN);
    n_++;
    return true;
  }
  bool pop(char *out) {                           // out: LEN bytes
    if (!n_) return false;
    strlcpy(out, buf_[head_], LEN);
    head_ = (head_ + 1) % CAP; n_--;
    return true;
  }
  void clear() { n_ = 0; head_ = 0; }
  uint16_t size() const { return n_; }
private:
  char buf_[CAP][LEN];
  uint16_t head_ = 0, n_ = 0;
};
