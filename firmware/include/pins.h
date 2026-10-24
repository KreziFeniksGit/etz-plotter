// ESP32-S3 pin map of the split controller board (wiring.md section 2, pcb/split_boards.md)
#pragma once

// TMC2209 single-wire UART bus (all three drivers): RX direct, TX through R8 1k onto the same wire
constexpr int PIN_TMC_RX = 5;
constexpr int PIN_TMC_TX = 6;

// STEP / DIR. Egor's cables cross X and wrist (controller J1 -> driver J3, J3 -> J1; 25 Oct), so the
// X driver gets the controller's J3 pins (18 / 8) and the wrist driver gets J1 (7 / 15). Swapped here, not in the cables.
constexpr int PIN_X_STEP = 18, PIN_X_DIR = 8;
constexpr int PIN_Y_STEP = 16, PIN_Y_DIR = 17;
constexpr int PIN_W_STEP = 7,  PIN_W_DIR = 15;     // W = wrist (NEMA17 pancake)

// Driver EN pins are tied to GND on the controller board: drivers are always enabled.
// They are switched off over UART (TOFF = 0); the stop button cuts their power (VM).

// Other pins (not used by this bench test yet)
constexpr int PIN_MAG_IO = 1, PIN_VBAT_SENSE = 2, PIN_STOP_SENSE = 42, PIN_SERVO = 41;
constexpr int PIN_SDA = 40, PIN_SCL = 39;
constexpr int PIN_X_HOME = 38, PIN_Y_HOME = 48, PIN_START = 47, PIN_LED_RED = 21;   // 38 / 48: inputs only
constexpr int PIN_A_IO = 9, PIN_B_IO = 10, PIN_U1_TX = 11, PIN_U1_RX = 12;
