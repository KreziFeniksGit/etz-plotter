"""
ETZ plotter main control PCB: parts, nets and placement -> pcb/etz_control.kicad_pcb  (KiCad 10, pcbnew API)
==========================================================================================================
Source of truth for the connections: wiring.md (power tree, ESP32-S3 pin map) and pcb/bom.md (parts).
Run with KiCad's own Python:  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" pcb\\build_pcb.py
Then check:  kicad-cli pcb drc pcb\\etz_control.kicad_pcb
Units mm, origin = board top-left corner, y down (KiCad convention). Plug-in modules sit on female headers.
Not routed here (traces come next). Everything marked VERIFY is a guess about a bought module: check it before ordering.
"""
import os, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
FP = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), 'share', 'kicad', 'footprints')
OUT = os.path.join(HERE, 'etz_control.kicad_pcb')

# =============================================================================
# 1. PARAMETERS
# =============================================================================
BOARD_W, BOARD_H = 130.0, 105.0
HOLE_INSET = 4.0                      # M3 mounting holes, 4 mm from each corner
ESP_ROW = 22.86                       # ESP32-S3-DevKitC-1 pin row spacing (VERIFY with calipers: 0.9" on most boards)
TMC_ROW = 12.7                        # StepStick / BTT TMC2209 V1.3 pin rows
LS_ROW = 12.7                         # BSS138 level shifter rows (VERIFY: SparkFun BOB-12009 style, 0.5")
MINI560_PITCH = 25.4                  # Mini560 Pro: IN pads at one end, OUT pads at the other (VERIFY on your module)

# footprints
F = dict(
    sock22='Connector_PinSocket_2.54mm:PinSocket_1x22_P2.54mm_Vertical',
    sock8='Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical',
    sock6='Connector_PinSocket_2.54mm:PinSocket_1x06_P2.54mm_Vertical',
    pins2='Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
    pins3='Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
    xh2='Connector_JST:JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical',
    xh4='Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical',
    xh5='Connector_JST:JST_XH_B5B-XH-A_1x05_P2.50mm_Vertical',
    term2='TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal',
    idc10='Connector_IDC:IDC-Header_2x05_P2.54mm_Vertical',
    res='Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P2.54mm_Vertical',
    cp63='Capacitor_THT:CP_Radial_D6.3mm_P2.50mm',
    cp8='Capacitor_THT:CP_Radial_D8.0mm_P3.50mm',
    cdisc='Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm',
    do41='Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal',          # pad 1 = cathode
    sot23='Package_TO_SOT_SMD:SOT-23',                           # AO3400: 1 G, 2 S, 3 D
    f1206='Fuse:Fuse_1206_3216Metric',
    tp='TestPoint:TestPoint_THTPad_D2.0mm_Drill1.0mm',
    hole='MountingHole:MountingHole_3.2mm_M3',
)

# =============================================================================
# 2. PARTS AND NETS   ref: (footprint, value, x, y, rotation deg, {pad: net})
# =============================================================================
P = {}
def part(ref, fp, value, x, y, rot=0.0, pads=None):
    P[ref] = (F[fp], value, x, y, rot, pads or {})

# ESP32-S3-DevKitC-1 pin map (Espressif user guide, J1 left / J3 right; VERIFY on your board revision:
# on v1.1 the RGB LED is on GPIO38, which wiring.md uses for the TOF XSHUT - see pcb/README.md)
J1 = ['3V3', '3V3', 'RST', 'IO4', 'IO5', 'IO6', 'IO7', 'IO15', 'IO16', 'IO17', 'IO18', 'IO8', 'IO3', 'IO46', 'IO9', 'IO10',
      'IO11', 'IO12', 'IO13', 'IO14', '5V', 'GND']
J3 = ['GND', 'TX', 'RX', 'IO1', 'IO2', 'IO42', 'IO41', 'IO40', 'IO39', 'IO38', 'IO37', 'IO36', 'IO35', 'IO0', 'IO45', 'IO48',
      'IO47', 'IO21', 'IO20', 'IO19', 'GND', 'GND']
GPIO_NET = {  # wiring.md section 2
    'IO4': 'X_STEP', 'IO5': 'X_DIR', 'IO6': 'Y_STEP', 'IO7': 'Y_DIR', 'IO8': 'W_STEP', 'IO9': 'W_DIR',
    'IO15': 'TMC_TX', 'IO16': 'TMC_UART', 'IO17': 'U1_TX', 'IO18': 'U1_RX', 'IO11': 'SDA', 'IO12': 'SCL', 'IO13': 'DRV_EN',
    'IO14': 'SERVO_IO', 'IO21': 'MAG_IO', 'IO38': 'TOF_XSHUT', 'IO39': 'X_HOME', 'IO40': 'Y_HOME', 'IO41': 'START',
    'IO42': 'LEDR_IO', 'IO47': 'STOP_SENSE', 'IO10': 'B_IO', 'IO1': 'A_IO', 'IO2': 'VBAT_SENSE',
    '3V3': '3V3', '5V': '5V_ESP', 'GND': 'GND'}
def esp_pads(names):
    return {i + 1: GPIO_NET[n] for i, n in enumerate(names) if n in GPIO_NET}

EX, EY = 10.0, 24.0                                   # ESP32 J1 pin 1
part('U1A', 'sock22', 'ESP32-S3 J1', EX, EY, 0, esp_pads(J1))
part('U1B', 'sock22', 'ESP32-S3 J3', EX + ESP_ROW, EY, 0, esp_pads(J3))

# TMC2209 x4 (BTT V1.3 pinout, VERIFY): left row EN MS1 MS2 PDN_UART (UART) CLK STEP DIR, right row VM GND 2B 2A 1A 1B VDD GND
DRV = [('X', 'X_STEP', 'X_DIR', ('GND', 'GND')), ('Y', 'Y_STEP', 'Y_DIR', ('3V3', 'GND')),
       ('W', 'W_STEP', 'W_DIR', ('GND', '3V3')), ('S', None, None, ('3V3', '3V3'))]      # MS1/MS2 = UART address 0..3
for i, (ax, st, di, (ms1, ms2)) in enumerate(DRV):
    x0, y0 = 66.0 + (i % 2) * 28.0, 22.0 + (i // 2) * 34.0
    n = i + 2 if i < 3 else 7
    part('U%dA' % n, 'sock8', 'TMC2209 %s left' % ax, x0, y0, 0,
         {1: 'DRV_EN', 2: ms1, 3: ms2, 4: 'TMC_UART', 7: st, 8: di} if st else {1: 'DRV_EN', 2: ms1, 3: ms2, 4: 'TMC_UART'})
    part('U%dB' % n, 'sock8', 'TMC2209 %s right' % ax, x0 + TMC_ROW, y0, 0,
         {1: 'VDRIVE', 2: 'GND', 3: '%s_2B' % ax, 4: '%s_2A' % ax, 5: '%s_1A' % ax, 6: '%s_1B' % ax, 7: '3V3', 8: 'GND'})
    part('C%d' % (i + 1), 'cp63', '100uF 35V', x0 + TMC_ROW / 2 - 1.25, y0 + 23.5, 0, {1: 'VDRIVE', 2: 'GND'})
    if i < 3:                                                         # motor connectors on the right edge (pin order VERIFY with the motor cable)
        part('J%d' % (i + 1), 'xh4', '%s motor' % ax, 124.0, 24.0 + i * 15.0, 90,
             {1: '%s_1A' % ax, 2: '%s_1B' % ax, 3: '%s_2A' % ax, 4: '%s_2B' % ax})
part('J4', 'xh4', 'spare motor', 124.0, 69.0, 90, {1: 'S_1A', 2: 'S_1B', 3: 'S_2A', 4: 'S_2B'})

# power
part('J10', 'term2', 'BAT in (after F1)', 12.0, 9.0, 0, {1: 'VBAT', 2: 'GND'})
part('J11', 'term2', 'DRIVE in (after stop 1)', 26.0, 9.0, 0, {1: 'VDRIVE', 2: 'GND'})
for ref, x, vin, vout, val in (('U5', 62.0, 'VBAT', '+5V', 'Mini560 Pro 5V logic'), ('U6', 96.0, 'VDRIVE', '+5VS', 'Mini560 Pro 5V servo')):
    part(ref + 'A', 'pins2', val + ' IN', x, 94.0, 90, {1: vin, 2: 'GND'})
    part(ref + 'B', 'pins2', val + ' OUT', x + MINI560_PITCH, 94.0, 90, {1: vout, 2: 'GND'})
part('D1', 'do41', '1N5819', 40.0, 90.0, 0, {1: '5V_ESP', 2: '+5V'})
part('C7', 'cp63', '100uF 10V', 46.0, 80.0, 0, {1: '+5V', 2: 'GND'})
part('F2', 'f1206', 'PTC 0.5A', 40.0, 84.0, 0, {1: '+5V', 2: 'C_V'})

# level shifter (BSS138 module, SparkFun BOB-12009 pin order VERIFY): LV row LV1 LV2 LV GND LV3 LV4, HV row HV1 HV2 HV GND HV3 HV4
part('U8A', 'sock6', 'BSS138 LV', 42.0, 24.0, 0, {1: 'U1_TX', 2: 'U1_RX', 3: '3V3', 4: 'GND'})
part('U8B', 'sock6', 'BSS138 HV', 42.0 + LS_ROW, 24.0, 0, {1: 'C_TX', 2: 'C_RX', 3: '+5V', 4: 'GND'})

# magnet switch
part('Q1', 'sot23', 'AO3400A', 56.0, 72.0, 0, {1: 'MAG_G', 2: 'GND', 3: 'MAG_SW'})
part('D2', 'do41', '1N5819 flyback', 40.0, 72.0, 0, {1: 'MAG5', 2: 'MAG_SW'})

# servo rail
part('C5', 'cp8', '470uF 16V', 112.0, 82.0, 0, {1: '+5VS', 2: 'GND'})
part('C6', 'cdisc', '100nF', 108.0, 90.0, 0, {1: '+5VS', 2: 'GND'})

# small connectors along the top edge
part('J5', 'pins3', 'SERVO', 44.0, 6.0, 90, {1: 'SERVO_SIG', 2: '+5VS', 3: 'GND'})
part('J6', 'xh2', 'MAGNET', 54.0, 6.0, 0, {1: 'MAG5', 2: 'MAG_SW'})
part('J12', 'xh2', 'STOP block 2 (5V out / magnet 5V back)', 63.0, 6.0, 0, {1: '+5V', 2: 'MAG5'})
part('J7', 'xh2', 'X HOME', 72.0, 6.0, 0, {1: 'X_HOME', 2: 'GND'})
part('J8', 'xh2', 'Y HOME', 81.0, 6.0, 0, {1: 'Y_HOME', 2: 'GND'})
part('J9', 'xh5', 'TOF400C', 90.0, 6.0, 0, {1: '3V3', 2: 'GND', 3: 'SDA', 4: 'SCL', 5: 'TOF_XSHUT'})
# panel side (bottom-left)
part('J17', 'idc10', 'PANEL A B C', 8.0, 89.0, 90,
     {1: 'A_SIG', 2: '3V3', 3: 'GND', 4: 'B_SIG', 5: '+5V', 6: 'GND', 7: 'C_TX', 8: 'C_RX', 9: 'C_V', 10: 'GND'})
part('J14', 'xh2', 'GREEN LED', 24.0, 98.0, 0, {1: 'LEDG_A', 2: 'GND'})
part('J15', 'xh2', 'RED LED', 33.0, 98.0, 0, {1: 'LEDR_A', 2: 'GND'})
part('J16', 'xh2', 'START', 42.0, 98.0, 0, {1: 'START', 2: 'GND'})

# resistors (vertical, 2.54 mm) in a grid between the ESP32 and the drivers
RES = [('R1', '100k', 'VDRIVE', 'STOP_SENSE'), ('R2', '22k', 'STOP_SENSE', 'GND'), ('R3', '100k', 'VBAT', 'VBAT_SENSE'),
       ('R4', '15k', 'VBAT_SENSE', 'GND'), ('R5', '10k', 'B_SIG', 'B_IO'), ('R6', '20k', 'B_IO', 'GND'),
       ('R7', '1k', 'A_SIG', 'A_IO'), ('R8', '1k', 'TMC_TX', 'TMC_UART'), ('R9', '1k', 'SERVO_IO', 'SERVO_SIG'),
       ('R10', '10k', 'DRV_EN', '3V3'), ('R11', '10k', 'TOF_XSHUT', '3V3'), ('R12', '4.7k', 'SDA', '3V3'),
       ('R13', '4.7k', 'SCL', '3V3'), ('R14', '100R', 'MAG_IO', 'MAG_G'), ('R15', '100k', 'MAG_G', 'GND'),
       ('R16', '1.5k 0.25W', 'VDRIVE', 'LEDG_A'), ('R17', '220R', 'LEDR_IO', 'LEDR_A')]
for k, (ref, val, a, b) in enumerate(RES):
    part(ref, 'res', val, 41.0 + (k % 4) * 5.5, 44.0 + (k // 4) * 6.0, 90, {1: a, 2: b})
part('C8', 'cdisc', '10nF', 27.0, 84.0, 0, {1: 'A_IO', 2: 'GND'})

# test points and mounting holes
for k, (ref, net) in enumerate((('TP1', '3V3'), ('TP2', '+5V'), ('TP3', '+5VS'), ('TP4', 'GND'))):
    part(ref, 'tp', net, 106.0 + k * 4.5, 6.0, 0, {1: net})
for k, (x, y) in enumerate(((HOLE_INSET, HOLE_INSET), (BOARD_W - HOLE_INSET, HOLE_INSET),
                            (HOLE_INSET, BOARD_H - HOLE_INSET), (BOARD_W - HOLE_INSET, BOARD_H - HOLE_INSET))):
    part('H%d' % (k + 1), 'hole', 'M3', x, y)

# =============================================================================
# 3. BUILD
# =============================================================================
def mm(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))

def build():
    board = pcbnew.BOARD()
    nets = {}
    def net(name):
        if name not in nets:
            nets[name] = pcbnew.NETINFO_ITEM(board, name)
            board.Add(nets[name])
        return nets[name]
    for ref, (fpid, value, x, y, rot, pads) in P.items():
        lib, name = fpid.split(':')
        fp = pcbnew.FootprintLoad(os.path.join(FP, lib + '.pretty'), name)
        if fp is None:
            raise RuntimeError('footprint not found: ' + fpid)
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.SetPosition(mm(x, y))
        fp.SetOrientationDegrees(rot)
        if ref.startswith('H'):
            fp.Reference().SetVisible(False)
        board.Add(fp)
        for pad in fp.Pads():
            num = pad.GetNumber()
            n = pads.get(int(num)) if num.isdigit() else None
            if n:
                pad.SetNet(net(n))
        missing = set(pads) - set(int(p.GetNumber()) for p in fp.Pads() if p.GetNumber().isdigit())
        if missing:
            raise RuntimeError('%s has no pads %s' % (ref, missing))
    # outline
    r = pcbnew.PCB_SHAPE(board)
    r.SetShape(pcbnew.SHAPE_T_RECT)
    r.SetStart(mm(0, 0))
    r.SetEnd(mm(BOARD_W, BOARD_H))
    r.SetLayer(pcbnew.Edge_Cuts)
    r.SetWidth(pcbnew.FromMM(0.1))
    board.Add(r)
    pcbnew.SaveBoard(OUT, board)
    return board, nets

if __name__ == '__main__':
    board, nets = build()
    single = sorted(n for n in nets if sum(1 for p in board.GetPads() if p.GetNetname() == n) < 2)
    print('board %g x %g mm, %d footprints, %d nets' % (BOARD_W, BOARD_H, len(P), len(nets)))
    print('nets with only one pad (check):', single or 'none')
    print('saved', OUT)
