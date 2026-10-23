"""
ETZ plotter main control PCB: parts, nets and placement -> pcb/etz_control.kicad_pcb  (KiCad 10, pcbnew API)
==========================================================================================================
Source of truth for the connections: wiring.md (power tree, ESP32-S3 pin map) and pcb/bom.md (parts).
Run with KiCad's own Python:  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" pcb\\build_pcb.py
Then check:  kicad-cli pcb drc pcb\\etz_control.kicad_pcb
Units mm, origin = board top-left corner, y down (KiCad convention). Plug-in modules sit on female headers.
Everything marked VERIFY is a guess about a bought module: check it before ordering.
HOME = True: single-sided board for toner transfer at home (Egor, 22 Oct): copper on the bottom only, traces >= 0.5 mm,
0.6 mm spacing, big oval pads, no vias; connections that do not fit on one side become insulated wire jumpers on the top
(listed in etz_control_jumpers.txt). HOME = False: the 2-layer JLCPCB version.
"""
import os, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
FP = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), 'share', 'kicad', 'footprints')
OUT = os.path.join(HERE, 'etz_control.kicad_pcb')

# =============================================================================
# 1. PARAMETERS
# =============================================================================
HOME = True                           # home-made board (toner transfer)
HOME_SIDES = 2                        # 2: copper both sides, part pins soldered on the bottom only, top = crossings between wire-through holes
SC = 1.3 if HOME else 1.0             # layout spread: more room between parts for 0.5 mm traces and 0.6 mm gaps
BOARD_W, BOARD_H = round(130.0 * SC), round(105.0 * SC)
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
    xh6='Connector_JST:JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical',
    res='Resistor_SMD:R_1206_3216Metric_Pad1.30x1.75mm_HandSolder' if HOME else 'Resistor_SMD:R_0805_2012Metric_Pad1.20x1.40mm_HandSolder',
    c0805='Capacitor_SMD:C_1206_3216Metric_Pad1.33x1.80mm_HandSolder' if HOME else 'Capacitor_SMD:C_0805_2012Metric_Pad1.18x1.45mm_HandSolder',
    to220='Package_TO_SOT_THT:TO-220-3_Vertical',                # IRLZ44N: 1 G, 2 D, 3 S
    cp63='Capacitor_SMD:CP_Elec_6.3x7.7',                        # pad 1 = +
    cp8='Capacitor_SMD:CP_Elec_8x10',
    cp5='Capacitor_SMD:CP_Elec_5x5.4',
    dpak='Package_TO_SOT_SMD:TO-252-2',                          # 100N03A (UMW): 1 G, 2 D (tab), 3 S
    sma='Diode_SMD:D_SMA_Handsoldering',                         # SS34 Schottky, pad 1 = cathode
    sot23='Package_TO_SOT_SMD:SOT-23',                           # AO3400: 1 G, 2 S, 3 D
    f1206='Fuse:Fuse_1206_3216Metric_Pad1.42x1.75mm_HandSolder',
    xt60='Connector_AMASS:AMASS_XT60PW-M_1x02_P7.20mm_Horizontal',   # pad 1 = -, pad 2 = +
    xt30='Connector_AMASS:AMASS_XT30PW-M_1x02_P2.50mm_Horizontal',   # male;   pad 1 = -, pad 2 = + (checked 23 Oct)
    xt30f='Connector_AMASS:AMASS_XT30PW-F_1x02_P2.50mm_Horizontal',  # female; pad 1 = -, pad 2 = +
    tp='TestPoint:TestPoint_THTPad_D2.0mm_Drill1.0mm',
    hole='MountingHole:MountingHole_3.2mm_M3',
)

# =============================================================================
# 2. PARTS AND NETS   ref: (footprint, value, x, y, rotation deg, {pad: net})
# =============================================================================
P = {}
def part(ref, fp, value, x, y, rot=0.0, pads=None):
    P[ref] = (F[fp], value, x * SC, y * SC, rot, pads or {})

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
    part('C%d' % (i + 1), 'cp8', '100uF 35V', x0 + TMC_ROW / 2, y0 + 25.0, 0, {1: 'VDRIVE', 2: 'GND'})
    if i < 3:                                                         # motor connectors on the right edge (pin order VERIFY with the motor cable)
        part('J%d' % (i + 1), 'xh4', '%s motor' % ax, 124.0, 24.0 + i * 15.0, 90,
             {1: '%s_1A' % ax, 2: '%s_1B' % ax, 3: '%s_2A' % ax, 4: '%s_2B' % ax})
part('J4', 'xh4', 'spare motor', 124.0, 69.0, 90, {1: 'S_1A', 2: 'S_1B', 3: 'S_2A', 4: 'S_2B'})

# power
part('J10', 'xt60', 'BAT', 17.0, 14.0, 0, {1: 'GND', 2: 'VBAT'})
part('J11', 'xt30', 'DRIVE', 42.0, 13.0, 0, {1: 'VDRIVE', 2: 'GND'})
for ref, x, vin, vout, val in (('U5', 62.0, 'VBAT', '+5V', 'Mini560 Pro 5V logic'), ('U6', 96.0, 'VDRIVE', '+5VS', 'Mini560 Pro 5V servo')):
    part(ref + 'A', 'pins2', val + ' IN', x, 94.0, 90, {1: vin, 2: 'GND'})
    part(ref + 'B', 'pins2', val + ' OUT', x + MINI560_PITCH, 94.0, 90, {1: vout, 2: 'GND'})
part('D1', 'sma', 'SS34', 44.0, 90.0, 0, {1: '5V_ESP', 2: '+5V'})
part('C7', 'cp63', '100uF 10V', 50.0, 80.0, 0, {1: '+5V', 2: 'GND'})
part('F2', 'f1206', 'PTC 0.5A', 40.0, 84.0, 0, {1: '+5V', 2: 'C_V'})

# level shifter (BSS138 module, SparkFun BOB-12009 pin order VERIFY): LV row LV1 LV2 LV GND LV3 LV4, HV row HV1 HV2 HV GND HV3 HV4
# connector C UART without a level shifter (Egor, 22 Oct): TX 3.3 V through 1 k (a 5 V device reads it as high),
# RX from a 5 V device through a 10 k / 20 k divider (5 V -> 3.3 V); resistors R18..R20 below

# magnet switch
if HOME:   # SOT-23 pins are too close for 0.6 mm toner gaps: logic-level IRLZ44N in TO-220 (Rds 0.035 ohm at 4 V; fine at 3.3 V for 0.5 A)
    part('Q1', 'to220', 'IRLZ44N', 56.0, 72.0, 0, {1: 'MAG_G', 2: 'MAG_SW', 3: 'GND'})
else:
    part('Q1', 'sot23', 'AO3400A', 56.0, 72.0, 0, {1: 'MAG_G', 2: 'GND', 3: 'MAG_SW'})
part('D2', 'sma', 'SS34 flyback', 44.0, 72.0, 0, {1: 'MAG5', 2: 'MAG_SW'})

# servo rail
part('C5', 'cp8', '470uF 16V', 112.0, 82.0, 0, {1: '+5VS', 2: 'GND'})
part('C6', 'c0805', '100nF', 108.0, 90.0, 0, {1: '+5VS', 2: 'GND'})

# small connectors along the top edge
part('J5', 'pins3', 'SERVO', 49.0, 9.0, 0, {1: 'SERVO_SIG', 2: '+5VS', 3: 'GND'})
part('J6', 'xh2', 'MAGNET', 59.0, 6.0, 0, {1: 'MAG5', 2: 'MAG_SW'})
part('J12', 'xh2', 'STOP2 5V', 68.5, 6.0, 0, {1: '+5V', 2: 'MAG5'})
part('J7', 'xh2', 'X HOME', 78.0, 6.0, 0, {1: 'X_HOME', 2: 'GND'})
part('J8', 'xh2', 'Y HOME', 87.5, 6.0, 0, {1: 'Y_HOME', 2: 'GND'})
part('J9', 'xh5', 'TOF400C', 97.0, 6.0, 0, {1: '3V3', 2: 'GND', 3: 'SDA', 4: 'SCL', 5: 'TOF_XSHUT'})
# panel side (bottom-left)
# panel cable to the A / B / C header strip (Egor, 22 Oct): 6 wires; on the strip the three V pins share pin 5 (5 V through
# the 0.5 A PTC) and the three GND pins share pin 6
part('J17', 'xh6', 'PANEL ABC', 8.0, 89.0, 0, {1: 'A_SIG', 2: 'B_SIG', 3: 'C_TX', 4: 'C_RX', 5: 'C_V', 6: 'GND'})
part('J14', 'xh2', 'GREEN LED', 24.0, 98.0, 0, {1: 'LEDG_A', 2: 'GND'})
part('J15', 'xh2', 'RED LED', 33.0, 98.0, 0, {1: 'LEDR_A', 2: 'GND'})
part('J16', 'xh2', 'START', 42.0, 98.0, 0, {1: 'START', 2: 'GND'})

# resistors (vertical, 2.54 mm) in a grid between the ESP32 and the drivers
RES = [('R1', '100k', 'VDRIVE', 'STOP_SENSE'), ('R2', '22k', 'STOP_SENSE', 'GND'), ('R3', '100k', 'VBAT', 'VBAT_SENSE'),
       ('R4', '15k', 'VBAT_SENSE', 'GND'), ('R5', '10k', 'B_SIG', 'B_IO'), ('R6', '20k', 'B_IO', 'GND'),
       ('R7', '10k', 'A_SIG', 'A_IO'), ('R8', '1k', 'TMC_TX', 'TMC_UART'), ('R9', '1k', 'SERVO_IO', 'SERVO_SIG'),
       ('R10', '10k', 'DRV_EN', '3V3'), ('R11', '10k', 'TOF_XSHUT', '3V3'), ('R12', '4.7k', 'SDA', '3V3'),
       ('R13', '4.7k', 'SCL', '3V3'), ('R14', '100R', 'MAG_IO', 'MAG_G'), ('R15', '100k', 'MAG_G', 'GND'),
       ('R16', '1.5k 0.25W', 'VDRIVE', 'LEDG_A'), ('R17', '220R', 'LEDR_IO', 'LEDR_A'),
       ('R18', '1k', 'U1_TX', 'C_TX'), ('R19', '10k', 'C_RX', 'U1_RX'), ('R20', '20k', 'U1_RX', 'GND'),
       ('R21', '20k', 'A_IO', 'GND')]          # A: 0..5 V sensor -> 0..3.3 V at GPIO1 (R7 / R21)
for k, (ref, val, a, b) in enumerate(RES):
    part(ref, 'res', val, 40.0 + (k % 5) * 4.6, 44.0 + (k // 5) * 5.5, 90, {1: a, 2: b})
part('C8', 'c0805', '10nF', 27.0, 84.0, 0, {1: 'A_IO', 2: 'GND'})

# test points and mounting holes
for k, (ref, net) in enumerate((('TP1', '3V3'), ('TP2', '+5V'), ('TP3', '+5VS'), ('TP4', 'GND'))):
    part(ref, 'tp', net, 100.0 + k * 4.5, 99.0, 0, {1: net})
for k, (x, y) in enumerate(((HOLE_INSET, HOLE_INSET), (BOARD_W - HOLE_INSET, HOLE_INSET),
                            (HOLE_INSET, BOARD_H - HOLE_INSET), (BOARD_W - HOLE_INSET, BOARD_H - HOLE_INSET))):
    part('H%d' % (k + 1), 'hole', 'M3', x / SC, y / SC)

# =============================================================================
# 3. RULES
#   fab  (HOME False): JLCPCB 2-layer 1 oz limits with margin; widths by current (IPC-2152, ~10 C rise, outer layer)
#   home (HOME True):  toner transfer - nothing under 0.5 mm, 0.6 mm gaps, wider power (etched copper is uneven)
# =============================================================================
if HOME:
    FAB = dict(track_min=0.5, clearance_min=0.5, via_min=0.6, drill_min=0.8, hole_to_hole=0.5, edge=0.8, annular=0.3)
    CLASSES = {   # name: (track mm, clearance mm, via dia, via drill, nets)
        # "vias" = 0.9 mm holes you drill; an insulated wire on the top joins two of them (soldered underneath)
        'Default': (0.6, 0.6, 2.0, 0.9, []),
        'Power':   (2.0, 0.8, 2.4, 1.1, ['VBAT', 'VDRIVE']),
        'Rail5V':  (1.2, 0.6, 2.0, 0.9, ['+5V', '+5VS', '5V_ESP', 'MAG5', 'MAG_SW', 'C_V']),
        'Motor':   (1.0, 0.6, 2.0, 0.9, [a + s for a in 'XYWS' for s in ('_1A', '_1B', '_2A', '_2B')]),
        'Ground':  (1.2, 0.6, 2.0, 0.9, ['GND']),
    }
    HDR_PAD = (1.7, 2.6, 1.0)     # oval pad on 2.54 mm rows: 1.7 along the row (0.84 gap), 2.6 across, 1.0 drill
else:
    FAB = dict(track_min=0.15, clearance_min=0.15, via_min=0.6, drill_min=0.3, hole_to_hole=0.5, edge=0.4, annular=0.15)
    CLASSES = {
        'Default': (0.3, 0.2, 0.8, 0.4, []),
        'Power':   (1.5, 0.3, 1.0, 0.5, ['VBAT', 'VDRIVE']),                                    # up to ~4 A (drivers + servo)
        'Rail5V':  (1.0, 0.25, 1.0, 0.5, ['+5V', '+5VS', '5V_ESP', 'MAG5', 'MAG_SW', 'C_V']),   # magnet 0.5 A, servo stall ~2.5 A
        'Motor':   (0.8, 0.25, 0.8, 0.4, [a + s for a in 'XYWS' for s in ('_1A', '_1B', '_2A', '_2B')]),   # 0.9 A RMS
        'Ground':  (1.0, 0.25, 0.8, 0.4, ['GND']),
    }
STITCH_PITCH = 10.0           # fab version: GND stitching vias between the two ground pours

def mm(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))

def set_rules(board):
    ds = board.GetDesignSettings()
    ds.m_TrackMinWidth = pcbnew.FromMM(FAB['track_min'])
    ds.m_MinClearance = pcbnew.FromMM(FAB['clearance_min'])
    ds.m_ViasMinSize = pcbnew.FromMM(FAB['via_min'])
    ds.m_MinThroughDrill = pcbnew.FromMM(FAB['drill_min'])
    ds.m_HoleToHoleMin = pcbnew.FromMM(FAB['hole_to_hole'])
    ds.m_CopperEdgeClearance = pcbnew.FromMM(FAB['edge'])
    ds.m_ViasMinAnnularWidth = pcbnew.FromMM(FAB['annular'])
    ns = ds.m_NetSettings
    for name, (tw, cl, vd, vdr, nets) in CLASSES.items():
        nc = ns.GetDefaultNetclass() if name == 'Default' else pcbnew.NETCLASS(name)
        nc.SetTrackWidth(pcbnew.FromMM(tw)); nc.SetClearance(pcbnew.FromMM(cl))
        nc.SetViaDiameter(pcbnew.FromMM(vd)); nc.SetViaDrill(pcbnew.FromMM(vdr))
        if name != 'Default':
            ns.SetNetclass(name, nc)
            for n in nets:
                ns.SetNetclassPatternAssignment(n, name)
    ns.RecomputeEffectiveNetclasses()
    board.SynchronizeNetsAndNetClasses(True)

def home_pads(fp):
    """HOME: SMD parts go to the copper (bottom) side; 2.54 mm-row through-hole pads become big ovals (1.0 mm drill)."""
    pads = list(fp.Pads())
    if pads and all(p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD for p in pads):
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        return
    w, l, drill = HDR_PAD
    pth = [p for p in pads if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
    for p in pth:
        q = p.GetPosition()
        near = [o for o in pth if o is not p and 2.3 < pcbnew.ToMM((o.GetPosition() - q).EuclideanNorm()) < 2.8]
        if not near or pcbnew.ToMM(p.GetSize().x) > 2.2:
            continue                                   # big pads (XT, test points) stay as they are
        dirs = {abs((o.GetPosition() - q).x) > abs((o.GetPosition() - q).y) for o in near}
        if len(dirs) == 2:                             # neighbours both ways (2-row header): round 1.9 mm, 0.64 gaps
            p.SetShape(pcbnew.PAD_SHAPE_CIRCLE); p.SetSize(mm(1.9, 1.9)); p.SetDrillSize(mm(drill, drill))
            continue
        along_x = dirs.pop()                           # row direction in board coordinates
        ang = p.GetOrientation().AsDegrees() % 180
        if abs(ang - 90) < 1:
            along_x = not along_x                      # pad frame is turned 90 degrees
        p.SetShape(pcbnew.PAD_SHAPE_OVAL)
        p.SetSize(mm(w, l) if along_x else mm(l, w))
        p.SetDrillSize(mm(drill, drill))
    if HOME_SIDES == 2:                                # no plated holes at home: pins are soldered on the bottom only,
        for p in pth:                                  # so their pads have no top copper (top traces end at via holes)
            ls = pcbnew.LSET(); ls.AddLayer(pcbnew.B_Cu); ls.AddLayer(pcbnew.B_Mask)
            p.SetLayerSet(ls)

# =============================================================================
# 4. BUILD: footprints + nets + outline + title
# =============================================================================
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
        if ref.startswith('J'):                       # connector names on the silkscreen (what plugs in where)
            v = fp.Value(); v.SetLayer(pcbnew.F_SilkS); v.SetVisible(True)
            v.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.9), pcbnew.FromMM(0.9))); v.SetTextThickness(pcbnew.FromMM(0.15))
        board.Add(fp)
        if HOME:
            home_pads(fp)
        for pad in fp.Pads():
            num = pad.GetNumber()
            n = pads.get(int(num)) if num.isdigit() else None
            if n:
                pad.SetNet(net(n))
        missing = set(pads) - set(int(p.GetNumber()) for p in fp.Pads() if p.GetNumber().isdigit())
        if missing:
            raise RuntimeError('%s has no pads %s' % (ref, missing))
    r = pcbnew.PCB_SHAPE(board)
    r.SetShape(pcbnew.SHAPE_T_RECT)
    r.SetStart(mm(0, 0)); r.SetEnd(mm(BOARD_W, BOARD_H))
    r.SetLayer(pcbnew.Edge_Cuts); r.SetWidth(pcbnew.FromMM(0.1))
    board.Add(r)
    for layer, mirror, txt in ((pcbnew.F_SilkS, False, 'ETZ plotter control v1.0 2026-10'),) + (
            ((pcbnew.B_Cu, True, 'ETZ CONTROL v1.0 BOTTOM'),) if HOME else ()) + (
            ((pcbnew.F_Cu, False, 'ETZ CONTROL v1.0 TOP'),) if HOME and HOME_SIDES == 2 else ()):
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetPosition(mm(BOARD_W / 2 + 8, BOARD_H - 2.5)); t.SetLayer(layer); t.SetMirrored(mirror)
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.5), pcbnew.FromMM(1.5))); t.SetTextThickness(pcbnew.FromMM(0.3))
        board.Add(t)
    set_rules(board)
    return board, nets

# =============================================================================
# 5. ROUTE (Freerouting) + ground pours
# =============================================================================
TOOLS = os.path.join(os.path.expanduser('~'), 'tools')
JAVA = os.path.join(TOOLS, 'jre25', 'jdk-25.0.4.1+1-jre', 'bin', 'java.exe')      # Freerouting 2.5 needs Java 25
FREEROUTING = os.path.join(TOOLS, 'freerouting-2.5.0.jar')

def keepout(board, layers, tracks, vias, tag):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(tracks); z.SetDoNotAllowVias(vias)
    z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False); z.SetDoNotAllowZoneFills(False)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    z.SetZoneName(tag)
    ol = z.Outline(); ol.NewOutline()
    for x, y in ((0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)):
        ol.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(z)
    return z

def freeroute(board, passes, tag):
    import subprocess
    dsn, ses = OUT[:-10] + '.dsn', OUT[:-10] + '.ses'
    if os.path.exists(ses):
        os.remove(ses)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise RuntimeError('DSN export failed')
    cmd = [JAVA, '-jar', FREEROUTING, '-de', dsn, '-do', ses, '-mp', str(passes), '--gui.enabled=false']
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    open(OUT[:-10] + '_freerouting_%s.log' % tag, 'w').write(r.stdout + r.stderr)
    if not os.path.exists(ses):
        raise RuntimeError('Freerouting made no SES file (see the log)')
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise RuntimeError('SES import failed')

def route(board, passes=40):
    if not HOME or HOME_SIDES == 2:
        freeroute(board, passes, 'home2' if HOME else 'fab')
        return
    # pass 1: bottom copper only, no vias
    k1 = keepout(board, (pcbnew.F_Cu,), True, True, 'top: no tracks (pass 1)')
    k2 = keepout(board, (pcbnew.B_Cu,), False, True, 'no vias')
    freeroute(board, passes, 'bottom')
    # pass 2: what is left goes on the top as insulated wire jumpers; 'vias' are holes you drill for the wire ends
    board.Remove(k1); board.Remove(k2)
    for t in board.GetTracks():
        t.SetLocked(True)
    freeroute(board, passes, 'jumpers')
    for t in board.GetTracks():
        t.SetLocked(False)

def pours(board):
    gnd = board.FindNet('GND')
    for layer in ((pcbnew.B_Cu,) if HOME and HOME_SIDES == 1 else (pcbnew.F_Cu, pcbnew.B_Cu)):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer); z.SetNet(gnd)
        z.SetLocalClearance(pcbnew.FromMM(0.8 if HOME else 0.3))
        z.SetMinThickness(pcbnew.FromMM(0.6 if HOME else 0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(pcbnew.FromMM(0.6 if HOME else 0.4)); z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.8 if HOME else 0.5))
        ol = z.Outline(); ol.NewOutline()
        e = 1.0 if HOME else 0.5
        for x, y in ((e, e), (BOARD_W - e, e), (BOARD_W - e, BOARD_H - e), (e, BOARD_H - e)):
            ol.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
        board.Add(z)

def stitch(board):
    """GND vias on a grid wherever both pours have room (fab version only)."""
    gnd = board.FindNet('GND')
    filler = pcbnew.ZONE_FILLER(board); filler.Fill(board.Zones())
    if HOME:
        return 0
    zf = [z for z in board.Zones() if z.GetLayer() == pcbnew.F_Cu][0]
    zb = [z for z in board.Zones() if z.GetLayer() == pcbnew.B_Cu][0]
    n = 0
    y = STITCH_PITCH / 2
    while y < BOARD_H:
        x = STITCH_PITCH / 2
        while x < BOARD_W:
            ok = True
            for dx, dy in ((0, 0), (0.8, 0), (-0.8, 0), (0, 0.8), (0, -0.8)):
                q = mm(x + dx, y + dy)
                if not (zf.GetFilledPolysList(pcbnew.F_Cu).Contains(q) and zb.GetFilledPolysList(pcbnew.B_Cu).Contains(q)):
                    ok = False; break
            if ok:
                v = pcbnew.PCB_VIA(board); v.SetPosition(mm(x, y)); v.SetNet(gnd)
                v.SetWidth(pcbnew.FromMM(0.8)); v.SetDrill(pcbnew.FromMM(0.4))
                board.Add(v); n += 1
            x += STITCH_PITCH
        y += STITCH_PITCH
    filler.Fill(board.Zones())
    return n

def jumpers(board):
    """HOME: top-side (F.Cu) tracks = insulated wires on the component side. Each connected top run is one wire; its ends
    are through-hole pads or drilled 'via' holes (soldered on the copper side). Returns (lines, number of holes)."""
    top = [t for t in board.GetTracks() if t.GetLayer() == pcbnew.F_Cu and t.Type() == pcbnew.PCB_TRACE_T]
    vias = [v for v in board.GetTracks() if v.Type() == pcbnew.PCB_VIA_T]
    key = lambda q: (round(pcbnew.ToMM(q.x), 2), round(pcbnew.ToMM(q.y), 2))
    parent = {}
    def find(a):
        while parent.setdefault(a, a) != a:
            a = parent[a]
        return a
    for t in top:
        a, b = find(key(t.GetStart())), find(key(t.GetEnd()))
        parent[a] = b
    runs = {}
    for t in top:
        runs.setdefault(find(key(t.GetStart())), []).append(t)
    out = []
    for i, segs in enumerate(sorted(runs.values(), key=lambda s: s[0].GetNetname())):
        pts = {key(q): q for t in segs for q in (t.GetStart(), t.GetEnd())}
        ends = set()
        for k, q in pts.items():
            for p in board.GetPads():
                if p.GetNetname() == segs[0].GetNetname() and p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH and p.HitTest(q):
                    ends.add('%s.%s' % (p.GetParentFootprint().GetReference(), p.GetNumber()))
            for v in vias:
                if key(v.GetPosition()) == k:
                    ends.add('hole(%.1f,%.1f)' % k)
        L = sum(pcbnew.ToMM(t.GetLength()) for t in segs)
        out.append('W%-3d %-11s %-70s ~%.0f mm' % (i + 1, segs[0].GetNetname(), ' <-> '.join(sorted(ends)), L))
    return out, len(vias)

if __name__ == '__main__':
    do_route = '--no-route' not in sys.argv
    board, nets = build()
    single = sorted(n for n in nets if sum(1 for p in board.GetPads() if p.GetNetname() == n) < 2)
    print('board %g x %g mm, %d footprints, %d nets, %s' % (BOARD_W, BOARD_H, len(P), len(nets), 'HOME single-sided' if HOME else 'fab 2-layer'))
    print('nets with only one pad (check):', single or 'none')
    if do_route:
        route(board)
        pours(board)
        print('stitching vias:', stitch(board))
        print('tracks:', len(board.GetTracks()))
        if HOME and HOME_SIDES == 2:
            vias = [v for v in board.GetTracks() if v.Type() == pcbnew.PCB_VIA_T]
            open(OUT[:-10] + '_vias.txt', 'w').write(
                'Wire-through holes (0.9 mm drill): push a bare wire through, solder top and bottom, cut flush.\n'
                'x, y in mm from the board top-left corner (top view), net\n' +
                ''.join('%.2f, %.2f, %s\n' % (pcbnew.ToMM(v.GetPosition().x), pcbnew.ToMM(v.GetPosition().y), v.GetNetname()) for v in vias))
            print('wire-through holes (vias):', len(vias), ' top tracks:', sum(1 for t in board.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T and t.GetLayer() == pcbnew.F_Cu))
        elif HOME:
            J, nv = jumpers(board)
            open(OUT[:-10] + '_jumpers.txt', 'w').write(
                'Top-side wire jumpers: insulated wire on the component side; each end goes through a pad or a drilled hole\n'
                '(hole(x,y) = mm from the board top-left corner, 0.9 mm drill) and is soldered on the copper side.\n'
                + '\n'.join(J) + '\n')
            print('jumper wires:', len(J), 'drilled jumper holes:', nv)
    pcbnew.SaveBoard(OUT, board)
    b2 = pcbnew.LoadBoard(OUT)              # attach the project (etz_control.kicad_pro): net classes live there
    set_rules(b2)
    pcbnew.SaveBoard(OUT, b2)
    print('saved', OUT, '+ .kicad_pro')
