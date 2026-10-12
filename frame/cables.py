"""
ETZ plotter v2: cable harness paths (FreeCAD Part script)
=========================================================
Each harness is a round tube (bundle diameter) along a polyline, so the checks can see it.
Coordinates are world mm; parts on the Y carriage are given at y relative to PYC, parts on the
wrist module at x relative to PXB and y relative to PYC. Inside the chains the cables are not drawn.

Wiring of each harness: see wiring.md (same names).
"""
import FreeCAD as App
import Part
import wrist_module as W

V = App.Vector

def tube(pts, d):
    r = d / 2
    out = None
    for a, b in zip(pts[:-1], pts[1:]):
        A, B = V(*a), V(*b)
        L = (B - A).Length
        if L < 1e-6:
            continue
        seg = Part.makeCylinder(r, L, A, B - A)
        out = seg if out is None else out.fuse(seg)
    for p in pts[1:-1]:
        out = out.fuse(Part.makeSphere(r, V(*p)))
    return out.removeSplitter()

# ---------------------------------------------------------------- wrist module (moves with the X carriage)
# up the chain post's -y face (zip ties at z 165 and 192), over the post plate, into the X chain's moving end
WRIST = {
    'cable_wrist_bundle': (7.0, [(13, -28.5, 142), (13, -28.5, 211), (6, -14, 216.5), (0, 0, 216.5), (5, 0, 216.5)]),
    # servo lead: out of the case's spline end 8 mm above the case bottom (MG996R), then to -y beside the case end
    # (clear of the chain post screw heads under the plate) and up to the bundle
    'cable_wrist_servo': (3.5, [(W.SERVO_X1 + W.SERVO_LEAD_BOSS + 1.95, W.CASE_TOP_Y - W.SERVO_CASE_H + W.SERVO_LEAD_UP, W.Z_PIVOT_TOP),
                                (W.SERVO_X1 + W.SERVO_LEAD_BOSS + 1.95, -27.0, 120.0), (13, -28.5, 142)]),
}
# ---------------------------------------------------------------- Y carriage (moves in Y)
YCAR = {
    # X chain fixed end -> beside the boom on -y -> down the post's -y face -> carriage top -> Y chain moving end
    'cable_ycar_bundle': (7.0, [(234, 0, 181.5), (227, -14, 182.5), (207, -14, 182.5), (207, -14, 99), (207, -19.5, 93.5),
                                (207, -19.5, 72.5), (230, -19.5, 72.5), (230, 1, 72.5), (235.5, 6, 78.0), (235.5, 16, 78.0)]),
    # X motor (rear) -> under the X motor mount -> beside the post socket -> joins at the Y chain end
    'cable_x_motor': (5.0, [(165, 74, 150), (165, 74, 118), (192, 22, 100), (192, 22, 71.5), (219, 22, 71.5), (219, 4, 71.5), (229, 3, 71.5)]),
    'cable_x_home': (3.0, [(212, 19, 124.5), (195, 22, 104)]),
}
# ---------------------------------------------------------------- base (static)
BASE = {
    # Y chain fixed end -> electronics board
    'cable_y_chain_to_board': (7.0, [(235.5, 218, 39.5), (235.5, 210, 39.5), (245, 203, 31), (262, 190, 31)]),
    # Y motor (lead stub on its +y side, near the rear) -> down to the plywood -> beside the motor mount base (x < 152) -> corridor x 189.5 -> under the beam at y 205 -> board
    'cable_y_motor': (5.0, [(135.2, 484.5, 45.0), (135.2, 484.5, 30.0), (135.2, 468.0, 18), (148.5, 420, 18), (149.5, 411.5, 18), (165, 411.5, 18), (189.5, 300, 18), (189.5, 205, 18), (225, 200, 18),
                            (240, 196, 31), (268, 180, 31)]),
    # battery -> corridor x 184 -> into the control panel (stop button)
    'cable_battery': (5.0, [(125, 301.5, 35), (125, 296, 33), (125, 294, 22), (184, 290, 22), (184, 100, 22), (166, 80, 22), (156, 80, 22)]),
    # control panel (stop, start, LEDs, connectors A/B/C, drive power) -> under the beam at y 60 -> board
    'cable_panel_to_board': (6.0, [(156, 74, 22), (170, 74, 22), (176, 60, 18.5), (232, 60, 18.5), (242, 104, 32), (268, 128, 32)]),
    # Y home switch -> board
    'cable_y_home': (3.0, [(239, 9, 44), (239, 9, 22), (239, 30, 18), (239, 100, 18), (242, 106, 31), (262, 116, 31)]),
}

def wrist_harness(PYC, PXB, h, wrist_deg=0.0):
    """Wrist harness tubes for one pose: each path point moves with its own group (end, top arm, carriage)."""
    out = {}
    for k, (d, pts) in W.harness_paths().items():
        P = []
        for g, p in pts:
            q = W.pose(Part.Vertex(V(*p)), g, h, wrist_deg).Point
            P.append((q.x + PXB, q.y + PYC, q.z))
        out[k] = (tube(P, d), 'wm_cable', 'cable', 'cable')
    return out

def harness(PYC, PXB):
    out = {}
    for k, (d, pts) in WRIST.items():
        out[k] = (tube([(PXB + x, PYC + y, z) for x, y, z in pts], d), 'wm_xcar', 'cable', 'cable')
    for k, (d, pts) in YCAR.items():
        out[k] = (tube([(x, PYC + y, z) for x, y, z in pts], d), 'ycar', 'cable', 'cable')
    for k, (d, pts) in BASE.items():
        out[k] = (tube(pts, d), 'base', 'cable', 'cable')
    return out
