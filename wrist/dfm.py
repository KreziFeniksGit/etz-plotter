"""Shared DFM checks: wall thickness, overhang and bridges, sharp internal corners (print orientation)."""
import math
import FreeCAD as App
import Part
import numpy as np
import wrist_module as W
V = App.Vector

def orient(shape, axis, deg):
    s = shape.copy()
    if deg:
        s.rotate(V(0, 0, 0), axis, deg)
    bb = s.BoundBox
    s.translate(V(-(bb.XMin + bb.XMax) / 2, -(bb.YMin + bb.YMax) / 2, -bb.ZMin))
    return s

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


def report(shape_in_print_orientation, model_shape):
    s = shape_in_print_orientation
    bb = s.BoundBox
    th = thickness_samples(s)
    thin = sorted([t for t in th if t[0] < W.WALL_MIN - 0.05])
    over, br = overhang_and_bridges(s)
    sharp = sharp_internal(model_shape)
    return dict(size=[round(bb.XLength, 1), round(bb.YLength, 1), round(bb.ZLength, 1)],
                fits_220=bb.XLength <= 220 and bb.YLength <= 220, volume_cm3=round(s.Volume / 1000, 2),
                mass_g=round(s.Volume / 1000 * 1.27 * 0.6, 1), min_wall=round(min(t[0] for t in th), 2) if th else None,
                thin_samples=len(thin), thin_examples=thin[:6], steep_overhang_mm2=over,
                widest_bridge_mm=br[0][0] if br else 0, bridges=br[:5], sharp_internal_edges=sharp[:8], n_sharp=len(sharp))
