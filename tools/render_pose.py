"""Render a pose of the whole device to PNG (matplotlib, painter's algorithm).
usage: fcpy tools/render_pose.py PYC PXB h wrist out.png [az el] [xmin xmax ymin ymax zmin zmax]"""
import sys, math, os
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [HERE, os.path.join(HERE, 'wrist'), os.path.join(HERE, 'frame')]
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import assembly as A, frame as F
a = sys.argv[1:]
PYC, PXB, h, wd = map(float, a[:4]); out = a[4]
az, el = (float(a[5]), float(a[6])) if len(a) > 6 else (-35.0, 28.0)
crop = list(map(float, a[7:13])) if len(a) > 12 else None
parts = A.world(PYC, PXB, h, wd, field=crop is None, fasteners=True, detail=True)   # real vendor models
azr, elr = math.radians(az), math.radians(el)
d = np.array([math.cos(elr) * math.sin(azr), -math.cos(elr) * math.cos(azr), math.sin(elr)])
x = np.cross([0, 0, 1.0], d); x /= np.linalg.norm(x); y = np.cross(d, x); M = np.stack([x, y, d])
L = np.array([-0.3, -0.5, 0.8]); L /= np.linalg.norm(L)
polys, cols, dep = [], [], []
for k, (s, g, kind, col) in parts.items():
    bb = s.BoundBox
    if crop and (bb.XMax < crop[0] or bb.XMin > crop[1] or bb.YMax < crop[2] or bb.YMin > crop[3] or bb.ZMax < crop[4] or bb.ZMin > crop[5]):
        continue
    base = np.array(F.COL.get(col, (0.6, 0.6, 0.6)))
    if k.startswith('cable_') and not k.startswith('cable_chain'):
        base = np.array((0.85, 0.35, 0.2))
    if kind == 'fastener':
        base = np.array((0.95, 0.80, 0.15)) if col == 'insert' else np.array((0.85, 0.15, 0.15))   # screws drawn red so they stand out
    v, f = s.tessellate(0.4)
    if not f:
        continue
    V3 = np.array([[p.x, p.y, p.z] for p in v]); T = V3[np.array(f)]
    n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ln = np.linalg.norm(n, axis=1); ok = ln > 1e-12
    T, n = T[ok], n[ok] / ln[ok][:, None]
    P = T @ M.T; vis = n @ d > 0
    sh = 0.5 + 0.5 * np.clip(n[vis] @ L, 0, 1)
    for t, kk in zip(P[vis], sh):
        polys.append(t[:, :2]); dep.append(t[:, 2].mean()); cols.append(np.clip(base * kk, 0, 1))
o = np.argsort(dep)
fig, ax = plt.subplots(figsize=(13, 9), dpi=110)
ax.add_collection(PolyCollection([polys[i] for i in o], facecolors=[cols[i] for i in o], edgecolors='face', linewidths=0.15))
ax.set_aspect('equal'); ax.autoscale_view(); ax.axis('off')
ax.set_title('Y %g  X %g  face %g mm  wrist %g deg' % (PYC, PXB, h, wd), fontsize=10)
fig.tight_layout(); fig.savefig(out)
