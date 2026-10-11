"""Design review of the wrist module: interference over the motion range, DFM in
print orientation (bed fit, wall thickness, overhangs, bridges, sharp internal
corners), clearance table. Writes out/review.json and out/*.png renders."""
import json, math, os, sys
import FreeCAD as App
import Part
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wrist_module as W

V = App.Vector
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
os.makedirs(OUT, exist_ok=True)
R = {}

parts, bought = W.build_all()
R['fillet_skips'] = W.FILLET_LOG[:]
R['valid'] = {k: (s.isValid(), len(s.Solids)) for k, s in parts.items()}

# ------------------------------------------------------------------ interference
ALLOWED = {frozenset(p) for p in [
    ('servo_tabs', 'servo_plate'), ('servo_horn', 'arm_top'), ('servo_spline', 'servo_horn'), ('servo_case', 'servo_spline'),
    ('x_belt', 'x_belt_clamp'),              # 0.3 mm squeeze is the design
    ('brg_AL', 'arm_bottom'), ('brg_BL', 'arm_bottom'), ('brg_BT', 'arm_top'),
    ('nema11_shaft', 'wrist_hub'), ('nema11_pilot', 'nema11'), ('nema11_shaft', 'nema11_pilot'),
    ('electromagnet', 'wrist_hub'), ('camera_board', 'camera_lens'), ('servo_case', 'servo_tabs'), ('x_belt', 'x_belt_riser'), ('spacer_AL', 'brg_AL'), ('spacer_BT', 'brg_BT'), ('spacer_BL', 'brg_BL'), ('shim_BT', 'brg_BT'), ('shim_BL', 'brg_BL'), ('shim_AL', 'brg_AL'), ('shim_BT', 'end_plate'), ('shim_BL', 'end_plate'), ('spacer_AL', 'wrist_carriage'),
]}
allsol = dict(parts); allsol.update(bought)

def check(h, w):
    posed = {k: W.pose(s, W.GROUP[k], h, w) for k, s in allsol.items()}
    hits = {}
    ks = list(posed)
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            a, b = ks[i], ks[j]
            if frozenset((a, b)) in ALLOWED:
                continue
            A, B = posed[a], posed[b]
            if not A.BoundBox.intersect(B.BoundBox):
                continue
            v = A.common(B).Volume
            if v > 0.5:
                hits['%s | %s' % (a, b)] = round(v, 2)
    return hits

sweep = {}
for h in (5.0, 10.0, 16.0, 22.5, 30.0, 36.0, 40.0):
    for w in ((0.0, 90.0, 180.0) if h in (5.0, 40.0) else (0.0,)):
        hh = check(h, w)
        if hh:
            sweep['h=%g w=%g' % (h, w)] = hh
R['interference'] = sweep or 'none'

# minimum gaps between moving neighbours (should be >= 0.3)
def gap(a, b, h):
    A = W.pose(allsol[a], W.GROUP[a], h); B = W.pose(allsol[b], W.GROUP[b], h)
    return round(A.distToShape(B)[0], 2)
GAPS = [('arm_top', 'wrist_carriage'), ('arm_bottom', 'wrist_carriage'), ('servo_horn', 'wrist_carriage'), ('arm_top', 'x_belt_riser'), ('arm_bottom', 'shelf'),
        ('arm_top', 'end_plate'), ('arm_bottom', 'end_plate'), ('arm_top', 'arm_bottom'), ('servo_case', 'wrist_carriage'),
        ('arm_top', 'servo_case'), ('wrist_hub', 'shelf'), ('electromagnet', 'shelf'), ('end_plate', 'wrist_carriage'),
        ('spacer_AL', 'arm_bottom'), ('spacer_BT', 'arm_top'), ('spacer_BL', 'arm_bottom'), ('shim_BT', 'arm_top'), ('shim_BL', 'arm_bottom'), ('shim_AL', 'arm_bottom')]
R['min_gap_mm'] = {}
for a, b in GAPS:
    R['min_gap_mm']['%s | %s' % (a, b)] = min(gap(a, b, h) for h in (5.0, 22.5, 40.0))

# lowest points at h = 5 (field clearance): only the magnet may touch the field
low = {}
for k in ('camera_lens', 'camera_board', 'shelf', 'wrist_hub', 'end_plate', 'arm_bottom'):
    low[k] = round(W.pose(allsol[k], W.GROUP[k], 5.0).BoundBox.ZMin, 1)
R['lowest_z_at_h5'] = low

# ------------------------------------------------------------------ DFM in print orientation
def oriented(name):
    fn, (axis, deg), how, qty = W.PRINTED[name]
    s = parts[name].copy()
    if deg:
        s.rotate(V(0, 0, 0), axis, deg)
    bb = s.BoundBox
    s.translate(V(-(bb.XMin + bb.XMax) / 2, -(bb.YMin + bb.YMax) / 2, -bb.ZMin))
    return s, how, qty

def thickness_samples(s, per_face=4):
    """Wall thickness: from points on each planar face, shoot inward along -normal
    and measure the first solid segment."""
    res = []
    for fi, f in enumerate(s.Faces):
        if f.Area < 1.0:
            continue
        u0, u1, v0, v1 = f.ParameterRange
        for a in np.linspace(0.2, 0.8, per_face):
            for b in np.linspace(0.2, 0.8, per_face):
                u, v = u0 + (u1 - u0) * a, v0 + (v1 - v0) * b
                p = f.valueAt(u, v)
                if not f.isInside(p, 1e-6, True):
                    continue
                n = f.normalAt(u, v)
                seg = Part.LineSegment(p + n * 0.02, p - n * 60.0).toShape()
                com = s.common(seg)
                best = None
                for e in com.Edges:
                    d0 = min(e.Vertexes[0].Point.distanceToPoint(p), e.Vertexes[-1].Point.distanceToPoint(p))
                    if d0 < 0.1:
                        best = e.Length
                if best is not None:
                    res.append((best, (round(p.x, 1), round(p.y, 1), round(p.z, 1)), fi))
    return res

def overhang_and_bridges(s, limit=45.0):
    over, bridges = 0.0, []
    cl = -math.cos(math.radians(limit))
    for f in s.Faces:
        u0, u1, v0, v1 = f.ParameterRange
        n = f.normalAt((u0 + u1) / 2, (v0 + v1) / 2)
        if f.BoundBox.ZMax < 0.05:
            continue                       # on the bed
        planar = f.Surface.__class__.__name__ == 'Plane'
        if planar and n.z < -0.999:
            bb = f.BoundBox
            span = min(bb.XLength, bb.YLength)
            supported = False
            # is it the roof of a hole or slot (bridge) or a free overhang?
            bridges.append((round(span, 1), round(f.Area, 1), (round(bb.Center.x, 1), round(bb.Center.y, 1), round(bb.ZMin, 1))))
        elif n.z < cl and planar:
            over += f.Area
    return round(over, 1), sorted(bridges, reverse=True)

def sharp_internal(s):
    out = []
    for e in s.Edges:
        if not W.is_line(e) or e.Length < 2.0:
            continue
        c = W._concave(s, e)
        if c:
            m = e.valueAt((e.FirstParameter + e.LastParameter) / 2)
            fs = s.ancestorsOfType(e, Part.Face)
            if all(f.Surface.__class__.__name__ == 'Plane' for f in fs):
                out.append((round(e.Length, 1), (round(m.x, 1), round(m.y, 1), round(m.z, 1))))
    return out

dfm = {}
for name in W.PRINTED:
    s, how, qty = oriented(name)
    bb = s.BoundBox
    th = thickness_samples(s)
    thin = sorted([t for t in th if t[0] < W.WALL_MIN - 0.05])
    over, br = overhang_and_bridges(s)
    sharp = sharp_internal(parts[name])
    s.exportStep(os.path.join(OUT, name + '.step'))      # STEP only (Part.export writes an empty file without the GUI)
    dfm[name] = dict(orientation=how, qty=qty, size=[round(bb.XLength, 1), round(bb.YLength, 1), round(bb.ZLength, 1)],
                     fits_220=bb.XLength <= 220 and bb.YLength <= 220, volume_cm3=round(s.Volume / 1000, 2),
                     mass_g=round(s.Volume / 1000 * 1.27 * 0.6, 1), min_wall=round(min(t[0] for t in th), 2) if th else None,
                     thin_samples=len(thin), thin_examples=thin[:6], steep_overhang_mm2=over,
                     widest_bridge_mm=br[0][0] if br else 0, bridges=br[:5], sharp_internal_edges=sharp[:8], n_sharp=len(sharp))
R['dfm'] = dfm

# ------------------------------------------------------------------ clearance table
R['clearances'] = {
    'M3 bolt hole': W.bolt(3), 'M4 bolt hole (pivots)': W.bolt(4), 'M2 camera hole': 2 + W.TOL_BOLT,
    'NEMA11 screw hole (M2.5 +0.2)': W.N11_HOLE + W.TOL_MOTOR, 'NEMA11 pilot hole (22 +0.2)': W.N11_PILOT_D + W.TOL_MOTOR,
    '684ZZ seat (9 +0.12, press)': W.BRG_OD + W.TOL_PRESS, 'bearing shoulder hole (4 + 2x0.4 + 1.5)': W.BRG_ID + 2 * W.TOL_MOVE + 1.5,
    'D-bore on stepper shaft (5 +0.12, press)': W.N11_SHAFT_D + W.TOL_PRESS, 'servo window (case + 0.4 each side)': W.TOL_MOVE,
    'arm to end plate gap (washer)': W.WASHER_T, 'heat-set insert hole': W.INSERT_D, 'TO-92 pocket (+0.12)': W.TO92_W + W.TOL_PRESS,
}
json.dump(R, open(os.path.join(OUT, 'review.json'), 'w'), indent=1, default=str)

# ------------------------------------------------------------------ renders
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
COL = {'printed': (0.13, 0.55, 0.52), 'bought': (0.55, 0.58, 0.62), 'dark': (0.22, 0.24, 0.27)}
def tri(shape, tol=0.15):
    v, f = shape.tessellate(tol)
    v = np.array([[p.x, p.y, p.z] for p in v]); f = np.array(f)
    return v[f] if len(f) else np.zeros((0, 3, 3))
def render(items, path, az, el, title):
    a, e = math.radians(az), math.radians(el)
    d = np.array([math.cos(e) * math.sin(a), -math.cos(e) * math.cos(a), math.sin(e)])
    up = np.array([0, 0, 1.0]); x = np.cross(up, d); x /= np.linalg.norm(x); y = np.cross(d, x); M = np.stack([x, y, d])
    L = np.array([-0.3, -0.5, 0.8]); L /= np.linalg.norm(L)
    polys, cols, dep = [], [], []
    for T, c in items:
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ln = np.linalg.norm(n, axis=1); ok = ln > 1e-12
        T, n = T[ok], n[ok] / ln[ok][:, None]
        P = T @ M.T; vis = n @ d > 0
        sh = 0.45 + 0.55 * np.clip(n[vis] @ L, 0, 1)
        for t, s in zip(P[vis], sh):
            polys.append(t[:, :2]); dep.append(t[:, 2].mean()); cols.append(np.clip(np.array(c) * s, 0, 1))
    o = np.argsort(dep)
    fig, ax = plt.subplots(figsize=(10, 8), dpi=110)
    ax.add_collection(PolyCollection([polys[i] for i in o], facecolors=[cols[i] for i in o], edgecolors='face', linewidths=0.2))
    ax.set_aspect('equal'); ax.autoscale_view(); ax.axis('off'); ax.set_title(title, fontsize=10)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)

def scene(h, w=0.0):
    items = []
    for k, s in allsol.items():
        c = COL['printed'] if k in parts else (COL['dark'] if k in ('nema11', 'servo_case', 'camera_board') else COL['bought'])
        items.append((tri(W.pose(s, W.GROUP[k], h, w)), c))
    return items
if '--norender' not in sys.argv:
    render(scene(22.5), os.path.join(OUT, 'module_front.png'), -40, 22, 'wrist module, face at 22.5 mm')
    render(scene(40.0, 90), os.path.join(OUT, 'module_back_up.png'), 140, 22, 'face at 40 mm, wrist 90 deg, from behind')
    render(scene(5.0), os.path.join(OUT, 'module_side_down.png'), 0, 0, 'side view, face at 5 mm')
    for name in W.PRINTED:
        s, how, qty = oriented(name)
        render([(tri(s, 0.08), COL['printed'])], os.path.join(OUT, 'print_' + name + '.png'), -35, 30, '%s (print orientation: %s)' % (name, how))

print(json.dumps({k: R[k] for k in ('fillet_skips', 'interference', 'min_gap_mm', 'lowest_z_at_h5')}, indent=1))
for k, d in dfm.items():
    print('%-15s %-28s size %s min_wall %s thin %d bridge %s overhang %s sharp %d' % (
        k, d['orientation'][:28], d['size'], d['min_wall'], d['thin_samples'], d['widest_bridge_mm'], d['steep_overhang_mm2'], d['n_sharp']))
