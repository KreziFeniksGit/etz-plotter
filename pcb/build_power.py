"""
POWER BOARD (split board 2 of 3), hand-routed, single-sided (bottom copper), toner transfer -> pcb/power/power.kicad_pcb
In:  J1 XT60  battery (after the inline 5 A fuse): 1 GND, 2 VBAT
     J2 XT30  drive bus back from stop block 1:     1 VDRIVE, 2 GND
Out: J3 XT30  VDRIVE to the driver board
     J4 1x3   MG996R servo: 1 SIG, 2 +5VS, 3 GND (470 uF + 100 nF at the plug)
     J5 JST-XH 6 to the controller: 1 MAG_IO, 2 +5V, 3 GND, 4 VBAT_SENSE, 5 STOP_SENSE, 6 SERVO_IO
     J6 JST-XH 2 magnet: 1 MAG5, 2 MAG_SW      J7 JST-XH 2 stop block 2: 1 +5V out, 2 MAG5 back
     J8 JST-XH 2 green LED (drives powered): 1 LEDG_A, 2 GND
U1 Mini560 Pro 5 V (logic, from VBAT), U2 Mini560 Pro 5 V (servo, from VDRIVE). Q1 IRLZ44N switches the magnet.
Run: "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" pcb\\build_power.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import handroute as H

OUT_DIR = os.path.join(H.HERE, 'power')
OUT = os.path.join(OUT_DIR, 'power.kicad_pcb')
W, HGT = 94.0, 84.0
M560 = 25.4                 # Mini560 Pro: IN pads to OUT pads (VERIFY on your module)
PWR_W, R5_W, SIG_W = 2.0, 1.2, 0.6

def place(b):
    b.part('J1', 'xt60', 'BAT in', 14.0, 12.0, 0, {1: 'GND', 2: 'VBAT'})
    b.part('J2', 'xt30', 'DRIVE in', 44.0, 12.0, 0, {1: 'VDRIVE', 2: 'GND'})
    b.part('J3', 'xt30', 'DRIVE out', 76.0, 12.0, 0, {1: 'VDRIVE', 2: 'GND'})
    b.part('U1A', 'pins2', 'Mini560 5V logic IN', 24.0, 24.0, 270, {1: 'VBAT', 2: 'GND'})
    b.part('U1B', 'pins2', 'Mini560 5V logic OUT', 24.0, 24.0 + M560, 270, {1: '+5V', 2: 'GND'})
    b.part('U2A', 'pins2', 'Mini560 5V servo IN', 60.0, 24.0, 270, {1: 'VDRIVE', 2: 'GND'})
    b.part('U2B', 'pins2', 'Mini560 5V servo OUT', 60.0, 24.0 + M560, 270, {1: '+5VS', 2: 'GND'})
    # controller plug: GND sits between MAG_IO and +5V so the magnet loop cannot cut off a piece of the ground pour
    b.part('J5', 'xh6', 'CONTROLLER', 22.5, 76.0, 0,
           {1: 'MAG_IO', 2: 'GND', 3: '+5V', 4: 'VBAT_SENSE', 5: 'STOP_SENSE', 6: 'SERVO_IO'})
    b.part('J4', 'pins3', 'SERVO', 52.0, 66.0, 270, {1: 'SERVO_SIG', 2: '+5VS', 3: 'GND'})
    b.part('C1', 'cp8', '470uF 16V', 66.0, 60.0, 0, {1: '+5VS', 2: 'GND'})
    b.part('C2', 'c0805', '100nF', 48.2, 70.5, 0, {1: '+5VS', 2: 'GND'})
    b.part('R1', 'res', '1k', 44.0, 74.0, 0, {1: 'SERVO_SIG', 2: 'SERVO_IO'})
    b.part('J7', 'xh2', 'STOP2 5V', 6.0, 44.0, 270, {1: '+5V', 2: 'MAG5'})
    b.part('J6', 'xh2', 'MAGNET', 6.0, 58.0, 270, {1: 'MAG5', 2: 'MAG_SW'})
    b.part('D1', 'sma', 'SS34 flyback', 12.0, 54.0, 270, {1: 'MAG5', 2: 'MAG_SW'})
    b.part('Q1', 'to220', 'IRLZ44N', 8.0, 68.0, 0, {1: 'MAG_G', 2: 'MAG_SW', 3: 'GND'})
    b.part('R2', 'res', '100R', 15.0, 78.0, 0, {1: 'MAG_IO', 2: 'MAG_G'})
    b.part('R3', 'res', '100k', 4.0, 73.0, 90, {1: 'GND', 2: 'MAG_G'})
    b.part('R7', 'res', '100k', 30.0, 30.0, 90, {1: 'VBAT_SENSE', 2: 'VBAT'})
    b.part('R8', 'res', '15k', 33.0, 36.0, 0, {1: 'GND', 2: 'VBAT_SENSE'})
    b.part('R5', 'res', '100k', 38.0, 46.0, 90, {1: 'STOP_SENSE', 2: 'VDRIVE'})
    b.part('R6', 'res', '22k', 34.0, 50.0, 0, {1: 'STOP_SENSE', 2: 'GND'})
    b.part('R4', 'res', '1.5k', 86.0, 22.0, 90, {1: 'LEDG_A', 2: 'VDRIVE'})
    b.part('J8', 'xh2', 'GREEN LED', 86.0, 30.0, 270, {1: 'LEDG_A', 2: 'GND'})
    b.holes()

def route(b):
    p = b.pad
    # VBAT: battery -> logic Mini560 IN and the battery divider
    b.track([p('J1', 2), (24.0, 15.0), p('U1A', 1)], 'VBAT', PWR_W)
    b.track([(24.0, 15.0), (30.0, 21.0), p('R7', 2)], 'VBAT', R5_W)
    b.track([p('R7', 1), (30.0, 36.0), p('J5', 4)], 'VBAT_SENSE', SIG_W)
    b.track([(30.0, 36.0), p('R8', 2)], 'VBAT_SENSE', SIG_W)
    # VDRIVE: stop block 1 -> driver board out, servo Mini560 IN, stop divider, green LED
    b.track([p('J2', 1), (44.0, 17.0), (76.0, 17.0), p('J3', 1)], 'VDRIVE', PWR_W)
    b.track([(60.0, 17.0), p('U2A', 1)], 'VDRIVE', PWR_W)
    b.track([(76.0, 17.0), (86.0, 17.0), p('R4', 2)], 'VDRIVE', R5_W)
    b.track([(44.0, 17.0), (38.0, 23.0), p('R5', 2)], 'VDRIVE', R5_W)
    b.track([p('R4', 1), p('J8', 1)], 'LEDG_A', SIG_W)
    b.track([p('R5', 1), (38.0, 50.0), p('R6', 1)], 'STOP_SENSE', SIG_W)
    b.track([(38.0, 50.0), (38.0, 52.0), (32.0, 58.0), p('J5', 5)], 'STOP_SENSE', SIG_W)
    # +5V logic: Mini560 OUT -> controller plug and stop block 2
    b.track([p('U1B', 1), (24.0, 53.0), (27.5, 56.5), p('J5', 3)], '+5V', R5_W)
    b.track([p('U1B', 1), (24.0, 42.0), (6.0, 42.0), p('J7', 1)], '+5V', R5_W)
    # magnet: MAG5 (back from stop block 2) -> magnet and flyback cathode; MAG_SW -> MOSFET drain
    b.track([p('J7', 2), p('J6', 1)], 'MAG5', R5_W)
    b.track([(6.0, p('D1', 1)[1]), p('D1', 1)], 'MAG5', R5_W)
    b.track([p('D1', 2), (12.0, 60.5), p('J6', 2)], 'MAG_SW', R5_W)
    b.track([(12.0, 60.5), (10.54, 63.0), p('Q1', 2)], 'MAG_SW', R5_W)
    b.track([p('Q1', 1), (8.0, 76.0), (10.0, 78.0), p('R2', 2)], 'MAG_G', SIG_W)
    b.track([(8.0, p('R3', 2)[1]), p('R3', 2)], 'MAG_G', SIG_W)
    b.track([p('J5', 1), (20.0, 78.5), (18.0, 78.5), p('R2', 1)], 'MAG_IO', SIG_W)
    # servo: signal through R1 into the plug from below; +5VS from the servo Mini560 via the 470 uF
    b.track([p('J5', 6), (38.0, 74.0), p('R1', 2)], 'SERVO_IO', SIG_W)
    b.track([p('R1', 1), (52.0, 74.0), p('J4', 1)], 'SERVO_SIG', SIG_W)
    b.track([p('U2B', 1), (60.0, 55.0), (p('C1', 1)[0], 55.0), p('C1', 1)], '+5VS', R5_W)
    b.track([(60.0, 55.0), (49.46, 58.0), p('J4', 2)], '+5VS', R5_W)
    b.track([p('J4', 2), p('C2', 1)], '+5VS', R5_W)

if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    b = H.Board(W, HGT, 'ETZ power v1')
    place(b)
    route(b)
    b.gnd_pour()
    b.save(OUT)
    unc, v = H.drc(OUT)
    print('power board %g x %g mm: %d unconnected, %d errors' % (W, HGT, len(unc), len(v)))
    for x in v[:25]:
        print('  ', x['type'], '|', [i['description'] for i in x['items']][:2])
    for u in unc[:20]:
        print('   UNCONNECTED', [i['description'] for i in u['items']][:2])
    H.render(OUT, os.path.join(OUT_DIR, 'power_bottom.png'), 'bottom')
