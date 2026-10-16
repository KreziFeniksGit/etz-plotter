"""Tessellate the whole device (parked pose) and the tolerance coupons for the web assembly animation.
Writes out/anim/parts.json + out/anim/meshes.bin (int16 positions in 0.02 mm, uint16/uint32 indices).
Run: ./fcpy tools/anim_export.py"""
import os, sys, json, struct, glob
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (HERE, os.path.join(HERE, 'wrist'), os.path.join(HERE, 'frame')):
    sys.path.insert(0, p)
import FreeCAD as App, Part
import assembly as A, frame as F
TOL = float(os.environ.get('ANIM_TOL', '0.35'))
Q = 50.0                                  # 1 unit = 0.02 mm
od = os.path.join(HERE, 'out', 'anim'); os.makedirs(od, exist_ok=True)
meta = []; buf = bytearray()

def add(name, s, grp, kind, branch, col):
    v, f = s.tessellate(TOL)
    if not f:
        return
    vo = len(buf)
    for p in v:
        buf.extend(struct.pack('<3h', *(int(round(c * Q)) for c in (p.x, p.y, p.z))))
    while len(buf) % 4: buf.append(0)
    io = len(buf); big = len(v) > 65535
    fmt = '<3I' if big else '<3H'
    for t in f: buf.extend(struct.pack(fmt, *t))
    while len(buf) % 4: buf.append(0)
    meta.append(dict(n=name, g=grp, k=kind, b=branch, c=[round(x, 3) for x in col[:3]],
                     vo=vo, nv=len(v), io=io, nf=len(f), u32=big))

parts = A.world(fasteners=True, detail=False, field=False)
for k, (s, grp, kind, col) in parts.items():
    add(k, s, grp, kind, A.branch(k, kind), F.COL.get(col, (0.6, 0.6, 0.6)))

# coupons laid out in a row on the table (only shown in step 0)
x0, y0, row = 20.0, 60.0, 0.0
for fn in sorted(glob.glob(os.path.join(HERE, 'tolerance', 'out', '*.step'))):
    s = Part.read(fn)
    bb = s.BoundBox
    if x0 + bb.XLength > 440:
        x0, y0, row = 20.0, y0 + row + 12, 0.0
    s.translate(App.Vector(x0 - bb.XMin, y0 - bb.YMin, -bb.ZMin))
    x0 += bb.XLength + 12; row = max(row, bb.YLength)
    add('coupon_' + os.path.basename(fn)[:-5], s, 'coupon', 'coupon', 'Coupons', (0.95, 0.55, 0.15))
import gzip
open(os.path.join(od, 'meshes.dat'), 'wb').write(gzip.compress(bytes(buf), 9))
json.dump(meta, open(os.path.join(od, 'parts.json'), 'w'), separators=(',', ':'))
print(len(meta), 'parts', len(buf) // 1024, 'KB')
os._exit(0)
