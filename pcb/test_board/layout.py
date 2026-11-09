"""
ETZ plotter control - TEST BOARD, 2-layer (JLCPCB). Board made FROM THE SCHEMATIC (etz_test.kicad_sch -> netlist).
================================================================================================================
Run with KiCad's Python:  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" pcb\\test_board\\layout.py  [passes]
Steps (the order from the pcb-brain notes "Component placement order" and "Routing order and priorities"):
  1. netlist from the schematic (kicad-cli), footprints from the Footprint field, linked to the symbols
  2. placement by zones: connectors on edges, power zone right, drivers + motor plugs top, ESP32 bottom-left
  3. net classes by current, then routing in two passes: power first (Freerouting), then signals around it
  4. GND: one via next to every SMD ground pad, ground pour on both layers, stitching vias
  5. silkscreen labels, revision text in copper, DRC + schematic parity (kicad-cli)
Units mm, origin = board top-left, y down.
"""
import os, sys, math, subprocess, json
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nl

KICAD = os.path.dirname(os.path.dirname(sys.executable))
CLI = os.path.join(KICAD, 'bin', 'kicad-cli.exe')
FPLIB = os.path.join(KICAD, 'share', 'kicad', 'footprints')
SCH = os.path.join(HERE, 'etz_test.kicad_sch')
NET = os.path.join(HERE, 'etz_test.net')
OUT = os.path.join(HERE, 'etz_test.kicad_pcb')
TOOLS = os.path.join(os.path.expanduser('~'), 'tools')
JAVA = os.path.join(TOOLS, 'jre25', 'jdk-25.0.4.1+1-jre', 'bin', 'java.exe')
FREEROUTING = os.path.join(TOOLS, 'freerouting-2.5.0.jar')
PASSES = int(sys.argv[1]) if len(sys.argv) > 1 else 30

W, H = 146.0, 100.0
mm = lambda x, y: pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
toMM = pcbnew.ToMM

# =============================================================================
# 1. RULES (JLCPCB 2-layer 1 oz: 0.127 mm track/space, 0.3 mm drill - we keep margin)
#    widths by current, IPC-2152 outer layer ~10 C rise: 1.5 mm ~3.5 A, 1.0 mm ~2.5 A, 0.8 mm ~2 A
# =============================================================================
FAB = dict(track_min=0.15, clearance_min=0.15, via_min=0.6, drill_min=0.3, hole_to_hole=0.5, edge=0.5, annular=0.13)
MOTOR = [a + s for a in 'XYWS' for s in ('_1A', '_1B', '_2A', '_2B')]
CLASSES = {   # name: (track, clearance, via dia, via drill, nets)
    'Default': (0.3, 0.2, 0.6, 0.3, []),
    'Power':   (1.5, 0.3, 1.0, 0.5, ['VBAT', 'VDRIVE']),                                  # drivers + servo, up to ~4 A
    'Rail5V':  (1.0, 0.25, 0.8, 0.4, ['+5V', '+5VS', '5V_ESP', 'MAG5', 'MAG_SW', 'C_V']),  # servo stall ~2.5 A, magnet 0.5 A
    'Motor':   (0.8, 0.25, 0.8, 0.4, MOTOR),                                               # 0.9 A RMS per phase
    'Rail3V3': (0.5, 0.2, 0.6, 0.3, ['3V3']),
    'Ground':  (1.0, 0.25, 0.6, 0.3, ['GND']),
}
POWER_FIRST = set(sum((v[4] for k, v in CLASSES.items() if k not in ('Default', 'Ground')), []))

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
                ns.SetNetclassPatternAssignment('/' + n, name)
    ns.RecomputeEffectiveNetclasses()
    board.SynchronizeNetsAndNetClasses(True)

# =============================================================================
# 2. PLACEMENT   ref: (x, y, rotation)   x, y = footprint origin (pad 1 for connectors / modules, centre for SMD)
# =============================================================================
PL = {}
# --- stepper strip along the top: driver, bulk cap at VM, 100 nF between VM and GND, motor plug straight above.
#     Left to right W, Y, X, spare: the same order as their STEP/DIR pins on the ESP32 J1 row (no crossings).
#     rot 90: power row (VM GND 2B 2A 1A 1B VIO GND) on top, logic row (EN MS1 MS2 PDN . . STEP DIR) below.
for i, (u, cb, cc, j) in enumerate((('U4', 'C3', 'C11', 'J3'), ('U3', 'C2', 'C10', 'J2'),
                                    ('U2', 'C1', 'C9', 'J1'), ('U7', 'C4', 'C12', 'J4'))):
    x0 = 16.0 + 25.0 * i
    PL[u] = (x0, 29.0, 90)                 # pin 1 (EN); VM pin 9 at (x0, 16.3)
    PL[cb] = (x0 - 3.5, 6.5, 90)           # 100 uF: + pad (bottom) 7 mm from VM
    PL[cc] = (x0 + 1.27, 13.2, 0)          # 100 nF right on VM / GND pins
    PL[j] = (x0 + 12.58, 5.0, 180)         # motor plug: pins over the 2B 2A 1A 1B pins
# --- power zone, right edge: XT30 drive bus and XT60 battery facing out, TVS on the pins, then the two bucks
PL['J11'] = (131.5, 18.0, 270)             # pad 2 (+) at y 13
PL['D4'] = (125.0, 15.5, 270)              # VDRIVE TVS, cathode up
PL['TP6'] = (120.5, 21.5, 0)
PL['TP7'] = (121.0, 26.5, 0)
PL['J10'] = (128.0, 30.0, 270)             # pad 1 (-) y 30, pad 2 (+) y 37.2
PL['D3'] = (121.5, 33.6, 90)               # VBAT TVS, cathode down (next to +)
PL['TP5'] = (121.5, 41.0, 0)
PL['C13'] = (137.0, 43.5, 0)               # U5 input ceramic
PL['U5'] = (141.0, 56.0, 180)              # VBAT -> +5V logic; IN on the right, OUT on the left
PL['C14'] = (137.0, 66.25, 0)              # U6 input ceramic
PL['U6'] = (141.0, 79.0, 180)              # VDRIVE -> +5VS servo
PL['C7'] = (105.0, 57.0, 90)               # +5V bulk at U5 output
PL['C5'] = (128.0, 93.0, 0)                # servo 470 uF next to the servo plug
PL['C6'] = (114.0, 90.5, 0)
PL['J5'] = (112.0, 95.0, 90)               # servo header
PL['R9'] = (109.5, 89.5, 0)
# --- ESP32 DevKit bottom-left, USB end at the left edge; J1 row (driver signals) faces the drivers, J3 row faces the plugs
PL['U1'] = (59.6, 46.0, 270)
PL['D1'] = (5.5, 38.0, 90)                 # +5V -> 5V pin, blocks USB back-feed
PL['R10'] = (14.0, 38.0, 0)                # DRV_EN pull-up (drivers off while the ESP boots)
PL['R8'] = (40.5, 38.0, 0)                 # TMC one-wire UART: TX -> 1k -> RX pin
# --- plugs along the bottom edge, in the order of their ESP32 pins
for ref, x in (('J6', 11), ('J12', 21), ('J9', 30), ('J7', 47), ('J8', 56), ('J16', 65), ('J15', 74), ('J14', 83), ('J17', 92)):
    PL[ref] = (float(x), 95.0, 0)
PL['D2'] = (17.0, 87.0, 0)                 # magnet flyback, right at J6
PL['Q1'] = (26.0, 87.0, 0)
PL['R14'] = (26.0, 82.5, 0)
PL['R15'] = (31.0, 87.0, 90)
PL['R1'] = (12.0, 76.5, 90); PL['R2'] = (16.0, 76.5, 90); PL['C16'] = (20.0, 76.5, 90)    # stop sense at IO47
PL['R3'] = (44.0, 76.5, 90); PL['R4'] = (48.0, 76.5, 90); PL['C15'] = (52.0, 76.5, 90)    # VBAT sense at IO2
PL['R7'] = (56.0, 76.5, 90); PL['R21'] = (60.0, 76.5, 90); PL['C8'] = (64.0, 76.5, 90)    # panel A at IO1
PL['R11'] = (36.0, 86.0, 90); PL['R12'] = (40.0, 86.0, 90); PL['R13'] = (44.0, 86.0, 90)  # TOF pull-ups
PL['R17'] = (75.0, 86.0, 90); PL['R16'] = (84.0, 86.0, 90)                                # LED resistors
for k, r in enumerate(('R5', 'R6', 'R18', 'R19', 'R20')):                                   # panel B and UART C
    PL[r] = (92.0 + 4.0 * k, 86.0, 90)
PL['F2'] = (100.0, 80.0, 0)                # panel 5 V PTC
for k, r in enumerate(('TP1', 'TP2', 'TP3', 'TP4')):
    PL[r] = (72.0 + 5.0 * k, 38.0, 0)
for k, (x, y) in enumerate(((4, 4), (W - 4, 4), (4, H - 4), (W - 4, H - 4))):
    PL['H%d' % (k + 1)] = (float(x), float(y), 0)

LABELS = {'J10': 'BAT XT60', 'J11': 'DRIVE XT30', 'J1': 'X', 'J2': 'Y', 'J3': 'W', 'J4': 'SPARE', 'J5': 'SERVO', 'J6': 'MAGNET',
          'J12': 'STOP2', 'J7': 'X HOME', 'J8': 'Y HOME', 'J9': 'TOF', 'J14': 'LED G', 'J15': 'LED R', 'J16': 'START',
          'J17': 'PANEL', 'U1': 'ESP32-S3 USB <-', 'U2': 'TMC X', 'U3': 'TMC Y', 'U4': 'TMC W', 'U7': 'TMC SPARE',
          'U5': '5V LOGIC', 'U6': '5V SERVO'}

# =============================================================================
# 3. BUILD from the netlist
# =============================================================================
def load_fp(fpid):
    lib, name = fpid.split(':')
    d = os.path.join(HERE, 'etz.pretty') if lib == 'etz' else os.path.join(FPLIB, lib + '.pretty')
    fp = pcbnew.FootprintLoad(d, name)
    if fp is None:
        raise RuntimeError('footprint not found ' + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp

def silk_text(board, txt, x, y, size=1.0, layer=pcbnew.F_SilkS, mirror=False, thick=None):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt); t.SetPosition(mm(x, y)); t.SetLayer(layer); t.SetMirrored(mirror)
    t.SetTextSize(mm(size, size)); t.SetTextThickness(pcbnew.FromMM(thick or size * 0.15))
    board.Add(t)
    return t

def build():
    subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', NET, SCH], check=True, capture_output=True)
    comps, nets = nl.read(NET, keep_unconnected=True)     # unused pins keep KiCad's unconnected-(...) nets
    missing = set(comps) - set(PL)
    if missing:
        raise RuntimeError('no placement for ' + ' '.join(sorted(missing)))
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(2)
    pin_net = {}
    for n, nodes in nets.items():
        for ref, pin in nodes:
            pin_net[(ref, pin)] = n
    netinfo = {}
    for n in sorted(nets):
        netinfo[n] = pcbnew.NETINFO_ITEM(board, n if n.startswith('unconnected-') else '/' + n); board.Add(netinfo[n])     # same names as the schematic (local labels)
    for ref, c in comps.items():
        fp = load_fp(c['footprint'])
        fp.SetReference(ref); fp.SetValue(c['value'])
        fp.SetPath(pcbnew.KIID_PATH('/' + c['tstamp']))     # link to the schematic symbol (Update PCB keeps it)
        fp.SetSheetname('/'); fp.SetSheetfile('etz_test.kicad_sch')
        x, y, rot = PL[ref]
        fp.SetPosition(mm(x, y)); fp.SetOrientationDegrees(rot)
        board.Add(fp)
        for p in fp.Pads():
            n = pin_net.get((ref, p.GetNumber()))
            if n:
                p.SetNet(netinfo[n])
        r = fp.Reference()
        r.SetTextSize(mm(0.8, 0.8)); r.SetTextThickness(pcbnew.FromMM(0.12))
        if ref.startswith('H'):
            r.SetVisible(False)
        if ref in LABELS:                                      # what plugs in where, on the silkscreen
            fp.Value().SetLayer(pcbnew.F_Fab)                # value stays as in the schematic; the label is separate silk text
            r.SetLayer(pcbnew.F_Fab)                            # the label replaces the reference on the silk (no overlap)
    edge = pcbnew.PCB_SHAPE(board); edge.SetShape(pcbnew.SHAPE_T_RECT)
    edge.SetStart(mm(0, 0)); edge.SetEnd(mm(W, H)); edge.SetLayer(pcbnew.Edge_Cuts); edge.SetWidth(pcbnew.FromMM(0.1))
    board.Add(edge)
    tb = board.GetTitleBlock()
    tb.SetTitle('ETZ plotter control - TEST BOARD'); tb.SetRevision('T1'); tb.SetDate('2026-11-09'); tb.SetCompany('VsOSh ETZ 2026-27')
    set_rules(board)
    return board, netinfo

def fix_value_text(board):
    """move connector labels next to the part, outside its pads (simple rule: above for bottom-edge plugs, below for top)"""
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref not in LABELS:
            continue
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else fp.GetBoundingBox(False)
        cx = toMM(bb.Centre().x)
        v = silk_text(board, LABELS[ref], 0, 0, 1.0)
        y = toMM(bb.GetY()) - 0.9 if toMM(bb.GetBottom()) > H - 10 else toMM(bb.GetBottom()) + 0.9
        if ref.startswith('U') and ref != 'U1':
            y = toMM(bb.Centre().y)
        if ref == 'U1':
            y = toMM(bb.Centre().y)
        if ref in ('J10', 'J11'):                              # above: C13 sits below the XT60, and the two labels would touch
            y = toMM(bb.GetY()) - 0.9
        v.SetPosition(mm(cx, y))

# =============================================================================
# 4. GROUND: a via next to every SMD ground pad (the shortest way into the planes)
# =============================================================================
def pad_box(p, grow):
    bb = p.GetBoundingBox()
    return (toMM(bb.GetX()) - grow, toMM(bb.GetY()) - grow, toMM(bb.GetRight()) + grow, toMM(bb.GetBottom()) + grow)

def escape_vias(board):
    """returns [(via, track)] (no net yet: ground stays out of the router; nets are set after routing)"""
    pads = list(board.GetPads())
    holes = [(toMM(f.GetPosition().x), toMM(f.GetPosition().y)) for f in board.GetFootprints() if f.GetReference().startswith('H')]
    made = []
    R = 0.3 + 0.25                                              # via radius + clearance
    for p in pads:
        if p.GetNetname().lstrip('/') != 'GND' or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            continue
        cx, cy = toMM(p.GetPosition().x), toMM(p.GetPosition().y)
        fx, fy = toMM(p.GetParentFootprint().GetPosition().x), toMM(p.GetParentFootprint().GetPosition().y)
        ox, oy = cx - fx, cy - fy
        base = math.atan2(oy, ox) if abs(ox) + abs(oy) > 0.1 else 0.0
        x0, y0, x1, y1 = pad_box(p, 0)
        half = max(x1 - x0, y1 - y0) / 2
        best = None
        for dist in (half + 0.75, half + 1.2, half + 1.8):
            for k in (0, 1, -1, 2, -2, 3, -3, 4):
                a = base + k * math.pi / 4
                vx, vy = cx + dist * math.cos(a), cy + dist * math.sin(a)
                if not (1.5 < vx < W - 1.5 and 1.5 < vy < H - 1.5):
                    continue
                if any(math.hypot(vx - hx, vy - hy) < 4.5 for hx, hy in holes):
                    continue
                ok = True
                for q in pads:
                    if q is p:
                        continue
                    a0, b0, a1, b1 = pad_box(q, R)
                    if a0 < vx < a1 and b0 < vy < b1:
                        ok = False; break
                    if q.GetNetname().lstrip('/') != 'GND' and seg_hits_box((cx, cy), (vx, vy), pad_box(q, 0.25 + 0.25)):
                        ok = False; break
                if ok and all(math.hypot(vx - mx, vy - my) > 1.2 for _, _, mx, my, _, _ in made):
                    best = (vx, vy); break
            if best:
                break
        if not best:
            print('  no room for a ground via at', p.GetParentFootprint().GetReference(), p.GetNumber())
            continue
        v = pcbnew.PCB_VIA(board); v.SetPosition(mm(*best)); v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3))
        v.SetNet(p.GetNet()); board.Add(v)
        t = pcbnew.PCB_TRACK(board); t.SetStart(mm(cx, cy)); t.SetEnd(mm(*best)); t.SetWidth(pcbnew.FromMM(0.5))
        t.SetLayer(pcbnew.F_Cu); t.SetNet(p.GetNet()); board.Add(t)
        made.append((v, t, best[0], best[1], cx, cy))
    return made

def seg_hits_box(a, b, box):
    x0, y0, x1, y1 = box
    for s in range(11):
        x, y = a[0] + (b[0] - a[0]) * s / 10, a[1] + (b[1] - a[1]) * s / 10
        if x0 < x < x1 and y0 < y < y1:
            return True
    return False

# =============================================================================
# 5. ROUTING: Freerouting, power first then signals
# =============================================================================
def freeroute(board, tag):
    dsn, ses = OUT[:-10] + '_%s.dsn' % tag, OUT[:-10] + '_%s.ses' % tag
    if os.path.exists(ses):
        os.remove(ses)
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise RuntimeError('DSN export failed')
    r = subprocess.run([JAVA, '-jar', FREEROUTING, '-de', dsn, '-do', ses, '-mp', str(PASSES), '--gui.enabled=false'],
                       capture_output=True, text=True, timeout=5400)
    open(OUT[:-10] + '_freerouting_%s.log' % tag, 'w').write(r.stdout + r.stderr)
    if not os.path.exists(ses):
        raise RuntimeError('Freerouting made no SES file (see the log)')
    if not pcbnew.ImportSpecctraSES(board, ses):
        raise RuntimeError('SES import failed')
    os.remove(dsn); os.remove(ses)

def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    u = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - u * dx, py - ay - u * dy)

def route(board, netinfo, ground):
    saved = [(p, p.GetNetname().lstrip('/')) for p in board.GetPads()]
    for v, t, *_ in ground:                         # ground escape vias: fixed obstacles for the router
        v.SetLocked(True); t.SetLocked(True)
    for p, n in saved:                              # pass 1: only the power nets exist
        if n not in POWER_FIRST:
            p.SetNetCode(0)
    freeroute(board, 'power')
    for t in board.GetTracks():
        t.SetLocked(True)
    for p, n in saved:                              # pass 2: signals around the fixed power tracks (ground still out)
        if n and n != 'GND':
            p.SetNet(netinfo[n])
    freeroute(board, 'signal')
    for p, n in saved:                              # ground back on its pads
        if n == 'GND':
            p.SetNet(netinfo['GND'])
    for t in board.GetTracks():
        t.SetLocked(False)
    # ground vias: the netless ones may not survive the SES round trip; put back the missing ones that still fit
    have = [(toMM(t.GetPosition().x), toMM(t.GetPosition().y)) for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    segs = [(t.GetNetname().lstrip('/'), toMM(t.GetStart().x), toMM(t.GetStart().y), toMM(t.GetEnd().x), toMM(t.GetEnd().y), toMM(t.GetWidth()) / 2)
            for t in board.GetTracks() if t.Type() != pcbnew.PCB_VIA_T]
    kept = back = lost = 0
    for v, t, vx, vy, sx, sy in ground:
        if any(math.hypot(vx - a, vy - b) < 0.05 for a, b in have):
            kept += 1
            for it in board.GetTracks():
                if it.Type() == pcbnew.PCB_VIA_T and math.hypot(toMM(it.GetPosition().x) - vx, toMM(it.GetPosition().y) - vy) < 0.05:
                    it.SetNet(netinfo['GND'])
                elif it.Type() != pcbnew.PCB_VIA_T and not it.GetNetname().lstrip('/') and math.hypot(toMM(it.GetEnd().x) - vx, toMM(it.GetEnd().y) - vy) < 0.05:
                    it.SetNet(netinfo['GND'])
            continue
        clash = False
        for n, ax, ay, bx, by, hw in segs:
            if n == 'GND':
                continue
            if seg_dist(vx, vy, ax, ay, bx, by) < 0.3 + hw + 0.25:
                clash = True; break
            # the short via track: check both of its ends against the routed track
            if min(seg_dist(sx + (vx - sx) * k / 4, sy + (vy - sy) * k / 4, ax, ay, bx, by) for k in range(1, 5)) < 0.25 + hw + 0.25:
                clash = True; break
        if clash:
            lost += 1; continue
        nv = pcbnew.PCB_VIA(board); nv.SetPosition(mm(vx, vy)); nv.SetWidth(pcbnew.FromMM(0.6)); nv.SetDrill(pcbnew.FromMM(0.3))
        nv.SetNet(netinfo['GND']); board.Add(nv)
        nt = pcbnew.PCB_TRACK(board); nt.SetStart(mm(sx, sy)); nt.SetEnd(mm(vx, vy)); nt.SetWidth(pcbnew.FromMM(0.5))
        nt.SetLayer(pcbnew.F_Cu); nt.SetNet(netinfo['GND']); board.Add(nt)
        back += 1
    print('ground vias: kept %d, put back %d, no room %d (those pads reach GND through the top pour)' % (kept, back, lost))

def pours(board, netinfo):
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer); z.SetNet(netinfo['GND']); z.SetZoneName('GND ' + ('top' if layer == pcbnew.F_Cu else 'bottom'))
        z.SetLocalClearance(pcbnew.FromMM(0.3)); z.SetMinThickness(pcbnew.FromMM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(pcbnew.FromMM(0.4)); z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.6))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline(); ol.NewOutline()
        for x, y in ((0.3, 0.3), (W - 0.3, 0.3), (W - 0.3, H - 0.3), (0.3, H - 0.3)):
            ol.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())

def stitch(board, netinfo, pitch=6.0):
    """GND vias on a grid wherever both pours are solid around the point (ties the two planes together)"""
    zf = [z for z in board.Zones() if z.GetLayer() == pcbnew.F_Cu][0].GetFilledPolysList(pcbnew.F_Cu)
    zb = [z for z in board.Zones() if z.GetLayer() == pcbnew.B_Cu][0].GetFilledPolysList(pcbnew.B_Cu)
    vias = [(toMM(t.GetPosition().x), toMM(t.GetPosition().y)) for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
    n = 0
    y = pitch / 2
    while y < H:
        x = pitch / 2
        while x < W:
            if all(zf.Contains(mm(x + dx, y + dy)) and zb.Contains(mm(x + dx, y + dy))
                   for dx, dy in ((0, 0), (0.75, 0), (-0.75, 0), (0, 0.75), (0, -0.75))) \
                    and all(math.hypot(x - a, y - b) > 1.2 for a, b in vias):
                v = pcbnew.PCB_VIA(board); v.SetPosition(mm(x, y)); v.SetNet(netinfo['GND'])
                v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3)); board.Add(v); n += 1
            x += pitch
        y += pitch
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    return n

def free_spot(board, w, h, cands):
    """first candidate centre where a w x h box touches no track, via or pad"""
    items = [t.GetBoundingBox() for t in board.GetTracks()] + [p.GetBoundingBox() for p in board.GetPads()]
    boxes = [(toMM(b.GetX()) - 0.4, toMM(b.GetY()) - 0.4, toMM(b.GetRight()) + 0.4, toMM(b.GetBottom()) + 0.4) for b in items]
    for cx, cy in cands:
        a0, b0, a1, b1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
        if not any(a0 < x1 and x0 < a1 and b0 < y1 and y0 < b1 for x0, y0, x1, y1 in boxes):
            return cx, cy
    return None

def teardrops(board):
    n = 0
    for p in board.GetPads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            try:
                p.GetTeardropParams().m_Enabled = True; n += 1
            except Exception as e:
                return 'not available (%s)' % e
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            t.GetTeardropParams().m_Enabled = True
    return n

if __name__ == '__main__':
    board, netinfo = build()
    fix_value_text(board)
    print('placed %d footprints, %d nets, board %g x %g mm' % (len(board.GetFootprints()), len(netinfo), W, H))
    ground = escape_vias(board)
    print('ground vias next to SMD pads:', len(ground))
    if '--place-only' in sys.argv:
        for v, t, *_ in ground:
            v.SetNet(netinfo['GND']); t.SetNet(netinfo['GND'])
        pcbnew.SaveBoard(OUT, board)
        sys.exit(0)
    route(board, netinfo, ground)
    print('tracks + vias after routing:', len(board.GetTracks()))
    pours(board, netinfo)
    print('stitching vias:', stitch(board, netinfo))
    print('teardrops:', teardrops(board))
    # revision text in copper (shows up on the bare board even if the silkscreen is wrong) + silkscreen title
    spot = free_spot(board, 34, 2.4, [(x, y) for y in (64, 60, 68, 56, 72, 52) for x in (85, 90, 80, 95, 75)])
    if spot:
        silk_text(board, 'ETZ CONTROL TEST T1 2026-11', spot[0], spot[1], 1.5, pcbnew.F_Cu)
        silk_text(board, 'ETZ CONTROL TEST T1 2026-11', spot[0], spot[1] + 4, 1.5, pcbnew.B_Cu, mirror=True)
    silk_text(board, 'ETZ plotter control  TEST T1  2-layer  9 Nov 2026', 90, 50.5, 1.2)
    for ref, plus, minus in (('J10', '+', '-'), ('J11', '+', '-')):
        fp = board.FindFootprintByReference(ref)
        for p in fp.Pads():
            if p.GetNumber() in ('1', '2'):
                silk_text(board, plus if p.GetNumber() == '2' else minus, toMM(p.GetPosition().x) - 3.2, toMM(p.GetPosition().y), 1.6)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(OUT, board)
    b2 = pcbnew.LoadBoard(OUT); set_rules(b2); pcbnew.ZONE_FILLER(b2).Fill(b2.Zones()); pcbnew.SaveBoard(OUT, b2)
    # DRC pass: a GND pin where passing tracks leave fewer than 2 thermal spokes gets a solid connection instead
    rep = os.path.join(HERE, 'drc.json')
    subprocess.run([CLI, 'pcb', 'drc', '--format', 'json', '-o', rep, OUT], capture_output=True)
    starved = set()
    for v in json.load(open(rep))['violations']:
        if v['type'] == 'starved_thermal':
            for it in v['items']:
                if 'pad' in it['description']:
                    d = it['description'].split()
                    starved.add((d[-1], d[d.index('pad') + 1]))
    if starved:
        b3 = pcbnew.LoadBoard(OUT)
        for ref, num in starved:
            for p in b3.FindFootprintByReference(ref).Pads():
                if p.GetNumber() == num:
                    p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        pcbnew.ZONE_FILLER(b3).Fill(b3.Zones()); pcbnew.SaveBoard(OUT, b3)
        print('solid GND connection (spokes were blocked):', ' '.join('%s.%s' % s for s in sorted(starved)))
    print('saved', OUT)
