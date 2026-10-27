# PCB guide: common mistakes, good practice, and what our boards did (27 Oct 2026)

Research summary for home-made (toner transfer, single-sided) and fab boards, checked against our three split boards
(`pcb/review_2026-10-27.md`). Sources at the end.

## 1. Trace angles (what Egor noticed)
Measured on our boards (all corners where two tracks meet):
| | drivers | power | controller |
|---|---|---|---|
| 90 deg corners | 22 | 11 | 53 |
| 135 deg (45 deg bends) | 12 | 4 | 4 |
| odd angles (99, 101, 113, 119, 146 ...) | 1 | 8 | 3 |
| **acute (< 90 deg) = acid traps** | **0** | **0** | **0** |

- **Acute angles are the real defect**: a narrow wedge between two tracks holds etchant and over-etches (or, on toner,
  the toner bridges and the gap does not etch). We have none.
- **90 deg corners are not an electrical problem** at our speeds (the "90 deg radiates" rule matters only at GHz). The rule
  started as a cosmetic / acid-trap heuristic. Still, 45 deg bends are the clean convention: shorter, no sharp outer
  corner that can lift or over-etch, easier to read.
- **The odd angles** come from our hand-routing script: from the last bend it drew a straight line to a pad that was off
  the 45 deg grid. Works, but looks messy and wastes space. Rule for next time: route only at 0 / 45 / 90 deg, and put a
  short 45 deg "jog" before a pad instead of a free diagonal.

## 2. Mistakes that kill boards (ranked)
1. **Wrong footprint / pinout** (library part does not match the real part; SOT-23 and TO-252 transistors have several
   pin orders). Check every footprint against the datasheet, print the copper 1:1 and lay the real parts on the paper.
2. **Reversed polarity on connectors** - our drivers XT30 (VDRIVE on the "-" contact) is exactly this. Use keyed
   connectors with one fixed convention, label + and - in copper (home boards have no silkscreen).
3. **No power switch / no fuse** - see section 4.
4. **Traces too thin for the current** - size power traces with IPC-2221 (KiCad calculator). Ours: 1.2-2.0 mm power,
   1.0 mm motor coils, 0.6 mm signals: fine.
5. **Mirrored print** - for toner transfer the copper layer prints so it reads correctly on the copper side; a mirrored
   board puts every IC pin on the wrong side. Check with a 1:1 paper print and a real part.
6. **Missing / far decoupling** - small ceramic next to each IC supply pin (within ~5 mm), bulk electrolytic where the
   high current enters (motor drivers: right at VM). The TMC2209 modules carry their own ceramics; our 100 uF per driver
   is next to each module - good.
7. **Broken ground** - one solid ground pour, no islands, no signal tracks cutting it into pieces. Ours: one GND island
   per board (checked).
8. **Strapping / boot pins** loaded by circuits (ESP32-S3: GPIO0, 3, 45, 46) - the board will not boot. Ours avoid them.
9. **Inputs floating** - pull-ups / pull-downs on every input that can be left open (our MOSFET gate has 100 k).

## 3. Home toner transfer: design rules that work
- Traces >= 0.4-0.5 mm (we used 0.6), clearance >= 0.4 mm; pour-to-track gap 0.4-0.5 mm.
- Pads big: 2 mm+ round for through-hole, wide SMD hand-solder pads (pads < ~1.5 mm lift when soldering).
- Thermal relief spokes on pour pads (we used 0 deg spokes) - otherwise the pour sinks the iron's heat.
- Print a **test coupon first** (widths 0.3-1.0 mm, clearances, horizontal and vertical lines): printers reproduce X and
  Y line widths differently.
- No text in copper smaller than ~2 mm; copper text must be mirrored the same way as the copper.
- Fill large empty areas with ground: less copper to etch away = faster, more even etching.
- Laser printer, glossy paper, clean (scrubbed) copper; tin the board after etching (stops oxidation, adds copper).
- Tin / add solder over high-current tracks.
- Holes: drill pads with a 0.8-1.0 mm bit; leave a copper ring >= 0.5 mm around each hole.

## 4. Why there is no switch on our boards (and why it matters)
The stop button is the rules' "cut all drive power": it switches VDRIVE (steppers, servo regulator) and the magnet 5 V.
**The logic 5 V regulator (Mini560 #1) is on the battery directly, before the stop button** (wiring.md: "not switched by
the stop"), so the ESP32 can still talk to the laptop with the stop pressed. Consequence: **as long as the battery is
plugged in, the ESP32 + regulator draw ~40-80 mA from it, all the time**. A 2200 mAh pack is empty in ~1-2 days.
This is the most likely reason the battery now reads 11.8 V.
Fix without a new board: **unplug the battery after every session**, or put a switch in the battery lead (an XT30 inline
switch / a 5 A rocker), and use the firmware battery check (warn below 14.8 V, stop below 14.0 V).
On a v2 board: a main switch (or a latching soft-power circuit) before both regulators.

## 5. Measuring everything with the ESP32 ("voltage on everything")
What the ESP32 can read today, with no hardware change:
| Value | How | In the firmware |
|---|---|---|
| battery voltage | VBAT_SENSE divider -> GPIO2 (ADC) | yes (`vbat` in json, self-test) |
| drive power on / off | STOP_SENSE -> GPIO42 (digital only: GPIO42 has no ADC) | yes (`drive`) |
| per driver: answers, temperature thresholds 120/143/150/157 C, pre-warning, overheat, short to GND, open coil, actual current scale, load (StallGuard) | TMC2209 UART registers | yes |
| per driver: PWM_SCALE (how hard the driver works to push the current = rough supply / motor heat indicator) | PWMCONF / PWM_SCALE register | can be added |
| ESP32 chip temperature, RAM, loop rate, reset reason | built in | yes |
| motor temperature | estimate (heat model) | yes |

What needs a little hardware (no new PCB):
| Value | Best option | Notes |
|---|---|---|
| **battery current + voltage + power + used mAh** | **INA226 module** (I2C, 36 V, 16-bit) with its shunt in the battery lead, on the SDA/SCL bus (GPIO40/39, 4.7 k pull-ups already on the controller board) | the single most useful sensor: shows motor load, stalls, magnet on, real consumption, battery left. INA219 is only 26 V (too close to 16.8 V + spikes). Check the shunt value printed on the module (often R100 or R010). ~2 USD |
| 5 V logic rail, 5 V servo rail | a 10 k / 10 k divider soldered by wire to a free ADC pin: GPIO4 (ADC1, free on the controller), or GPIO13 / 14 (ADC2: usable because Wi-Fi is never started) | or a second INA226 (another I2C address) on the servo rail: also gives the servo current |
| 3.3 V rail | a divider to a free ADC pin | low value: if 3.3 V fails, the ESP32 stops anyway |
| magnet current | INA226 on the magnet lead, or read it from the battery current step when the magnet switches | confirms "magnet really on" |

Risks / blind spots: the ESP32-S3 ADC is non-linear near 0 V and above ~3.1 V (keep dividers in 0.2-2.8 V);
`analogReadMilliVolts` uses the factory calibration, accuracy ~2-3 %. Cheap INA226 clones vary: check the shunt
value and compare against a multimeter once.

## Sources
- Altium, "Slaying the PCB 90 deg right-angle bend dragon": https://resources.altium.com/p/slaying-900-right-angle-bend-dragon
- Cadence, "The challenges of right angle PCB traces": https://resources.pcb.cadence.com/blog/2022-the-challenges-of-right-angle-pcb-traces
- NextPCB, "Acid traps": https://www.nextpcb.com/blog/acid-traps
- EEVblog forum, "Acid traps": https://www.eevblog.com/forum/eda/acid-traps-310805/msg3983057
- DigiKey forum, "Common PCB design mistakes beginners make": https://forum.digikey.com/t/common-pcb-design-mistakes-beginners-make-and-how-to-avoid-them/70102
- JLCPCB, "5 common PCB design mistakes": https://jlcpcb.com/blog/common-pcb-design-mistakes
- UIUC ECE 445 PCB checklist: https://courses.grainger.illinois.edu/ece445/lab/PCB%20Checklist%20FA25.pdf
- KiCad forum, "Trace widths for toner transfer etching": https://forum.kicad.info/t/trace-widths-for-toner-transfer-etching/11364
- SparkFun community, "Etching PCB - minimum feature size": https://community.sparkfun.com/t/etching-pcb-minimum-feature-size/15085
- TI, "Motor driver layout best practices": https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/38/Motor-Driver-Layout-Best-Practices.pdf
- esp32.co.uk, INA226 with ESP32: https://esp32.co.uk/ina226-esp32-esphome-dc-voltage-current-power-energy/
- universal-solder, "INA219, INA226 and INA3221 explained": https://www.universal-solder.ca/sensors-current/
