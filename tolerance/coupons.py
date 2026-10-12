"""
ETZ plotter v2: tolerance test coupons (FreeCAD Part script)
============================================================
Print these BEFORE the real parts, with the same printer, filament (PETG), nozzle and slicer settings.
Every coupon tests one tolerance constant from wrist/wrist_module.py (section 1) and frame/frame.py.
The middle variant of each row is the value the model uses now; the others are one step tighter and looser.
Pick the variant that fits as the guide (tolerance/README.md) describes, then change the constant: every part follows.

Run with FreeCAD's python:  ../fcpy coupons.py   -> out/*.step, out/coupon_dfm.json  (STEP only)
Coupons lie in print orientation (flat on z = 0).
"""
import json, math, os, sys, struct
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'wrist'), os.path.join(HERE, '..', 'frame'), os.path.join(HERE, '..')]
import FreeCAD as App
import Part
import wrist_module as W
from wrist_module import box, cyl, rbox, slot, fillet_all, cut_all, tidy, TOL_BOLT, TOL_PRESS, TOL_MOTOR, TOL_MOVE, INSERT_D

V = App.Vector
FONT = next((f for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 'C:/Windows/Fonts/arialbd.ttf',
                         'C:/Windows/Fonts/segoeuib.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf') if os.path.exists(f)), None)
# engraved labels need a bold TTF; set FONT to any .ttf on your computer if none of these exist
ENGRAVE = 0.6

# variants: (current - step, current, current + step)
def trio(cur, step):
    return [round(cur - step, 3), round(cur, 3), round(cur + step, 3)]

BOLT_T = trio(TOL_BOLT, 0.10)          # 0.15 0.25 0.35
PRESS_T = trio(TOL_PRESS, 0.06)        # 0.06 0.12 0.18
MOTOR_T = trio(TOL_MOTOR, 0.10)        # 0.10 0.20 0.30
MOVE_T = trio(TOL_MOVE, 0.10)          # 0.30 0.40 0.50
INSERT_T = [3.8, 3.9, 4.0, 4.1]        # Ruthex says 4.0
SOCKET_T = trio(W.SOCKET_GAP, 0.1)     # per-side gap of the 2020 post socket (model: 0.2, inner 20.4)
PILOT_T = trio(W.M2_PILOT, 0.2)        # M2 self-tapping pilot (model: 1.8)

def text_solid(t, size):
    faces = []
    for ch in Part.makeWireString(t, FONT, size, 0):
        try:
            faces.append(Part.Face(ch, 'Part::FaceMakerBullseye'))
        except Exception:
            pass                                       # spaces
    return Part.makeCompound(faces).extrude(V(0, 0, ENGRAVE + 1.0))

LABELS = True       # False while running the print-rule check (the engraved text is cosmetic)

def engrave_top(s, t, x, y, ztop, size=3.5, centre=True):
    if not LABELS:
        return s
    ts = text_solid(t, size)
    bb = ts.BoundBox
    dx = x - (bb.XMin + bb.XMax) / 2 if centre else x - bb.XMin
    dy = y - (bb.YMin + bb.YMax) / 2
    ts.translate(V(dx, dy, ztop - ENGRAVE))
    return s.cut(ts)

def engrave_front(s, t, x, z, yface, size=3.5):
    """Engrave text on a face at y = yface whose material lies at y > yface (reads from -y)."""
    if not LABELS:
        return s
    ts = text_solid(t, size)
    ts.rotate(V(0, 0, 0), V(1, 0, 0), 90)            # text plane x-z, extruded toward -y
    bb = ts.BoundBox
    ts.translate(V(x - (bb.XMin + bb.XMax) / 2, yface + ENGRAVE - bb.YMax, z - (bb.ZMin + bb.ZMax) / 2))
    return s.cut(ts)

def plate(w, h, t, r=3.0):
    p = box(0, 0, 0, w, h, t)
    p = p.makeFillet(r, [e for e in p.Edges if abs(e.Length - t) < 1e-6])
    return fillet_all(p, r_out=0.6)

def fmt(v):
    return ('%.2f' % v).lstrip('0') if v < 1 else ('%.1f' % v)

# =============================================================================
# A. clearance holes, printed vertical  -> TOL_BOLT
# =============================================================================
def coupon_A():
    ds = [5, 4, 3, 2.5, 2]
    w, h, t = 58.0, 73.0, 4.0
    s = plate(w, h, t)
    cut = []
    for i, d in enumerate(ds):
        for j, tol in enumerate(BOLT_T):
            cut.append(cyl((19.0 + 14.0 * j, 7.0 + 12.0 * i, -1), (d + tol) / 2, t + 2))
    s = cut_all(s, cut)
    lab = []
    for i, d in enumerate(ds):
        s = engrave_top(s, 'M%g' % d, 6.0, 7.0 + 12.0 * i, t, 3.2)
    for j, tol in enumerate(BOLT_T):
        s = engrave_top(s, '+' + fmt(tol), 19.0 + 14.0 * j, h - 6.0, t, 3.2)
    return s

# =============================================================================
# B. clearance holes, printed horizontal  -> TOL_BOLT (holes through vertical walls)
# =============================================================================
def coupon_B():
    ds = [3, 4, 5]
    pitch, t_wall, hgt = 11.5, 8.0, 15.0
    L = 9 * pitch + 6.0
    s = box(0, 0, 0, L, t_wall, hgt)
    s = fillet_all(s, r_out=0.6)
    cut = []
    for g, d in enumerate(ds):
        for j, tol in enumerate(BOLT_T):
            x = 3.0 + pitch * (3 * g + j) + pitch / 2
            cut.append(cyl((x, -1, 6.5), (d + tol) / 2, t_wall + 2, 'y'))
    s = cut_all(s, cut)
    for g, d in enumerate(ds):
        for j, tol in enumerate(BOLT_T):
            x = 3.0 + pitch * (3 * g + j) + pitch / 2
            s = engrave_top(s, fmt(tol), x, t_wall / 2, hgt, 3.0)
        s = engrave_front(s, 'M%g' % d, 3.0 + pitch * (3 * g + 1) + pitch / 2, 12.5, 0.0, 3.0)
    return s

# =============================================================================
# C. heat-set insert holes  -> INSERT_D
# =============================================================================
def coupon_C():
    n = len(INSERT_T)
    w, h, t = 13.0 * n + 4.0, 19.0, 9.0
    s = plate(w, h, t, 2.0)
    s = cut_all(s, [cyl((8.5 + 13.0 * i, 6.5, t + 0.01), d / 2, -W.INSERT_DEPTH) for i, d in enumerate(INSERT_T)])
    for i, d in enumerate(INSERT_T):
        s = engrave_top(s, '%.1f' % d, 8.5 + 13.0 * i, 14.5, t, 3.2)
    return s

# =============================================================================
# D1. press fit in a plate: 684ZZ seat  -> TOL_PRESS   (the hall sensor and its magnet were dropped, 12 Oct)
# =============================================================================
def coupon_D1():
    w, h, t = 56.0, 26.0, 8.0
    s = plate(w, h, t)
    cut = []
    for j, tol in enumerate(PRESS_T):
        x = 12.0 + 16.0 * j
        cut.append(cyl((x, 16.0, t + 0.01), (W.BRG_OD + tol) / 2, -W.BRG_W - 0.01))          # bearing seat, 4 deep
        cut.append(cyl((x, 16.0, -1), (W.SPACER_OD + 2 * W.SPACER_GAP) / 2, t + 2))             # shoulder hole as in the arms
    s = cut_all(s, cut)
    for j, tol in enumerate(PRESS_T):
        s = engrave_top(s, '+' + fmt(tol), 12.0 + 16.0 * j, 4.5, t, 3.0)
    return s

# =============================================================================
# D2. D-bore hubs on the NEMA11 shaft and post-cap pins for the 2020 centre hole  -> TOL_PRESS
# =============================================================================
def coupon_D2():
    w, h, t = 60.0, 44.0, 3.0
    s = plate(w, h, t)
    bodies = []
    for j, tol in enumerate(PRESS_T):
        x = 12.0 + 18.0 * j
        bodies.append(cyl((x, 30.0, t), 7.0, 10.0))                                             # hub, like wrist_hub
        bodies.append(cyl((x, 12.0, t), (4.2 - tol) / 2, 6.0))                                  # pin, like post_cap
    s = fillet_all(tidy(s.fuse(bodies)), r_out=0.4)
    cut = []
    for j, tol in enumerate(PRESS_T):
        x = 12.0 + 18.0 * j
        bore = cyl((x, 30.0, -1), (W.N11_SHAFT_D + tol) / 2, t + 12)
        flat = box(x + (W.N11_SHAFT_FLAT - W.N11_SHAFT_D / 2) + tol / 2, 26.0, -2, x + 4, 34.0, t + 13)
        cut.append(bore.cut(flat))
    s = cut_all(s, cut)
    for j, tol in enumerate(PRESS_T):
        s = engrave_top(s, fmt(tol), 12.0 + 18.0 * j + 8.5, 20.5, t, 2.6)
    return s

# =============================================================================
# E1 / E2. motor pilot and screw holes  -> TOL_MOTOR
# =============================================================================
def _motor_coupon(cell, pilot, pitch, hole):
    t = 3.0
    w, h = 3 * cell + 4.0, cell + 7.0
    s = plate(w, h, t)
    cut = []
    for j, tol in enumerate(MOTOR_T):
        cx, cy = 2.0 + cell * j + cell / 2, 7.0 + cell / 2
        cut.append(cyl((cx, cy, -1), (pilot + tol) / 2, t + 2))
        for a in (-1, 1):
            for b in (-1, 1):
                cut.append(cyl((cx + a * pitch / 2, cy + b * pitch / 2, -1), (hole + tol) / 2, t + 2))
    s = cut_all(s, cut)
    for j, tol in enumerate(MOTOR_T):
        s = engrave_top(s, '+' + fmt(tol), 2.0 + cell * j + cell / 2, 3.6, t, 3.0)
    return s

def coupon_E1():
    return _motor_coupon(44.0, 22.0, 31.0, 3.0)                 # NEMA17 17HS16: pilot 22, M3 on 31

def coupon_E2():
    return _motor_coupon(33.0, W.N11_PILOT_D, W.N11_HOLE_PITCH, W.N11_HOLE)   # NEMA11: pilot 22, M2.5 on 23

# =============================================================================
# F1. servo window frames  -> TOL_MOVE (per side)
# =============================================================================
def coupon_F1():
    t = W.SP_T
    wall, top = 3.0, 7.0
    ws = [(W.SERVO_L + 2 * g, W.SERVO_W + 2 * g) for g in MOVE_T]
    cw = max(a for a, b in ws) + wall
    w, h = 3 * cw + wall, max(b for a, b in ws) + wall + top
    s = plate(w, h, t, 2.0)
    cut = []
    for j, (a, b) in enumerate(ws):
        cx = wall + cw * j + (cw - wall) / 2
        win = box(cx - a / 2, wall, -1, cx + a / 2, wall + b, t + 1)
        win = win.makeFillet(0.5, [e for e in win.Edges if abs(e.Length - (t + 2)) < 1e-6])
        cut.append(win)
    s = cut_all(s, cut)
    for j, g in enumerate(MOVE_T):
        s = engrave_top(s, fmt(g), wall + cw * j + (cw - wall) / 2, h - top / 2, t, 3.5)
    return s

# =============================================================================
# F2. 2020 profile fits: post socket sleeves (per-side gap) and riser tongues  -> socket gap, TOL_MOVE
# =============================================================================
def coupon_F2():
    parts = []
    for j, g in enumerate(SOCKET_T):
        a = 20.0 + 2 * g
        x0 = 30.0 * j
        sl = box(x0, 0, 0, x0 + a + 6.0, a + 6.0, 10.0)
        sl = sl.makeFillet(2.0, [e for e in sl.Edges if abs(e.Length - 10.0) < 1e-6])
        hole = box(x0 + 3.0, 3.0, -1, x0 + 3.0 + a, 3.0 + a, 11.0)
        hole = hole.makeFillet(0.6, [e for e in hole.Edges if abs(e.Length - 12.0) < 1e-6])     # the profile's own corner radius is 0.5
        sl = fillet_all(sl, r_out=0.5).cut(hole)
        sl = engrave_front(sl, '%.1f' % a, x0 + 3.0 + a / 2, 5.0, 0.0, 3.2)
        parts.append(sl)
    for j, g in enumerate(MOVE_T):
        x0 = 30.0 * j
        tw = 6.0 - 2 * g
        blk = box(x0, 34.0, 0, x0 + 24.0, 46.0, 4.0).fuse(box(x0 + 2.0, 40.0 - tw / 2, 4.0, x0 + 22.0, 40.0 + tw / 2, 5.8))
        blk = fillet_all(tidy(blk), r_in=0.4, r_out=0.4)
        blk = engrave_front(blk, '%.1f' % tw, x0 + 12.0, 2.0, 34.0, 2.6)
        parts.append(blk)
    return Part.makeCompound(parts)

# =============================================================================
# F3. small sliding and self-tapping fits: spacer shoulder, zip-tie slots, M2 pilots
# =============================================================================
def coupon_F3():
    w, h, t = 62.0, 40.0, 7.5             # 5 mm deep pilots keep a 2.5 mm floor
    s = plate(w, h, t)
    cut = []
    for j, g in enumerate(trio(W.SPACER_GAP, 0.1)):
        cut.append(cyl((10.0 + 18.0 * j, 30.0, -1), (W.SPACER_OD + 2 * g) / 2, t + 2))          # 7 mm spacer, model 0.3 radial
    for j, (zw, zt) in enumerate(((3.0, 1.8), (3.4, 2.1), (3.8, 2.4))):
        cut.append(slot((10.0 + 18.0 * j - (zw - zt) / 2, 17.0, -1), (10.0 + 18.0 * j + (zw - zt) / 2, 17.0, -1), zt / 2, t + 2))
    for j, d in enumerate(PILOT_T):
        cut.append(cyl((10.0 + 18.0 * j, 7.0, t + 0.01), d / 2, -5.0))                          # M2 self-tapping, 5 deep
    s = cut_all(s, cut)
    for j, (a, b, c) in enumerate(zip(['%.1f' % (W.SPACER_OD + 2 * g) for g in trio(W.SPACER_GAP, 0.1)], ('3x1.8', '3.4', '3.8'), PILOT_T)):
        s = engrave_top(s, a, 10.0 + 18.0 * j + 8.6, 34.5, t, 2.4)
        s = engrave_top(s, '%.1f' % c, 10.0 + 18.0 * j + 7.0, 3.5, t, 2.4)
    return s

# =============================================================================
# G. panel holes: stop button 22, start button 16, LED holder 6  -> TOL_BOLT
# =============================================================================
def coupon_G():
    t = 3.0
    rows = [(22.0, 33.0), (16.0, 25.0), (6.0, 13.0)]
    w = 3 * 30.0 + 4.0
    h = sum(r[1] for r in rows) + 8.0
    s = plate(w, h, t)
    cut = []
    y = 8.0
    ys = []
    for d, rh in rows:
        yc = y + rh / 2
        ys.append(yc)
        for j, tol in enumerate(BOLT_T):
            cut.append(cyl((2.0 + 30.0 * j + 15.0, yc, -1), (d + tol) / 2, t + 2))
        y += rh
    s = cut_all(s, cut)
    for j, tol in enumerate(BOLT_T):
        s = engrave_top(s, '+' + fmt(tol), 2.0 + 30.0 * j + 15.0, 4.0, t, 3.0)
    return s

COUPONS = {
    'tol_A_bolt_holes_vertical': (coupon_A, 'TOL_BOLT', 'M2..M5 clearance holes printed vertical'),
    'tol_B_bolt_holes_horizontal': (coupon_B, 'TOL_BOLT', 'M3..M5 clearance holes through a standing wall'),
    'tol_C_inserts': (coupon_C, 'INSERT_D', 'Ruthex M3 x 5.7 heat-set insert holes'),
    'tol_D1_press_bearing': (coupon_D1, 'TOL_PRESS', '684ZZ seat'),
    'tol_D2_press_dbore_pins': (coupon_D2, 'TOL_PRESS', 'D-bore hub on the NEMA11 shaft, post cap pin in the 2020 centre hole'),
    'tol_E1_nema17': (coupon_E1, 'TOL_MOTOR', 'NEMA17 pilot and M3 holes'),
    'tol_E2_nema11': (coupon_E2, 'TOL_MOTOR', 'NEMA11 pilot and M2.5 holes'),
    'tol_F1_servo_window': (coupon_F1, 'TOL_MOVE', 'DS3218 servo window, gap per side'),
    'tol_F2_profile_socket_tongue': (coupon_F2, 'SOCKET_GAP / TOL_MOVE', '2020 post socket sleeves and beam riser tongues'),
    'tol_F3_spacer_ziptie_pilot': (coupon_F3, 'SPACER_GAP / ZIP_SLOT / M2_PILOT', 'nylon spacer shoulder hole, zip-tie slots, M2 self-tapping pilots'),
    'tol_G_panel_holes': (coupon_G, 'TOL_BOLT', 'stop button 22, start button 16, LED holder 6'),
}

def write_stl(shape, path):
    import numpy as np
    v, t = shape.tessellate(0.02)
    Vv = np.array([[p.x, p.y, p.z] for p in v]); T = Vv[np.array(t)]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ln = np.linalg.norm(n, axis=1, keepdims=True); ln[ln == 0] = 1
    rec = np.zeros(len(T), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
    rec['n'] = n / ln; rec['v'] = T
    with open(path, 'wb') as fh:
        fh.write(b'ETZ plotter tolerance coupon'.ljust(80, b' ')); fh.write(struct.pack('<I', len(T))); fh.write(rec.tobytes())

if __name__ == '__main__':
    import dfm
    out = os.path.join(HERE, 'out')
    os.makedirs(out, exist_ok=True)
    R = {}
    import time
    only = sys.argv[1:] or list(COUPONS)
    for name in only:
        fn, const, what = COUPONS[name]
        t0 = time.time()
        globals()['LABELS'] = True
        s = fn()
        s.exportStep(os.path.join(out, name + '.step'))
        t1 = time.time()
        globals()['LABELS'] = False
        s0 = fn()
        bb = s.BoundBox
        rs = [dfm.report(x, x) for x in s0.Solids]
        r = {'min_wall': min(x['min_wall'] for x in rs), 'widest_bridge_mm': max(x['widest_bridge_mm'] for x in rs),
             'steep_overhang_mm2': sum(x['steep_overhang_mm2'] for x in rs), 'n_sharp': sum(x['n_sharp'] for x in rs)}
        print(name, 'build %.0f s, check %.0f s' % (t1 - t0, time.time() - t1))
        R[name] = {'tests': what, 'constant': const, 'size_mm': [round(bb.XLength, 1), round(bb.YLength, 1), round(bb.ZLength, 1)],
                   'grams_petg_100pct': round(s.Volume / 1000 * 1.27, 1), 'valid': s.isValid(),
                   'min_wall': r['min_wall'], 'widest_bridge_mm': r['widest_bridge_mm'], 'steep_overhang_mm2': r['steep_overhang_mm2'],
                   'n_sharp': r['n_sharp']}
        print('%-36s %-30s %s %5.1f g  wall %s bridge %s overhang %s sharp %s' % (name, const, R[name]['size_mm'], R[name]['grams_petg_100pct'],
              r['min_wall'], r['widest_bridge_mm'], r['steep_overhang_mm2'], r['n_sharp']))
    old = {}
    try:
        old = json.load(open(os.path.join(out, 'coupon_dfm.json')))
    except Exception:
        pass
    old.update(R)
    json.dump(old, open(os.path.join(out, 'coupon_dfm.json'), 'w'), indent=1)
