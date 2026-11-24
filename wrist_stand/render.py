"""Render the wrist stand with the wrist on it -> out/wrist_stand.png (run wrist_stand.py first)."""
import math, os
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import FreeCAD, Part
HERE = os.path.dirname(os.path.abspath(__file__))
COL = [(0.30, 0.45, 0.70), (0.85, 0.55, 0.15), (0.20, 0.60, 0.45)]   # base, post, head; the wrist is grey
WRIST = (0.62, 0.62, 0.62)
L = np.array([-0.3, -0.5, 0.8]); L /= np.linalg.norm(L)
SOLIDS = Part.read(os.path.join(HERE, 'out', 'wrist_stand_assembly.step')).Solids

def view(ax, az, el, title):
    a, e = math.radians(az), math.radians(el)
    d = np.array([math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)])
    x = np.cross([0, 0, 1], d); x /= np.linalg.norm(x); y = np.cross(d, x); M = np.stack([x, y, d])
    allP, allC, allZ = [], [], []
    for i, s in enumerate(SOLIDS):
        v, t = s.tessellate(0.3)
        if not t:
            continue
        T = np.array([[p.x, p.y, p.z] for p in v])[np.array(t)]
        nn = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ln = np.linalg.norm(nn, axis=1); ok = ln > 1e-12
        T, nn = T[ok], nn[ok] / ln[ok][:, None]
        P = T @ M.T; vis = nn @ d > 0
        sh = 0.45 + 0.55 * np.clip(nn[vis] @ L, 0, 1)
        col = COL[i] if i < 3 else WRIST
        allP.append(P[vis]); allZ.append(P[vis][:, :, 2].mean(axis=1))
        allC.append(np.clip(np.array(col)[None, :] * sh[:, None] + 0.05, 0, 1))
    P, C, Z = np.concatenate(allP), np.concatenate(allC), np.concatenate(allZ)
    o = np.argsort(Z)
    ax.add_collection(PolyCollection(P[o][:, :, :2], facecolors=C[o], edgecolors='face', linewidths=0.1))
    ax.set_aspect('equal'); ax.autoscale_view(); ax.axis('off'); ax.set_title(title)

fig, axs = plt.subplots(1, 2, figsize=(15, 7), dpi=90)
view(axs[0], -60, 25, 'wrist stand (blue base, orange post, green head) with the real wrist, h 22.5')
view(axs[1], -90, 0, 'side: head underside at z 139 = MGN12H block face; magnet h 5..40 over the desk')
fig.tight_layout(); fig.savefig(os.path.join(HERE, 'out', 'wrist_stand.png'))
