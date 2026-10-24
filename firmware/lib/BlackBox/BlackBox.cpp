#include "BlackBox.h"
#include <stdarg.h>
#include "esp_attr.h"

namespace BlackBox {

static constexpr uint32_t MAGIC = 0xB1ACB0C5;
RTC_NOINIT_ATTR static Log rtcLog;          // RTC memory: not cleared by a crash / watchdog / software restart

void begin() {
  if (rtcLog.magic != MAGIC || rtcLog.head >= ENTRIES || rtcLog.count > ENTRIES) {   // power-on: memory is random
    memset(&rtcLog, 0, sizeof rtcLog);
    rtcLog.magic = MAGIC;
  }
  rtcLog.boots++;
}

void add(const char *fmt, ...) {
  Entry &e = rtcLog.e[rtcLog.head];
  e.ms = millis();
  e.boot = (uint16_t)rtcLog.boots;
  va_list ap;
  va_start(ap, fmt); vsnprintf(e.text, TEXT, fmt, ap); va_end(ap);
  rtcLog.head = (rtcLog.head + 1) % ENTRIES;
  if (rtcLog.count < ENTRIES) rtcLog.count++;
}

void clear() {
  uint32_t b = rtcLog.boots;
  memset(&rtcLog, 0, sizeof rtcLog);
  rtcLog.magic = MAGIC; rtcLog.boots = b;
}

void print(Stream &out, const Log *log) {
  const Log &l = log ? *log : rtcLog;
  uint16_t start = (l.head + ENTRIES - l.count) % ENTRIES;
  for (uint16_t i = 0; i < l.count; i++) {
    const Entry &e = l.e[(start + i) % ENTRIES];
    char t[TEXT + 1];
    memcpy(t, e.text, TEXT); t[TEXT] = 0;
    out.printf("  boot %u  %7lu.%03lu s  %s\r\n", e.boot, (unsigned long)(e.ms / 1000), (unsigned long)(e.ms % 1000), t);
  }
  if (!l.count) out.print("  (empty)\r\n");
}

const Log &live() { return rtcLog; }
uint32_t boots() { return rtcLog.boots; }

}
