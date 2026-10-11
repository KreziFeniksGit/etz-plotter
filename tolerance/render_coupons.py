"""Render every coupon STEP (labels included) -> out/coupons_overview.png"""
import glob, math, os
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import FreeCAD, Part
HERE = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(HERE, 'out', 'tol_*.step')))
L = np.array([-0.3, -0.4, 0.85]); L /= np.linalg.norm(L)
el = math.radians(60); d = np.array([0, -math.cos(el), math.sin(el)])
x = np.array([1.0, 0, 0]); y = np.cross(d, x); M = np.stack([x, y, d])
fig, axs = plt.subplots(4, 3, figsize=(14, 15), dpi=80)
for ax, f in zip(axs.flat, files):
    s = Part.read(f)
    v, t = s.tessellate(0.3)
    T = np.array([[p.x, p.y, p.z] for p in v])[np.array(t)]
    del s, v, t
    nn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ln = np.linalg.norm(nn, axis=1); ok = ln > 1e-12
    T, nn = T[ok], nn[ok] / ln[ok][:, None]
    P = T @ M.T; vis = nn @ d > 0
    P, sh = P[vis], 0.45 + 0.55 * np.clip(nn[vis] @ L, 0, 1)
    o = np.argsort(P[:, :, 2].mean(axis=1))
    cols = np.clip(np.array([0.12, 0.55, 0.52])[None, :] * sh[o][:, None] + 0.08, 0, 1)
    ax.add_collection(PolyCollection(P[o][:, :, :2], facecolors=cols, edgecolors='face', linewidths=0.1))
    ax.set_aspect('equal'); ax.autoscale_view(); ax.axis('off')
    ax.set_title(os.path.basename(f)[:-5], fontsize=10)
for ax in list(axs.flat)[len(files):]:
    ax.axis('off')
fig.tight_layout(); fig.savefig(os.path.join(HERE, 'out', 'coupons_overview.png'))
