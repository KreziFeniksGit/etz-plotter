"""
ETZ plotter control board: full connection schematic -> pcb/etz_control.kicad_sch  (KiCad 10)
=============================================================================================
Same parts and nets as build_pcb.py (one source: the P table there, from wiring.md). Every pin gets a net label;
equal labels = connected. Plug-in modules (ESP32-S3-DevKitC-1, TMC2209, Mini560 Pro, BSS138 shifter) get their own
symbol + footprint in the project library `etz` (etz.kicad_sym, etz.pretty); the rest are KiCad library parts.
Run with KiCad's Python:  "C:\\Program Files\\KiCad\\10.0\\bin\\python.exe" pcb\\build_sch.py
It then exports the netlist with kicad-cli and checks every net against build_pcb.P (must be identical), runs ERC,
and writes etz_control_schematic.pdf.
"""
import os, sys, uuid, json, subprocess, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.argv = [sys.argv[0], '--no-route']
import build_pcb as B

KICAD = os.path.dirname(os.path.dirname(sys.executable))
SYMDIR = os.path.join(KICAD, 'share', 'kicad', 'symbols')
CLI = os.path.join(KICAD, 'bin', 'kicad-cli.exe')
SCH = os.path.join(HERE, 'etz_control.kicad_sch')
G = 2.54

# =============================================================================
# 1. tiny s-expression reader / writer (for copying KiCad library symbols)
# =============================================================================
class Q(str):
    """a quoted string token"""

def parse(text):
    tok = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+')
    stack, cur = [], []
    for m in tok.finditer(text):
        t = m.group(0)
        if t == '(':
            stack.append(cur); cur = []
        elif t == ')':
            done = cur; cur = stack.pop(); cur.append(done)
        elif t[0] == '"':
            cur.append(Q(t[1:-1].replace('\\"', '"').replace('\\\\', '\\')))
        else:
            cur.append(t)
    return cur[0]

def dump(x, ind=0):
    if isinstance(x, list):
        inner = [dump(e, ind + 1) for e in x]
        if sum(len(s) for s in inner) < 90 and not any('\n' in s for s in inner):
            return '(' + ' '.join(inner) + ')'
        return '(' + inner[0] + ''.join('\n' + '\t' * (ind + 1) + s for s in inner[1:]) + ')'
    if isinstance(x, Q):
        return '"' + x.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return str(x)

_LIBS = {}
def lib_symbol(lib, name):
    if lib not in _LIBS:
        _LIBS[lib] = parse(open(os.path.join(SYMDIR, lib + '.kicad_sym'), encoding='utf8').read())
    for e in _LIBS[lib]:
        if isinstance(e, list) and e[0] == 'symbol' and e[1] == name:
            if any(isinstance(k, list) and k[0] == 'extends' for k in e):
                raise RuntimeError('%s:%s extends another symbol' % (lib, name))
            s = [x for x in e]
            s[1] = Q('%s:%s' % (lib, name))
            return s
    raise RuntimeError('symbol not found %s:%s' % (lib, name))

def pins_of(sym):
    """{number: (x, y, angle)} - x, y = the connection point in symbol coordinates (y up)"""
    out = {}
    def walk(e):
        for k in e:
            if isinstance(k, list):
                if k[0] == 'pin':
                    at = next(a for a in k if isinstance(a, list) and a[0] == 'at')
                    num = next(a for a in k if isinstance(a, list) and a[0] == 'number')[1]
                    out[str(num)] = (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0)
                else:
                    walk(k)
    walk(sym)
    return out

# =============================================================================
# 2. module symbols + footprints (project library 'etz')
# =============================================================================
MODULES = {   # name: (left pin names, right pin names, footprint geometry)
    'ESP32-S3-DevKitC-1': (B.J1, B.J3, dict(rows=B.ESP_ROW, body=(25.5, 62.7))),
    'TMC2209_Module': (['EN', 'MS1', 'MS2', 'PDN_UART', 'UART', 'CLK', 'STEP', 'DIR'],
                       ['VM', 'GND', '2B', '2A', '1A', '1B', 'VIO', 'GND'], dict(rows=B.TMC_ROW, body=(15.3, 20.3))),
    'BSS138_LevelShifter_4ch': (['LV1', 'LV2', 'LV', 'GND', 'LV3', 'LV4'], ['HV1', 'HV2', 'HV', 'GND', 'HV3', 'HV4'],
                                dict(rows=B.LS_ROW, body=(16.0, 16.5))),
    'Mini560_Pro': (['IN+', 'IN-'], ['OUT+', 'OUT-'], dict(rows=B.MINI560_PITCH, body=(29.0, 18.0))),
}

def module_symbol(name):
    L, R, _ = MODULES[name]
    n = max(len(L), len(R))
    w = max(12, max(len(s) for s in L + R) * 2) * 1.27 * 2
    w = round(w / G) * G
    top = (n - 1) / 2 * G
    body = [Q('rectangle'), ['start', -w / 2, top + G], ['end', w / 2, -top - G],
            ['stroke', ['width', 0.254], ['type', 'default']], ['fill', ['type', 'background']]]
    body[0] = 'rectangle'
    pins = []
    for side, names, x, ang, off in (('L', L, -w / 2 - G, 0, 0), ('R', R, w / 2 + G, 180, len(L))):
        for i, nm in enumerate(names):
            pins.append(['pin', 'passive', 'line', ['at', round(x, 3), round(top - i * G, 3), ang], ['length', G],
                         ['name', Q(nm), ['effects', ['font', ['size', 1.27, 1.27]]]],
                         ['number', Q(str(off + i + 1)), ['effects', ['font', ['size', 1.27, 1.27]]]]])
    prop = lambda k, v, y, hide=False: ['property', Q(k), Q(v), ['at', 0, y, 0],
                                         ['effects', ['font', ['size', 1.27, 1.27]]] + ([['hide', 'yes']] if hide else [])]
    return ['symbol', Q('etz:' + name), ['pin_names', ['offset', 1.016]], ['exclude_from_sim', 'no'], ['in_bom', 'yes'],
            ['on_board', 'yes'], prop('Reference', 'U', top + 2 * G), prop('Value', name, -top - 2 * G),
            prop('Footprint', 'etz:' + name, 0, True), prop('Datasheet', '', 0, True), prop('Description', '', 0, True),
            ['symbol', Q(name + '_0_1'), body], ['symbol', Q(name + '_1_1')] + pins]

def module_footprint(name):
    """two rows of 2.54 mm through-hole pads (female header sockets), rows 'rows' apart; body outline on silk"""
    L, R, g = MODULES[name]
    rows, (bw, bl) = g['rows'], g['body']
    lines = ['(footprint "%s"' % name, '\t(version 20241229)', '\t(generator "etz_build_sch")', '\t(layer "F.Cu")',
             '\t(descr "%s plug-in module on female headers. VERIFY pin rows %.2f mm and pin order on the real module")' % (name, rows),
             '\t(property "Reference" "REF**" (at %.2f -3 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))' % (rows / 2),
             '\t(property "Value" "%s" (at %.2f %.2f 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))' % (name, rows / 2, (max(len(L), len(R)) - 1) * G + 3)]
    if name == 'Mini560_Pro':     # IN pads at one end, OUT pads at the other, 2 pads each, across the module
        pos = [(0, 0), (0, G), (rows, 0), (rows, G)]
    else:
        pos = [(0, i * G) for i in range(len(L))] + [(rows, i * G) for i in range(len(R))]
    for i, (x, y) in enumerate(pos):
        shape = 'rect' if i == 0 else 'circle'
        lines.append('\t(pad "%d" thru_hole %s (at %.3f %.3f) (size 1.7 1.7) (drill 1) (layers "*.Cu" "*.Mask"))' % (i + 1, shape, x, y))
    ymax = max(p[1] for p in pos)
    cx, cy = rows / 2, ymax / 2
    x0, x1, y0, y1 = cx - bw / 2, cx + bw / 2, cy - bl / 2, cy + bl / 2
    for (a, b) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        lines.append('\t(fp_line (start %.2f %.2f) (end %.2f %.2f) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))' % (a + b))
        lines.append('\t(fp_line (start %.2f %.2f) (end %.2f %.2f) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))' %
                     (a[0] + (0.5 if a[0] > cx else -0.5), a[1] + (0.5 if a[1] > cy else -0.5), b[0] + (0.5 if b[0] > cx else -0.5), b[1] + (0.5 if b[1] > cy else -0.5)))
    lines.append(')')
    return '\n'.join(lines) + '\n'

# =============================================================================
# 3. the parts (merged from build_pcb.P: module sockets A/B -> one module)
# =============================================================================
STD = {   # build_pcb footprint key -> (lib, symbol)
    'res': ('Device', 'R'), 'c0805': ('Device', 'C'), 'cp63': ('Device', 'C_Polarized'), 'cp8': ('Device', 'C_Polarized'),
    'sma': ('Device', 'D_Schottky'), 'sot23': ('Transistor_FET', 'Q_NMOS_GSD'), 'to220': ('Transistor_FET', 'Q_NMOS_GDS'),
    'f1206': ('Device', 'Polyfuse'),
    'xt60': ('Connector_Generic', 'Conn_01x02'), 'xt30': ('Connector_Generic', 'Conn_01x02'),
    'xh2': ('Connector_Generic', 'Conn_01x02'), 'pins3': ('Connector_Generic', 'Conn_01x03'),
    'xh4': ('Connector_Generic', 'Conn_01x04'), 'xh5': ('Connector_Generic', 'Conn_01x05'),
    'idc10': ('Connector_Generic', 'Conn_02x05_Odd_Even'), 'tp': ('Connector', 'TestPoint'), 'hole': ('Mechanical', 'MountingHole'),
}
FPKEY = {v: k for k, v in B.F.items()}

def merged_parts():
    """ref -> (lib_id, value, footprint, {pin number str: net})"""
    out = {}
    mod = {'U1': ('ESP32-S3-DevKitC-1', 22, 'ESP32-S3-DevKitC-1 N16R8'), 'U2': ('TMC2209_Module', 8, 'TMC2209 X'),
           'U3': ('TMC2209_Module', 8, 'TMC2209 Y'), 'U4': ('TMC2209_Module', 8, 'TMC2209 wrist'), 'U7': ('TMC2209_Module', 8, 'TMC2209 spare'),
           'U5': ('Mini560_Pro', 2, 'Mini560 Pro 5V (logic)'), 'U6': ('Mini560_Pro', 2, 'Mini560 Pro 5V (servo)'),
           'U8': ('BSS138_LevelShifter_4ch', 6, 'BSS138 level shifter')}
    for ref, (fpid, value, x, y, rot, pads) in B.P.items():
        if ref[:-1] in mod and ref[-1] in 'AB':
            r = ref[:-1]
            name, nleft, val = mod[r]
            d = out.setdefault(r, ('etz:' + name, val, 'etz:' + name, {}))[3]
            for k, n in pads.items():
                d[str(k + (nleft if ref[-1] == 'B' else 0))] = n
        else:
            lib, sym = STD[FPKEY[fpid]]
            out[ref] = ('%s:%s' % (lib, sym), value, fpid, {str(k): n for k, n in pads.items()})
    return out

GROUPS = [   # (title, refs) - laid out left to right, row by row
    ('POWER IN: battery (fused, unswitched) and drive bus (after stop block 1)', ['J10', 'J11', 'U5', 'U6', 'D1', 'C7', 'F2', 'C5', 'C6', 'TP1', 'TP2', 'TP3', 'TP4']),
    ('CONTROLLER: ESP32-S3-DevKitC-1 (radio never started)', ['U1']),
    ('STEPPER DRIVERS: TMC2209, UART addresses 0..3 (MS1/MS2), bulk caps, motor plugs', ['U2', 'U3', 'U4', 'U7', 'C1', 'C2', 'C3', 'C4', 'J1', 'J2', 'J3', 'J4', 'R8', 'R10']),
    ('MAGNET (switched by stop block 2 + MOSFET), SERVO, SENSORS, HOME SWITCHES', ['J12', 'J6', 'Q1', 'D2', 'R14', 'R15', 'J5', 'R9', 'J9', 'R11', 'R12', 'R13', 'J7', 'J8']),
    ('PANEL: connectors A / B / C (rules), LEDs, start, stop sense, battery sense', ['J17', 'U8', 'R5', 'R6', 'R7', 'C8', 'J14', 'J15', 'J16', 'R16', 'R17', 'R1', 'R2', 'R3', 'R4']),
    ('MOUNTING', ['H1', 'H2', 'H3', 'H4']),
]
CONN_NAMES = {'J10': 'XT60 BAT (1 -, 2 +)', 'J11': 'XT30 DRIVE (1 +, 2 -)'}

# =============================================================================
# 4. write the schematic
# =============================================================================
def U():
    return Q(str(uuid.uuid4()))

def build():
    parts = merged_parts()
    libsyms, pinmap = {}, {}
    for ref, (lid, val, fp, nets) in parts.items():
        if lid not in libsyms:
            lib, name = lid.split(':')
            libsyms[lid] = module_symbol(name) if lib == 'etz' else lib_symbol(lib, name)
            pinmap[lid] = pins_of(libsyms[lid])
    root = str(uuid.uuid4())
    items = []
    PAGE_W, MARGIN = 570.0, 20.0
    y = 22.0
    for title, refs in GROUPS:
        items.append(['text', Q(title), ['exclude_from_sim', 'no'], ['at', MARGIN, y, 0],
                      ['effects', ['font', ['size', 2.54, 2.54], ['thickness', 0.5], ['bold', 'yes']], ['justify', 'left', 'bottom']], ['uuid', U()]])
        y += 8.0
        x, rowh = MARGIN, 0.0
        for ref in refs:
            lid, val, fp, nets = parts[ref]
            pins = pinmap[lid]
            xs = [p[0] for p in pins.values()] or [0]
            ys = [p[1] for p in pins.values()] or [0]
            lab = max([len(n) for n in nets.values()] + [4]) * 1.3 + 4
            left = -min(xs) + (lab if any(p[2] == 0 for p in pins.values()) else 6)
            right = max(xs) + (lab if any(p[2] == 180 for p in pins.values()) else 12)
            up = max(ys) + (lab if any(p[2] == 270 for p in pins.values()) else 6)
            down = -min(ys) + (lab if any(p[2] == 90 for p in pins.values()) else 8)
            if x + left + right > PAGE_W - MARGIN:
                x, y, rowh = MARGIN, y + rowh + 4.0, 0.0
            X = round((x + left) / G) * G
            Y = round((y + up) / G) * G
            rowh = max(rowh, up + down)
            x = X + right + 3.0
            sym = ['symbol', ['lib_id', Q(lid)], ['at', X, Y, 0], ['unit', 1], ['exclude_from_sim', 'no'], ['in_bom', 'yes'],
                   ['on_board', 'yes'], ['dnp', 'no'], ['uuid', U()],
                   ['property', Q('Reference'), Q(ref), ['at', X, Y - up + 3.0, 0], ['effects', ['font', ['size', 1.27, 1.27]]]],
                   ['property', Q('Value'), Q(CONN_NAMES.get(ref, val)), ['at', X, Y + down - 2.0, 0], ['effects', ['font', ['size', 1.27, 1.27]]]],
                   ['property', Q('Footprint'), Q(fp), ['at', X, Y, 0], ['effects', ['font', ['size', 1.27, 1.27]], ['hide', 'yes']]],
                   ['property', Q('Datasheet'), Q(''), ['at', X, Y, 0], ['effects', ['font', ['size', 1.27, 1.27]], ['hide', 'yes']]]]
            for num in sorted(pins, key=lambda s: (len(s), s)):
                sym.append(['pin', Q(num), ['uuid', U()]])
            sym.append(['instances', ['project', Q('etz_control'), ['path', Q('/' + root), ['reference', Q(ref)], ['unit', 1]]]])
            items.append(sym)
            for num, (px, py, ang) in pins.items():
                sx, sy = round(X + px, 3), round(Y - py, 3)
                n = nets.get(num)
                if n:
                    la = {0: 180, 180: 0, 90: 270, 270: 90}[int(ang) % 360]
                    just = ['justify', 'right' if la in (180, 270) else 'left', 'bottom']
                    items.append(['label', Q(n), ['at', sx, sy, la], ['fields_autoplaced', 'yes'],
                                  ['effects', ['font', ['size', 1.27, 1.27]], just], ['uuid', U()]])
                elif lid != 'Mechanical:MountingHole':
                    items.append(['no_connect', ['at', sx, sy], ['uuid', U()]])
        y += rowh + 8.0
    paper = 'A2' if y < 400 else 'A1'
    print('content height %.0f mm -> %s' % (y, paper))
    doc = ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')], ['generator_version', Q('10.0')], ['uuid', Q(root)],
           ['paper', Q(paper)],
           ['title_block', ['title', Q('ETZ plotter control board - full connection schematic')], ['date', Q('2026-10-22')],
            ['rev', Q('1.0')], ['company', Q('VsOSh ETZ 2026-27')],
            ['comment', 1, Q('Nets from wiring.md (same as pcb/build_pcb.py). Equal labels = connected.')],
            ['comment', 2, Q('Module pinouts VERIFY on the real parts')]],
           ['lib_symbols'] + list(libsyms.values())] + items + [['sheet_instances', ['path', Q('/'), ['page', Q('1')]]]]
    open(SCH, 'w', encoding='utf8', newline='\n').write(dump(doc) + '\n')
    # project library: symbols + footprints, and the library tables
    lib = ['kicad_symbol_lib', ['version', 20241209], ['generator', Q('etz_build_sch')], ['generator_version', Q('10.0')]]
    for name in MODULES:
        s = module_symbol(name); s[1] = Q(name); lib.append(s)
    open(os.path.join(HERE, 'etz.kicad_sym'), 'w', encoding='utf8', newline='\n').write(dump(lib) + '\n')
    os.makedirs(os.path.join(HERE, 'etz.pretty'), exist_ok=True)
    for name in MODULES:
        open(os.path.join(HERE, 'etz.pretty', name + '.kicad_mod'), 'w', encoding='utf8', newline='\n').write(module_footprint(name))
    open(os.path.join(HERE, 'sym-lib-table'), 'w', newline='\n').write(
        '(sym_lib_table\n\t(version 7)\n\t(lib (name "etz")(type "KiCad")(uri "${KIPRJMOD}/etz.kicad_sym")(options "")(descr "ETZ plug-in modules"))\n)\n')
    open(os.path.join(HERE, 'fp-lib-table'), 'w', newline='\n').write(
        '(fp_lib_table\n\t(version 7)\n\t(lib (name "etz")(type "KiCad")(uri "${KIPRJMOD}/etz.pretty")(options "")(descr "ETZ plug-in modules"))\n)\n')
    return parts

# =============================================================================
# 5. checks: netlist == build_pcb nets, ERC, PDF
# =============================================================================
def check(parts):
    net_xml = os.path.join(HERE, 'etz_control_sch.net')
    subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', net_xml, SCH], capture_output=True)
    nl = parse(open(net_xml, encoding='utf8').read())
    got = {}
    for e in nl:
        if isinstance(e, list) and e[0] == 'nets':
            for n in e[1:]:
                name = next(a[1] for a in n if isinstance(a, list) and a[0] == 'name')
                nodes = {(next(b[1] for b in a if isinstance(b, list) and b[0] == 'ref'), next(b[1] for b in a if isinstance(b, list) and b[0] == 'pin'))
                         for a in n if isinstance(a, list) and a[0] == 'node'}
                if len(nodes) and not name.startswith('unconnected-'):
                    got[name.lstrip('/')] = nodes
    want = {}
    for ref, (lid, val, fp, nets) in parts.items():
        for pin, n in nets.items():
            want.setdefault(n, set()).add((ref, pin))
    bad = {n: {'schematic': sorted(got.get(n, [])), 'expected': sorted(want.get(n, []))}
           for n in set(want) | set(got) if got.get(n) != want.get(n)}
    os.remove(net_xml)
    erc = os.path.join(HERE, 'erc.json')
    subprocess.run([CLI, 'sch', 'erc', '--format', 'json', '-o', erc, SCH], capture_output=True)
    e = json.load(open(erc))
    viol = [v for s in e.get('sheets', []) for v in s.get('violations', [])]
    subprocess.run([CLI, 'sch', 'export', 'pdf', '-o', os.path.join(HERE, 'etz_control_schematic.pdf'), SCH], capture_output=True)
    return bad, viol

if __name__ == '__main__':
    parts = build()
    bad, viol = check(parts)
    print('parts', len(parts), 'nets', len({n for p in parts.values() for n in p[3].values()}))
    print('netlist vs build_pcb:', 'IDENTICAL' if not bad else json.dumps(bad, indent=1)[:3000])
    from collections import Counter
    print('ERC:', len(viol), dict(Counter(v['type'] for v in viol)))
    for v in viol[:15]:
        print('  ', v['type'], '|', v['description'], '|', [i['description'] for i in v.get('items', [])][:2])
