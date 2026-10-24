// BlackBox - the last events (commands, errors, temperatures ...) in a ring buffer that survives a crash or
// watchdog restart (RTC memory that the restart does not clear; a power-off does clear it). After a crash the
// firmware copies it to flash (Settings "crashlog"), so it can be read even after the battery was unplugged.
#pragma once
#include <Arduino.h>

namespace BlackBox {
  constexpr uint8_t ENTRIES = 64, TEXT = 42;
  struct Entry { uint32_t ms; uint16_t boot; char text[TEXT]; };
  struct Log { uint32_t magic; uint32_t boots; uint16_t head, count; Entry e[ENTRIES]; };

  void begin();                                   // once in setup: keeps the old entries, counts the boot
  void add(const char *fmt, ...);                 // one line (printf style, cut at 41 characters)
  void clear();
  void print(Stream &out, const Log *log = nullptr);   // oldest first; nullptr = the live log
  const Log &live();
  uint32_t boots();
}
