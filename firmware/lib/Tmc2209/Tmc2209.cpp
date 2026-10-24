#include "Tmc2209.h"

// CRC8 of the UART datagrams (datasheet 4.2): polynomial x^8 + x^2 + x + 1, bytes LSB first.
uint8_t Tmc2209::crc8(const uint8_t *data, uint8_t len) {
  uint8_t crc = 0;
  for (uint8_t i = 0; i < len; i++) {
    uint8_t b = data[i];
    for (uint8_t j = 0; j < 8; j++) {
      if ((crc >> 7) ^ (b & 0x01)) crc = (crc << 1) ^ 0x07;
      else crc <<= 1;
      b >>= 1;
    }
  }
  return crc;
}

// Write datagram (8 bytes): sync 0x05, address, register | 0x80, 4 data bytes (MSB first), CRC.
void Tmc2209::writeReg(uint8_t reg, uint32_t value) {
  uint8_t d[8] = {0x05, addr_, (uint8_t)(reg | 0x80), (uint8_t)(value >> 24), (uint8_t)(value >> 16),
                  (uint8_t)(value >> 8), (uint8_t)value, 0};
  d[7] = crc8(d, 7);
  while (uart_.available()) uart_.read();
  uart_.write(d, 8);
  uart_.flush();                         // wait until sent
  uint32_t t = millis();                 // drop our own echo (8 bytes)
  uint8_t n = 0;
  while (n < 8 && millis() - t < 5) { if (uart_.available()) { uart_.read(); n++; } }
  delayMicroseconds(200);                // a few bit times before the next datagram
}

// Read request (4 bytes): sync, address, register, CRC. The driver answers with 8 bytes: sync, 0xFF (master
// address), register, 4 data bytes, CRC. With the shared wire we first get our own 4 request bytes back.
bool Tmc2209::readReg(uint8_t reg, uint32_t &value) {
  uint8_t q[4] = {0x05, addr_, reg, 0};
  q[3] = crc8(q, 3);
  while (uart_.available()) uart_.read();
  uart_.write(q, 4);
  uart_.flush();
  uint8_t b[16];
  uint8_t n = 0;
  uint32_t t = millis();
  while (n < 12 && millis() - t < 10) { if (uart_.available()) b[n++] = uart_.read(); }
  for (uint8_t i = 0; i + 8 <= n; i++) {                 // find the reply in what came back
    if (b[i] == 0x05 && b[i + 1] == 0xFF && b[i + 2] == reg && crc8(&b[i], 7) == b[i + 7]) {
      value = ((uint32_t)b[i + 3] << 24) | ((uint32_t)b[i + 4] << 16) | ((uint32_t)b[i + 5] << 8) | b[i + 6];
      return true;
    }
  }
  return false;
}

uint8_t Tmc2209::version() {
  uint32_t v;
  return readReg(IOIN, v) ? (uint8_t)(v >> 24) : 0;
}

// Motor current (datasheet 9): I_rms = (CS + 1) / 32 * Vfs / (Rsense + 0.02 ohm) / sqrt(2).
// Vfs = 0.325 V (vsense 0) or 0.180 V (vsense 1, finer for small currents). CS is 0..31.
void Tmc2209::setCurrent(uint16_t rmsMilliAmps) {
  mA_ = rmsMilliAmps;
  float i = rmsMilliAmps / 1000.0f;
  float cs = 32.0f * 1.41421f * i * (rSense_ + 0.02f) / 0.325f - 1.0f;
  vsense_ = false;
  if (cs < 16.0f) {                       // small current: use the finer range
    vsense_ = true;
    cs = 32.0f * 1.41421f * i * (rSense_ + 0.02f) / 0.180f - 1.0f;
  }
  int c = (int)(cs + 0.5f);
  if (c < 0) c = 0;
  if (c > 31) c = 31;
  writeChopconf();                        // vsense lives in CHOPCONF
  writeReg(IHOLD_IRUN, (8UL << 16) | ((uint32_t)c << 8) | (uint32_t)(c / 2));   // IHOLDDELAY 8, IRUN, IHOLD = half
}

// MRES: 0 = 256 microsteps, 1 = 128 ... 8 = full steps
uint8_t Tmc2209::mres(uint16_t microsteps) {
  uint8_t m = 0;
  for (uint16_t s = 256; s > microsteps && m < 8; s >>= 1) m++;
  return m;
}

void Tmc2209::setMicrosteps(uint16_t microsteps) {
  mres_ = mres(microsteps);
  writeChopconf();
}

void Tmc2209::enable(bool on) {
  on_ = on;
  writeChopconf();
}

// CHOPCONF (datasheet 5.5): TOFF 3 (0 = off), HSTRT 5, HEND 0, TBL 2 (24 clocks), vsense, MRES, interpolation on.
void Tmc2209::writeChopconf() {
  uint32_t v = 0x10000050UL | (on_ ? 3UL : 0UL) | (2UL << 15) | ((vsense_ ? 1UL : 0UL) << 17) | ((uint32_t)mres_ << 24);
  writeReg(CHOPCONF, v);
}

bool Tmc2209::readLoad(uint16_t &sg) {
  uint32_t v;
  if (!readReg(SG_RESULT, v)) return false;
  sg = v & 0x3FF;
  return true;
}

bool Tmc2209::begin(uint16_t rmsMilliAmps, uint16_t microsteps) {
  // GCONF: pdn_disable (UART on the PDN pin), mstep_reg_select (microsteps from MRES, MS pins = address),
  // multistep_filt; I_scale_analog 0 (current from the register, not the pot); en_spreadcycle 0 = StealthChop
  writeReg(GCONF, (1UL << 6) | (1UL << 7) | (1UL << 8));
  writeReg(TPOWERDOWN, 20);               // ~0.4 s standstill, then hold current
  writeReg(TCOOLTHRS, 0xFFFFF);           // StallGuard result valid at all speeds (load reading)
  mres_ = mres(microsteps);
  on_ = true;
  setCurrent(rmsMilliAmps);               // also writes CHOPCONF (TOFF, MRES, vsense)
  writeReg(GSTAT, 0x07);                  // clear reset / error flags
  return version() == 0x21;
}
