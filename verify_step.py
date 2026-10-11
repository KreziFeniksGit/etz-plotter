import re, sys, math
import FreeCAD as App, Part
import numpy as np
path = sys.argv[1]
txt = open(path).read()
print('products', len(re.findall(r"PRODUCT\('", txt)), 'colours', len(re.findall('COLOUR_RGB', txt)))
names = sorted(set(re.findall(r"PRODUCT\('([^']*)'", txt)))
print('sample names', names[:6], '...', names[-4:])
s = Part.read(path)
print('solids', len(s.Solids), 'valid', s.isValid(), 'bbox', [round(v, 1) for v in (s.BoundBox.XMin, s.BoundBox.YMin, s.BoundBox.ZMin, s.BoundBox.XMax, s.BoundBox.YMax, s.BoundBox.ZMax)])
if len(sys.argv) > 2:
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection
    az, el = math.radians(-35), math.radians(28)
    d = np.array([math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), math.sin(el)])
    x = np.cross([0, 0, 1.0], d); x /= np.linalg.norm(x); y = np.cross(d, x); M = np.stack([x, y, d])
    L = np.array([-0.3, -0.5, 0.8]); L /= np.linalg.norm(L)
    polys, cols, dep = [], [], []
    for so in s.Solids:
        if so.BoundBox.ZMax < 0.5 and so.BoundBox.XLength > 200:
            base = np.array([0.85, 0.86, 0.87])
        else:
            base = np.array([0.45, 0.62, 0.66])
        v, f = so.tessellate(0.5)
        if not f:
            continue
        V3 = np.array([[p.x, p.y, p.z] for p in v]); T = V3[np.array(f)]
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ln = np.linalg.norm(n, axis=1); ok = ln > 1e-12
        T, n = T[ok], n[ok] / ln[ok][:, None]
        P = T @ M.T; vis = n @ d > 0
        sh = 0.45 + 0.55 * np.clip(n[vis] @ L, 0, 1)
        for t, k in zip(P[vis], sh):
            polys.append(t[:, :2]); dep.append(t[:, 2].mean()); cols.append(np.clip(base * k, 0, 1))
    o = np.argsort(dep)
    fig, ax = plt.subplots(figsize=(12, 9), dpi=110)
    ax.add_collection(PolyCollection([polys[i] for i in o], facecolors=[cols[i] for i in o], edgecolors='face', linewidths=0.2))
    ax.set_aspect('equal'); ax.autoscale_view(); ax.axis('off'); ax.set_title('re-imported ' + path.split('/')[-1], fontsize=10)
    fig.tight_layout(); fig.savefig(sys.argv[2])
