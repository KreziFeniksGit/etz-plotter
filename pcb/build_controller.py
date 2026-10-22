"""
CONTROLLER BOARD (split board 3 of 3): ESP32-S3-DevKitC-1 + small parts, hand-routed, single-sided (bottom copper),
toner transfer -> pcb/controller/controller.kicad_pcb.  3 wire links (insulated wire on the component side).
ESP32 pins are chosen so every connector's lines reach the ESP32 in the same order (no crossings). Pin map (GPIO):
  left row : 4 not used, 5 TMC_UART (RX), 6 TMC_TX (through R8 1k onto the same wire), 7 X_STEP, 15 X_DIR, 16 Y_STEP,
             17 Y_DIR, 18 W_STEP, 8 W_DIR, 9 A_IO (ADC), 10 B_IO, 11 U1_TX (connector C), 12 U1_RX, 13/14 not used
  right row: 1 MAG_IO, 2 VBAT_SENSE (ADC), 42 STOP_SENSE, 41 SERVO_IO, 40 SDA, 39 SCL, 38 X_HOME, 48 Y_HOME,
             47 START, 21 LEDR_IO   (38 / 48: one of them is the board's RGB LED data pin - used as inputs only: harmless)
Driver EN pins are tied to GND here (drivers always enabled; the firmware turns them off over UART, the stop button cuts
their power). TOF XSHUT is tied to 3V3 (sensor always on).
Connectors (all <= 6 pins, straight 1:1 cables):
  J1/J2/J3 drivers X/Y/W (to the driver board J1/J2/J3): 1 GND, 2 EN(=GND), 3 UART, 4 STEP, 5 DIR, 6 3V3
  J4 power board (to its J5): 1 MAG_IO, 2 GND, 3 +5V, 4 VBAT_SENSE, 5 STOP_SENSE, 6 SERVO_IO
  J5 panel A/B/C: 1 A_SIG, 2 B_SIG, 3 C_TX, 4 C_RX, 5 C_V (5 V via 0.5 A PTC), 6 GND
  J6 TOF400C: 1 3V3, 2 GND, 3 SDA, 4 SCL, 5 XSHUT(=3V3)    J7 X home, J8 Y home, J9 start: 1 signal, 2 GND
  J10 red LED: 1 LEDR_A, 2 GND
Run: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" pcb\\build_controller.py
"""
import os, sys
FLAGS = sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handroute as H

OUT_DIR = os.path.join(H.HERE, 'controller')
OUT = os.path.join(OUT_DIR, 'controller.kicad_pcb')
W, HGT = 118.0, 115.0
EL, ER, EY = 48.0, 48.0 + 22.86, 18.0      # ESP32 left / right pin rows x, pin 1 y (row spacing VERIFY: 22.86)
CX = 15.0                                   # left connector column
RX_ = 108.0                                 # right connector column
SIG, R5W = 0.6, 1.2
TOP3V3 = 12.0                               # 3V3 runs along the top edge
P5V_X, P5V_Y = 114.0, 104.0                 # +5V runs down the right edge and along the bottom
LJ = [('Y_STEP', 19.5), ('Y_DIR', 21.1), ('W_STEP', 22.7), ('W_DIR', 24.3),
      ('A', 25.9), ('B', 27.5), ('CTX', 29.1), ('CRX', 30.7)]          # x lanes, left side
X33, LNK = 5.5, 9.0                         # 3V3 and UART wire-link pad columns, left edge
DRV_Y = (21.0, 40.0, 59.0)                  # driver plugs, pin 1 y
LANE = dict(LJ)

def esp(n, right=False):
    return ((ER if right else EL), EY + (n - 1) * 2.54)

def place(b):
    left = {4: None, 5: 'TMC_UART', 6: 'TMC_TX', 7: 'X_STEP', 8: 'X_DIR', 9: 'Y_STEP', 10: 'Y_DIR', 11: 'W_STEP',
            12: 'W_DIR', 15: 'A_IO', 16: 'B_IO', 17: 'U1_TX', 18: 'U1_RX', 1: '3V3', 2: '3V3', 21: '5V_ESP', 22: 'GND'}
    right = {1: 'GND', 4: 'MAG_IO', 5: 'VBAT_SENSE', 6: 'STOP_SENSE', 7: 'SERVO_IO', 8: 'SDA', 9: 'SCL', 10: 'X_HOME',
             16: 'Y_HOME', 17: 'START', 18: 'LEDR_IO', 21: 'GND', 22: 'GND'}
    b.part('U1A', 'sock22', 'ESP32-S3 left (J1)', EL, EY, 0, {k: v for k, v in left.items() if v})
    b.part('U1B', 'sock22', 'ESP32-S3 right (J3)', ER, EY, 0, right)
    for k, (ax, y0) in enumerate(zip('XYW', DRV_Y)):
        b.part('J%d' % (k + 1), 'xh6', '%s driver' % ax, CX, y0, 270,
               {1: 'GND', 2: 'GND', 3: 'TMC_UART', 4: ax + '_STEP', 5: ax + '_DIR', 6: '3V3'})
    b.part('J5', 'xh6', 'PANEL ABC', CX, 79.0, 270, {1: 'A_SIG', 2: 'B_SIG', 3: 'C_TX', 4: 'C_RX', 5: 'C_V', 6: 'GND'})
    b.part('J4', 'xh6', 'POWER BOARD', RX_, 24.0, 270,
           {1: 'MAG_IO', 2: 'GND', 3: '+5V', 4: 'VBAT_SENSE', 5: 'STOP_SENSE', 6: 'SERVO_IO'})
    b.part('J6', 'xh5', 'TOF400C', RX_, 44.0, 270, {1: '3V3', 2: 'GND', 3: 'SDA', 4: 'SCL', 5: '3V3'})
    for ref, y, nm, net in (('J7', 61.0, 'X HOME', 'X_HOME'), ('J8', 69.5, 'Y HOME', 'Y_HOME'), ('J9', 78.0, 'START', 'START'),
                            ('J10', 86.5, 'RED LED', 'LEDR_A')):
        b.part(ref, 'xh2', nm, RX_, y, 270, {1: net, 2: 'GND'})
    # series resistors on the lines into the ESP32, shunts toward the free space above each line
    b.part('R8', 'res', '1k', 42.0, esp(6)[1], 0, {1: 'TMC_TX', 2: 'TMC_UART'})
    b.part('R7', 'res', '10k', 40.0, esp(15)[1], 0, {1: 'A_IO', 2: 'A_SIG'})
    b.part('R5', 'res', '10k', 36.0, esp(16)[1], 0, {1: 'B_IO', 2: 'B_SIG'})
    b.part('R18', 'res', '1k', 40.0, esp(17)[1], 0, {1: 'U1_TX', 2: 'C_TX'})
    b.part('R19', 'res', '10k', 36.0, esp(18)[1], 0, {1: 'U1_RX', 2: 'C_RX'})
    # shunts to GND sit UNDER the ESP32 board between its pin rows (SMD parts are on the copper side, so no clash)
    b.part('R21', 'res', '20k', EL + 4.5, esp(15)[1], 0, {2: 'A_IO', 1: 'GND'})
    b.part('C8', 'c0805', '10nF', EL + 4.5, esp(14)[1], 0, {2: 'A_IO', 1: 'GND'})
    b.part('R6', 'res', '20k', EL + 4.5, esp(16)[1], 0, {2: 'B_IO', 1: 'GND'})
    b.part('R20', 'res', '20k', EL + 4.5, esp(18)[1], 0, {2: 'U1_RX', 1: 'GND'})
    b.part('R12', 'res', '4.7k', 104.0, 46.5, 90, {1: 'SDA', 2: '3V3'})
    b.part('R13', 'res', '4.7k', 104.0, 52.75, 90, {1: '3V3', 2: 'SCL'})
    b.part('R17', 'res', '220R', 76.5, esp(18, True)[1], 0, {1: 'LEDR_A', 2: 'LEDR_IO'})
    b.part('D1', 'sma', 'SS34', 40.0, 90.0, 270, {1: '5V_ESP', 2: '+5V'})
    b.part('F2', 'f1206', 'PTC 0.5A', 19.0, 99.0, 270, {1: 'C_V', 2: '+5V'})
    b.part('C7', 'cp63', '100uF 10V', 56.0, 100.0, 0, {1: '+5V', 2: 'GND'})
    b.holes()

def route(b):
    p = b.pad
    jx = lambda r, n: p(r, n)
    # ---- 3V3: ESP pins 1/2 -> wire links on the top to every driver plug (a copper chain down the left edge would wall
    #      off the ground around the plugs); and along the top edge to the TOF (wire link L3 over the power-plug lines)
    b.track([esp(1), esp(2)], '3V3', SIG)
    b.track([esp(1), (44.0, 15.0)], '3V3', SIG)
    b.link('L4', '3V3', (44.0, 15.0), (X33, 15.0))
    b.link('L5', '3V3', (X33, 15.0), (X33, p('J1', 6)[1]), first_exists=True)
    b.link('L6', '3V3', (X33, p('J1', 6)[1]), (X33, p('J2', 6)[1]), first_exists=True)
    b.link('L7', '3V3', (X33, p('J2', 6)[1]), (X33, p('J3', 6)[1]), first_exists=True)
    for r in ('J1', 'J2', 'J3'):
        b.track([(X33, p(r, 6)[1]), p(r, 6)], '3V3', SIG)
    b.track([esp(1), (EL, TOP3V3), (100.0, TOP3V3), (100.0, 18.5)], '3V3', SIG)
    b.track([p('J4', 2), (111.0, p('J4', 2)[1])], 'GND', SIG)             # ground stubs into the open pour
    b.link('L3', '3V3', (100.0, 18.5), (100.0, 41.0))                    # over the four power-board lines
    b.track([(100.0, 41.0), (103.0, 44.0), p('J6', 1)], '3V3', SIG)
    b.track([(104.0, 44.0), p('R12', 2)], '3V3', SIG)
    b.track([p('R13', 1), p('J6', 5)], '3V3', SIG)
    b.track([p('J6', 1), (111.0, p('J6', 1)[1]), (111.0, p('J6', 5)[1]), p('J6', 5)], '3V3', SIG)
    # ---- driver plugs: EN tied to GND (pin 2 -> pin 1); UART chained on the top by wire links L1, L2
    for r in ('J1', 'J2', 'J3'):
        b.track([p(r, 2), p(r, 1)], 'GND', SIG)
        b.track([p(r, 3), (LNK, p(r, 3)[1])], 'TMC_UART', SIG)
    b.link('L1', 'TMC_UART', (LNK, p('J1', 3)[1]), (LNK, p('J2', 3)[1]))
    b.link('L2', 'TMC_UART', (LNK, p('J2', 3)[1]), (LNK, p('J3', 3)[1]), first_exists=True)
    # X plug: UART -> RX pin and (via R8) TX pin; STEP/DIR down to their pins (DIR lane further from the ESP32)
    b.track([p('J1', 3), (37.0, p('J1', 3)[1]), (38.2, esp(5)[1]), esp(5)], 'TMC_UART', SIG)
    b.track([(37.0, p('J1', 3)[1]), (37.0, esp(6)[1]), p('R8', 2)], 'TMC_UART', SIG)
    b.track([p('R8', 1), esp(6)], 'TMC_TX', SIG)
    b.track([p('J1', 4), (34.0, p('J1', 4)[1]), (34.0, esp(7)[1]), esp(7)], 'X_STEP', SIG)
    b.track([p('J1', 5), (32.0, p('J1', 5)[1]), (32.0, esp(8)[1]), esp(8)], 'X_DIR', SIG)
    # Y / W plugs: up to their pins (the line that ends higher has the lane further from the ESP32)
    for r, ax, ps, pd in (('J2', 'Y', 9, 10), ('J3', 'W', 11, 12)):
        b.track([p(r, 4), (LANE[ax + '_STEP'], p(r, 4)[1]), (LANE[ax + '_STEP'], esp(ps)[1]), esp(ps)], ax + '_STEP', SIG)
        b.track([p(r, 5), (LANE[ax + '_DIR'], p(r, 5)[1]), (LANE[ax + '_DIR'], esp(pd)[1]), esp(pd)], ax + '_DIR', SIG)
    # panel plug: through the series resistors, shunts to GND above / below the lines
    for n, key, net, rref, pin in ((1, 'A', 'A_SIG', 'R7', 15), (2, 'B', 'B_SIG', 'R5', 16), (3, 'CTX', 'C_TX', 'R18', 17),
                                   (4, 'CRX', 'C_RX', 'R19', 18)):
        b.track([p('J5', n), (LANE[key], p('J5', n)[1]), (LANE[key], esp(pin)[1]), p(rref, 2)], net, SIG)
    for rref, pin, net in (('R7', 15, 'A_IO'), ('R5', 16, 'B_IO'), ('R18', 17, 'U1_TX'), ('R19', 18, 'U1_RX')):
        b.track([p(rref, 1), esp(pin)], net, SIG)
    b.track([esp(15), p('R21', 2), p('C8', 2)], 'A_IO', SIG)            # under the ESP32
    b.track([esp(16), p('R6', 2)], 'B_IO', SIG)
    b.track([esp(18), p('R20', 2)], 'U1_RX', SIG)
    # ---- right side: power-board plug
    b.track([p('J4', 1), (104.0, p('J4', 1)[1]), (102.4, esp(4, True)[1]), esp(4, True)], 'MAG_IO', SIG)
    for n, lane, pin, net in ((4, 100.0, 5, 'VBAT_SENSE'), (5, 98.4, 6, 'STOP_SENSE'), (6, 96.8, 7, 'SERVO_IO')):
        b.track([p('J4', n), (lane, p('J4', n)[1]), (lane, esp(pin, True)[1]), esp(pin, True)], net, SIG)
    # TOF: SDA lane further from the ESP32 than SCL; pull-ups to 3V3 at the plug
    b.track([p('J6', 3), (94.0, p('J6', 3)[1]), (94.0, esp(8, True)[1]), esp(8, True)], 'SDA', SIG)
    b.track([p('R12', 1), (104.0, p('J6', 3)[1])], 'SDA', SIG)
    b.track([p('J6', 4), (92.0, p('J6', 4)[1]), (92.0, esp(9, True)[1]), esp(9, True)], 'SCL', SIG)
    b.track([p('R13', 2), (104.0, p('J6', 4)[1])], 'SCL', SIG)
    # home switches, start, red LED
    for ref, lane, pin, net in (('J7', 88.0, 10, 'X_HOME'), ('J8', 85.6, 16, 'Y_HOME'), ('J9', 83.2, 17, 'START')):
        b.track([p(ref, 1), (lane, p(ref, 1)[1]), (lane, esp(pin, True)[1]), esp(pin, True)], net, SIG)
    b.track([esp(18, True), p('R17', 2)], 'LEDR_IO', SIG)
    b.track([p('R17', 1), (80.8, esp(18, True)[1]), (80.8, p('J10', 1)[1]), p('J10', 1)], 'LEDR_A', SIG)
    # ---- +5V: power-board plug -> right edge -> bottom -> 100 uF, ESP32 5V pin (through D1), panel V (through the PTC)
    b.track([p('J4', 3), (P5V_X, p('J4', 3)[1]), (P5V_X, P5V_Y), (p('F2', 2)[0], P5V_Y), p('F2', 2)], '+5V', R5W)
    b.track([(p('D1', 2)[0], P5V_Y), p('D1', 2)], '+5V', R5W)
    b.track([(p('C7', 1)[0], P5V_Y), p('C7', 1)], '+5V', R5W)
    b.track([p('D1', 1), (p('D1', 1)[0], esp(21)[1]), esp(21)], '5V_ESP', R5W)
    b.track([p('F2', 1), (p('F2', 1)[0], p('J5', 5)[1]), p('J5', 5)], 'C_V', R5W)

if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    b = H.Board(W, HGT, 'ETZ controller v1')
    place(b)
    if '--place' in FLAGS:
        for ref in sorted(b.fp):
            if ref[0] in 'RCDF':
                print(ref, [(q.GetNumber(), tuple(round(v, 2) for v in b.pad(ref, q.GetNumber()))) for q in b.fp[ref].Pads()])
    route(b)
    b.gnd_pour()
    b.save(OUT)
    unc, v = H.drc(OUT)
    print('controller board %g x %g mm: %d unconnected, %d errors' % (W, HGT, len(unc), len(v)))
    for x in v[:30]:
        print('  ', x['type'], '|', [i['description'] for i in x['items']][:2])
    for u in unc[:25]:
        print('   UNCONNECTED', [i['description'] for i in u['items']][:2])
    H.render(OUT, os.path.join(OUT_DIR, 'controller_bottom.png'), 'bottom')
