// Console - our own line editor and command splitter for the serial port (no outside library).
// For a person in a terminal: echo, Backspace, arrow keys ignored, "> " prompt.
// For a program: echo off (no prompt, no echo), one command per line, replies "ok ..." / "err ...".
#pragma once
#include <Arduino.h>

class Console {
public:
  static constexpr uint8_t MAX_LINE = 80, MAX_ARGS = 4;

  explicit Console(Stream &io) : io_(io) {}

  // Read what has arrived (never waits). True when a whole line is ready: then words()/arg*() describe it.
  bool poll();
  void prompt() { if (echo_) io_.print("> "); }
  void setEcho(bool on) { echo_ = on; }
  bool echo() const { return echo_; }

  // the line just read, split at spaces and lowercased
  uint8_t words() const { return n_; }
  const char *word(uint8_t i) const { return i < n_ ? w_[i] : ""; }
  bool is(uint8_t i, const char *s) const { return strcmp(word(i), s) == 0; }
  long argInt(uint8_t i) const { return strtol(word(i), nullptr, 10); }
  float argFloat(uint8_t i) const { return strtof(word(i), nullptr); }

  void reply(const char *fmt, ...);      // printf-style line ending in \r\n

private:
  void split();
  Stream &io_;
  bool echo_ = true;
  char line_[MAX_LINE + 1];
  uint8_t len_ = 0, n_ = 0, esc_ = 0;
  char *w_[MAX_ARGS];
};
