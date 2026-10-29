#include "Console.h"
#include <stdarg.h>

bool Console::poll() {
  while (io_.available()) {
    char c = io_.read();
    if (esc_) {                           // arrow keys etc. send ESC [ x: skip the two bytes after ESC
      if (esc_ == 1 && c != '[') esc_ = 0;
      else { esc_ = esc_ == 1 ? 2 : 0; continue; }
    }
    if (c == 0x1b) { esc_ = 1; continue; }
    if (c == '\r' || c == '\n') {
      if (c == '\n' && !len_) continue;   // the \n after a \r
      if (echo_) io_.print("\r\n");
      if (!len_) { prompt(); continue; }
      line_[len_] = 0;
      len_ = 0;
      load(line_);
      if (n_) return true;
      prompt();
    } else if (c == '\b' || c == 0x7f) {  // Backspace / Delete
      if (len_) { len_--; if (echo_) io_.print("\b \b"); }
    } else if (isprint((unsigned char)c) && len_ < MAX_LINE) {
      line_[len_++] = tolower((unsigned char)c);
      if (echo_) io_.write(c);
    }
  }
  return false;
}

void Console::load(const char *line) {
  strlcpy(cmd_, line, sizeof cmd_);
  strlcpy(words_, line, sizeof words_);
  split();
}

void Console::split() {
  n_ = 0;
  char *p = words_;
  while (*p && n_ < MAX_ARGS) {
    while (*p == ' ') *p++ = 0;
    if (!*p) break;
    w_[n_++] = p;
    while (*p && *p != ' ') p++;
  }
}

void Console::reply(const char *fmt, ...) {
  char b[160];
  va_list ap;
  va_start(ap, fmt); vsnprintf(b, sizeof b, fmt, ap); va_end(ap);
  io_.print(b); io_.print("\r\n");
}
