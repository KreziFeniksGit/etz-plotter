"""
DRIVER BOARD (split board 1 of 3): 3x TMC2209 (X, Y, wrist), hand-routed, single-sided (bottom copper), toner transfer.
-> pcb/drivers/drivers.kicad_pcb
Each driver has its own 6-pin JST-XH from the controller board, pins in the order of the socket pins so the traces
run straight: 1 GND, 2 EN, 3 UART, 4 STEP, 5 DIR, 6 3V3. Motor plug (JST-XH 4) beside the driver's motor pins:
1 2B, 2 2A, 3 1A, 4 1B (swapping a coil's ends only reverses the motor: set the direction in firmware; VERIFY with the motor).
VDRIVE comes in on an XT30 (from the power board) and runs down the right edge as one 2 mm bus; GND = copper pour.
UART addresses by MS1/MS2: X = 0 (GND, GND), Y = 2 (GND, 3V3), wrist = 3 (3V3, 3V3) - no crossing needed for these three.
No spare socket: a spare TMC2209 module plugs into whichever socket failed.
Run: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" pcb\\build_drivers.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handroute as H

OUT_DIR = os.path.join(H.HERE, 'drivers')
OUT = os.path.join(OUT_DIR, 'drivers.kicad_pcb')

# =============================================================================
# 1. PARAMETERS (mm, origin top-left, y down)
# =============================================================================
W, HGT = 64.0, 112.0
UX = 22.0                  # left socket row x
UY0, UPITCH = 26.0, 28.0   # first driver's pin 1 y, distance between drivers
ROW = 12.7                 # TMC2209 pin rows
JST_DX = -9.0              # signal JST column, relative to the left row
MOT_DX = ROW + 9.0         # motor JST column, relative to the left row
BUS_X = W - 5.0            # VDRIVE bus
SIG_W, PWR_W, MOT_W, V33_W = 0.6, 2.0, 1.0, 0.6
DRIVERS = [('X', 'GND', 'GND'), ('Y', 'GND', '3V3'), ('W', '3V3', '3V3')]   # MS1, MS2 -> UART address 0, 2, 3
# each driver's 3V3 comes on its own cable (they join on the controller board), so on this board they are separate nets
V33 = lambda ax: ax + '_3V3'

def place(b):
    for k, (ax, ms1, ms2) in enumerate(DRIVERS):
        ux, uy = UX, UY0 + k * UPITCH
        pre = ax + '_'
        ms1, ms2 = [V33(ax) if m == '3V3' else m for m in (ms1, ms2)]
        b.part('U%dA' % (k + 1), 'sock8', 'TMC2209 %s' % ax, ux, uy, 0,
               {1: pre + 'EN', 2: ms1, 3: ms2, 4: pre + 'UART', 7: pre + 'STEP', 8: pre + 'DIR'})
        b.part('U%dB' % (k + 1), 'sock8', 'TMC2209 %s' % ax, ux + ROW, uy, 0,
               {1: 'VDRIVE', 2: 'GND', 3: pre + '2B', 4: pre + '2A', 5: pre + '1A', 6: pre + '1B', 7: V33(ax), 8: 'GND'})
        b.part('J%d' % (k + 1), 'xh6', '%s signals' % ax, ux + JST_DX, uy, 270,
               {1: 'GND', 2: pre + 'EN', 3: pre + 'UART', 4: pre + 'STEP', 5: pre + 'DIR', 6: V33(ax)})
        b.part('J%d' % (k + 4), 'xh4', '%s motor' % ax, ux + MOT_DX, uy + 5.0, 270,
               {1: pre + '2B', 2: pre + '2A', 3: pre + '1A', 4: pre + '1B'})
        b.part('C%d' % (k + 1), 'cp8', '100uF 25V', ux + ROW + 12.0, uy - 6.5, 0, {1: 'VDRIVE', 2: 'GND'})
    b.part('J7', 'xt30f', 'VDRIVE in (female)', BUS_X - 17.0, 13.0, 0, {1: 'GND', 2: 'VDRIVE'})   # pad 1 = -, pad 2 = +
    b.holes()

# =============================================================================
# 2. HAND ROUTING (every track drawn here; no auto-router)
# =============================================================================
L_DIR, L_STEP, L_FAN = 15.6, 17.2, 17.0     # x lanes between the signal JST (x 13) and the left row (x 22)
L_33 = UX + 3.5                             # 3V3 lane under the module, between the two rows

def route(b):
    for k, (ax, ms1, ms2) in enumerate(DRIVERS):
        uy = UY0 + k * UPITCH
        pre, J, UA, UB, M, C = ax + '_', 'J%d' % (k + 1), 'U%dA' % (k + 1), 'U%dB' % (k + 1), 'J%d' % (k + 4), 'C%d' % (k + 1)
        j = lambda n: b.pad(J, n)
        a = lambda n: b.pad(UA, n)
        r = lambda n: b.pad(UB, n)
        # signals: JST -> left row, in order, no crossings (DIR lane left of the STEP lane)
        b.track([j(2), (L_FAN, j(2)[1]), (L_FAN + 2.5, a(1)[1]), a(1)], pre + 'EN', SIG_W)
        b.track([j(3), (L_FAN, j(3)[1]), (L_FAN + 2.6, a(4)[1]), a(4)], pre + 'UART', SIG_W)
        b.track([j(4), (L_STEP, j(4)[1]), (L_STEP, a(7)[1]), a(7)], pre + 'STEP', SIG_W)
        b.track([j(5), (L_DIR, j(5)[1]), (L_DIR, a(8)[1]), a(8)], pre + 'DIR', SIG_W)
        # 3V3: down from the JST, under the left row's end, up the lane between the rows
        y33 = a(8)[1] + 3.2
        top = r(7)[1]
        pins = [n for n, v in ((2, ms1), (3, ms2)) if v == '3V3']
        v33 = V33(ax)
        if pins:
            top = a(min(pins))[1]
        b.track([j(6), (j(6)[0], y33), (L_33, y33), (L_33, top)], v33, V33_W)
        b.track([(L_33, r(7)[1]), r(7)], v33, V33_W)                         # VIO
        for n in pins:                                                        # MS pins tied to 3V3 (the GND ones go to the pour)
            b.track([(L_33, a(n)[1]), a(n)], v33, V33_W)
        # motor: straight across to the plug
        for n, m in ((3, 1), (4, 2), (5, 3), (6, 4)):
            b.track([r(n), b.pad(M, m)], b.fp[UB].Pads()[n - 1].GetNetname() if False else pre + {3: '2B', 4: '2A', 5: '1A', 6: '1B'}[n], MOT_W)
        # power: VM to the bus, bulk capacitor + to the bus (its - pad sits in the GND pour)
        b.track([r(1), (BUS_X, r(1)[1])], 'VDRIVE', PWR_W)
        b.track([b.pad(C, 1), (BUS_X, b.pad(C, 1)[1])], 'VDRIVE', PWR_W)
    last = UY0 + (len(DRIVERS) - 1) * UPITCH
    x30 = b.pad('J7', 2)
    b.track([x30, (BUS_X, x30[1] + 2.0), (BUS_X, last)], 'VDRIVE', PWR_W)

if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    b = H.Board(W, HGT, 'ETZ drivers v1')
    place(b)
    route(b)
    b.gnd_pour()
    b.save(OUT)
    unc, v = H.drc(OUT)
    print('drivers board %g x %g mm: %d unconnected, %d errors' % (W, HGT, len(unc), len(v)))
    for x in v[:20]:
        print('  ', x['type'], '|', [i['description'] for i in x['items']][:2])
    for u in unc[:20]:
        print('   UNCONNECTED', [i['description'] for i in u['items']][:2])
    H.render(OUT, os.path.join(OUT_DIR, 'drivers_bottom.png'), 'bottom')
    H.render(OUT, os.path.join(OUT_DIR, 'drivers_top.png'), 'top')
