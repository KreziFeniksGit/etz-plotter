// Tmc2209 - our own driver for the TMC2209 over its single-wire UART (no outside library).
// Datasheet: TMC2209 rev 1.09, sections 4 (UART), 5 (registers). All three drivers share one wire; each answers to
// its own address (MS1 / MS2 pins: X 0, Y 2, wrist 3). The ESP32 TX goes through 1 k onto the wire, RX sits on it
// directly, so every byte we send also comes back to us (echo) and is skipped when reading.
#pragma once
#include <Arduino.h>

class Tmc2209 {
public:
  // registers used (datasheet section 5)
  enum : uint8_t { GCONF = 0x00, GSTAT = 0x01, IFCNT = 0x02, IOIN = 0x06, IHOLD_IRUN = 0x10, TPOWERDOWN = 0x11,
                   TCOOLTHRS = 0x14, SGTHRS = 0x40, SG_RESULT = 0x41, CHOPCONF = 0x6C, DRV_STATUS = 0x6F, PWMCONF = 0x70 };

  Tmc2209(HardwareSerial &uart, uint8_t address, float rSense = 0.11f) : uart_(uart), addr_(address), rSense_(rSense) {}

  // Configure for STEP/DIR use: current from the register, microsteps from the register, StealthChop, driver on.
  // Returns true if the driver answered (version 0x21).
  bool begin(uint16_t rmsMilliAmps, uint16_t microsteps);

  bool readReg(uint8_t reg, uint32_t &value);   // false = no / bad answer
  void writeReg(uint8_t reg, uint32_t value);

  uint8_t version();                             // 0x21 for a TMC2209, 0 = no answer
  void setCurrent(uint16_t rmsMilliAmps);        // RMS motor current while moving
  void setHoldPercent(uint8_t pct);              // current while standing, % of the moving current (default 50)
  uint8_t holdPercent() const { return holdPct_; }
  uint16_t current() const { return mA_; }
  void setMicrosteps(uint16_t microsteps);       // 1, 2, 4 ... 256
  void enable(bool on);                          // on = chopper running; off = motor free (TOFF = 0)
  bool enabled() const { return on_; }

  // DRV_STATUS bits: 0 otpw, 1 ot, 2 s2ga, 3 s2gb, 6 ola, 7 olb, 8 t120, 9 t143, 10 t150, 11 t157, 16..20 cs_actual, 31 stst
  bool readStatus(uint32_t &drvStatus) { return readReg(DRV_STATUS, drvStatus); }
  bool readLoad(uint16_t &sg);                   // StallGuard result 0..510: lower = more load

  // what came back on the wire for the last read (our 4 echo bytes, then the 8-byte reply): for checks
  const uint8_t *lastRx() const { return rx_; }
  uint8_t lastRxLen() const { return rxLen_; }

private:
  static uint8_t crc8(const uint8_t *data, uint8_t len);
  static uint8_t mres(uint16_t microsteps);
  void writeChopconf();
  void writeIhold();
  HardwareSerial &uart_;
  uint8_t addr_;
  float rSense_;
  uint16_t mA_ = 0;
  uint8_t cs_ = 0, holdPct_ = 50;
  uint8_t mres_ = 4;          // 16 microsteps
  bool vsense_ = false;
  bool on_ = true;
  uint8_t rx_[16] = {0}, rxLen_ = 0;
};
