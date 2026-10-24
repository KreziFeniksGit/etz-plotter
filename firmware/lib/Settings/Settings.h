// Settings - keep blocks of bytes in the ESP32 flash (NVS), so they survive power-off (no outside library:
// the ESP-IDF nvs_* calls that come with the chip). Each block has a short name (max 15 characters), e.g. the
// settings profiles "boot", "fast", "careful", or the black box copied after a crash.
#pragma once
#include <Arduino.h>

namespace Settings {
  bool begin();                                              // once in setup
  bool save(const char *name, const void *data, size_t len);
  bool load(const char *name, void *data, size_t len);       // false if missing or a different size
  bool remove(const char *name);
  // call fn(name) for every block kept
  void list(void (*fn)(const char *name));
}
