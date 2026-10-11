"""
ETZ plotter v2: frame, Y axis, X axis and base items  (FreeCAD Part script)
==========================================================================
World coordinates (mm), the competition polygon:
  X  along the 600 mm side (0..350 = zone 1, field from 350),
  Y  along the 500 mm side,
  Z  up from the table.
Everything that rides on the Y carriage is built at the parked position
PYC0 = 40 (Y carriage centre) and moved by (0, PYC - PYC0, 0).
The wrist module (wrist/wrist_module.py) hangs under the X rail block at (PXB, PYC).

Printed parts in this file: y_carriage, y_belt_spacer, y_belt_clamp, y_motor_mount,
y_idler_bracket, x_motor_mount, x_idler_bracket, post_cap, control_panel,
breadboard_tray, battery_tray.
"""
import math, os, sys
import FreeCAD as App
import Part
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'wrist'))
import wrist_module as W
import chains
from wrist_module import (box, cyl, slot, prism_x, prism_y, prism_z, rbox, zip_pair, fillet_all, cut_all, tidy, bolt,
                          TOL_MOVE, TOL_PRESS, TOL_BOLT, TOL_MOTOR, INSERT_D, INSERT_DEPTH, WALL_MIN)

V = App.Vector

# =============================================================================
# 1. LAYOUT PARAMETERS
# =============================================================================
PYC0, PXB0 = 40.0, 292.0                  # parked Y carriage centre, parked wrist pivot X (magnet at x 397, first cell column)
PYC_RANGE = (40.0, 376.0)
PXB_RANGE = (292.0, 435.0)                 # 292: wrist carriage clears the Y carriage (x 245); magnet x 397..540 covers the cells (397..537)
# base
Z_FOOT, Z_PLY = 3.0, 12.0                 # rubber feet height, plywood thickness
Z_PLY0, Z_PLY1 = Z_FOOT, Z_FOOT + Z_PLY
PLY = (90.0, 0.0, 340.0, 470.0)           # plywood outline (corner radius 10)
FEET = [(100.0, 22.0), (330.0, 22.0), (100.0, 458.0), (330.0, 458.0)]
FOOT_D, FOOT_H, FOOT_POCKET = 20.0, 7.0, 4.0     # screw-on rubber foot 20 x 7, sits 4 mm deep in a pocket: 3 mm below the plywood
FOOT_SCREW_SINK = 2.5                            # wood screw head recess inside the foot
BEAM_CBORE = 7.5                                 # counterbore depth for the beam bolt heads (M5x20 socket cap)
# Y axis
YB_X = 205.0                              # Y beam / rail centre line
YB_Y0, YB_Y1 = 10.0, 410.0                # 2020 beam and MGN12 rail, 400 mm
Y_RISER = 10.0                            # printed risers under the Y beam: a cable tunnel under the beam (y 155..265)
BEAM_BOLTS_Y = (40.0, 140.0, 280.0, 380.0)
Z_YB0 = Z_PLY1 + Y_RISER                  # beam bottom
Z_YB1 = Z_YB0 + 20.0                      # beam top
Z_YR1 = Z_YB1 + 8.0                       # rail top
Z_YBLK0, Z_YBLK1 = Z_YB1 + 3.0, Z_YB1 + 13.0
Y_BELT_Z = 36.5 + Y_RISER                 # Y pulley axis height
Y_BELT_X0, Y_BELT_X1 = 183.0, 189.0       # belt width (along X)
GT2_PD = 12.73                            # 20T pitch diameter
YM_C = (443.0, Y_BELT_Z)                  # Y motor axis (Y, Z)
YM_FACE = 171.5                           # Y motor face (motor body on the -X side)
YI_C = (12.0, Y_BELT_Z)                   # Y idler axis (y 12: the axle nut stays clear of the parked Y block, y >= 17.3)
# Y carriage
YC_X0, YC_X1 = 165.0, 245.0
YC_HALF_Y = 30.0
Z_YC0, Z_YC1 = Z_YBLK1, Z_YBLK1 + 10.0
assert abs(Z_YC1 - chains.Z_CARRIAGE_TOP) < 1e-6
POST_C = (199.0, PYC0)
POST_L = 140.0 - Y_RISER                  # post length keeps the boom at z 152..172
Z_POST0, Z_POST1 = Z_YC1, Z_YC1 + POST_L
SOCKET_H = 25.0
# X axis (boom, rail)
BOOM_X0, BOOM_X1 = 209.0, 479.0
Z_BOOM0, Z_BOOM1 = 152.0, 172.0
XR_X0, XR_X1 = 229.0, 479.0               # MGN12 rail 250
X_BELT_Z = 162.0
XB_DY0, XB_DY1 = 14.0, 20.0               # belt width (along Y), relative to PYC
XM_C = (165.0, X_BELT_Z)                  # X motor axis (X, Z)
XM_FACE_DY = 31.5                         # motor face, relative to PYC
XI_C = (470.0, X_BELT_Z)                  # X idler axis
# control panel and base items
PANEL = (95.0, 30.0, 160.0, 125.0, 55.0)  # x0, y0, x1, y1, top z
ESTOP_C, START_C = (122.0, 62.0), (145.0, 95.0)
LED_G, LED_R = (108.0, 108.0), (122.0, 108.0)
STOP_TEXT = (8.0, 0.3)                    # 'STOP' on the stop button cap: letter height, thickness (cosmetic)
FONT = next((f for f in ('C:/Windows/Fonts/arialbd.ttf', 'C:/Windows/Fonts/segoeuib.ttf',
                         '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/System/Library/Fonts/Supplemental/Arial Bold.ttf')
             if os.path.exists(f)), None)     # bold TTF for the label; the label is skipped if none is found
CONN = {'A': (50.0, 3), 'B': (70.0, 3), 'C': (93.0, 4)}     # Y centre, pins (2.54 mm)
BB = (95.0, 139.0)                        # breadboard corner
BAT = (105.0, 34.0, 30.0)                 # 4S 2200 mAh pack, L x W x H
BT = (100.0, 300.0, 100.0 + BAT[1] + 2 * (2.4 + 1.9), 300.0 + BAT[0] + 2 * (2.4 + 1.9))   # battery tray outline
EB = (246.0, 110.0, 326.0, 210.0)         # electronics board

# bought-part data
NEMA17 = dict(sq=42.3, L=40.0, chamfer=4.0, hole=31.0, pilot=22.0, pilot_h=2.0, shaft=5.0, shaft_L=23.0, flat=4.5)   # 17HS16-2004S1
D2F = dict(L=12.8, W=5.8, H=6.5, hole_pitch=6.5)          # Omron D2F-01L
ESP32_BOARD = (25.5, 62.7)                # ESP32-S3-DevKitC-1 (N16R8) board, x by y. VERIFY on the board you have (clones differ)
ESP32_PIN_ROWS = 22.86                    # distance between its two pin rows (VERIFY)
HDR_H = 8.5                               # female header height (modules plug in, so they can be swapped)

PARTS = {}      # name -> (shape, group, kind, colour)
COL = {'printed': (0.12, 0.55, 0.52), 'printed2': (0.85, 0.47, 0.13), 'alu': (0.80, 0.82, 0.84), 'steel': (0.70, 0.72, 0.75),
       'motor': (0.20, 0.21, 0.23), 'wood': (0.76, 0.60, 0.40), 'rubber': (0.12, 0.12, 0.12), 'belt': (0.08, 0.08, 0.08),
       'board': (0.10, 0.45, 0.25), 'red': (0.80, 0.15, 0.12), 'green': (0.15, 0.65, 0.25), 'white': (0.95, 0.95, 0.95),
       'battery': (0.20, 0.33, 0.60), 'chain': (0.18, 0.18, 0.20), 'black': (0.05, 0.05, 0.05), 'servo': (0.15, 0.20, 0.45),
       'field': (0.92, 0.92, 0.90), 'zone1': (0.80, 0.82, 0.83), 'zone2': (0.66, 0.67, 0.69), 'fieldarea': (0.50, 0.50, 0.52),
       'copper': (0.72, 0.45, 0.20), 'yellow': (0.95, 0.80, 0.15), 'cable': (0.85, 0.33, 0.18),
       'fastener': (0.30, 0.31, 0.33), 'fastener2': (0.62, 0.63, 0.65), 'insert': (0.80, 0.62, 0.25)}

def relief_pocket(x0, y0, x1, y1, z0, z1, r_corner=0.4, r_groove=0.6):
    """Pocket tool with rounded vertical corners and a round relief groove along the
    floor edges: no sharp internal corner, and a square part still sits flat on the floor."""
    tool = rbox(x0, y0, z0, x1, y1, z1, r_corner, 'z')
    for (ax, ay), (bx, by) in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        d = V(bx - ax, by - ay, 0)
        L = d.Length
        d.normalize()
        tool = tool.fuse(Part.makeCylinder(r_groove, L, V(ax, ay, z0), d))
    return tidy(tool)

def add(name, shape, group='base', kind='printed', colour='printed'):
    PARTS[name] = (shape, group, kind, colour)
    return shape

# =============================================================================
# 2. BOUGHT-PART BUILDERS
# =============================================================================
def profile2020(p0, axis, length):
    """2020 aluminium profile (6 mm slots, 4.2 centre hole) from p0 along +axis."""
    s = Part.makeBox(20, 20, length, V(-10, -10, 0))
    for ang in (0, 90, 180, 270):
        sl = Part.makeBox(6.2, 6.0, length + 2, V(-3.1, 4.0, -1))
        sl.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        s = s.cut(sl)
    s = s.cut(Part.makeCylinder(2.1, length + 2, V(0, 0, -1)))
    s = s.makeFillet(0.5, [e for e in s.Edges if abs(e.Length - length) < 1e-6 and
                           max(abs(e.Vertexes[0].Point.x), abs(e.Vertexes[0].Point.y)) > 9.9 and
                           abs(abs(e.Vertexes[0].Point.x) - 10) < 1e-6 and abs(abs(e.Vertexes[0].Point.y) - 10) < 1e-6])
    if axis == 'x':
        s.rotate(V(0, 0, 0), V(0, 1, 0), 90)
    elif axis == 'y':
        s.rotate(V(0, 0, 0), V(1, 0, 0), -90)
    s.translate(V(*p0))
    return s

def nema17(face_c, direction):
    """NEMA17 17HS16-2004S1: body behind the face, pilot and shaft in front.
    face_c = centre of the mounting face, direction = unit vector the shaft points to ('+x', '-y', ...)."""
    n = NEMA17
    body = Part.makeBox(n['sq'], n['sq'], n['L'], V(-n['sq'] / 2, -n['sq'] / 2, -n['L']))
    body = body.makeFillet(n['chamfer'] / 2, [e for e in body.Edges if abs(e.Length - n['L']) < 1e-6])
    body = body.fuse(Part.makeCylinder(n['pilot'] / 2, n['pilot_h'], V(0, 0, 0)))
    shaft = Part.makeCylinder(n['shaft'] / 2, n['shaft_L'], V(0, 0, 0))
    shaft = shaft.cut(Part.makeBox(5, 5, n['shaft_L'] - 2 + 1, V(n['flat'] - n['shaft'] / 2, -2.5, 2)))
    out = {}
    for k, s in (('body', body), ('shaft', shaft)):
        rot = {'+x': (V(0, 1, 0), 90), '-x': (V(0, 1, 0), -90), '+y': (V(1, 0, 0), -90), '-y': (V(1, 0, 0), 90),
               '+z': (V(0, 0, 1), 0), '-z': (V(1, 0, 0), 180)}[direction]
        if rot[1]:
            s.rotate(V(0, 0, 0), rot[0], rot[1])
        s.translate(V(*face_c))
        out[k] = s
    return out

def nema17_vendor(face_c, direction, spin=0.0):
    """vendor/17HS16-2004S1.step placed like nema17() (vendor: rear at z 0, mounting face at z 40, shaft +z)."""
    s = W.vendor('17HS16-2004S1.step')
    s.translate(V(0, 0, -40.0))
    if spin:
        s.rotate(V(0, 0, 0), V(0, 0, 1), spin)        # turn about the shaft: where the lead stub points
    rot = {'+x': (V(0, 1, 0), 90), '-x': (V(0, 1, 0), -90), '+y': (V(1, 0, 0), -90), '-y': (V(1, 0, 0), 90),
           '+z': (V(0, 0, 1), 0), '-z': (V(1, 0, 0), 180)}[direction]
    if rot[1]:
        s.rotate(V(0, 0, 0), rot[0], rot[1])
    s.translate(V(*face_c))
    return s

def detailed():
    """Vendor shapes for frame parts, in build coordinates (Y carriage parts at PYC0)."""
    return {'y_motor_17HS16': nema17_vendor((YM_FACE, YM_C[0], YM_C[1]), '+x', 180.0),     # leads toward +y, away from the battery
            'x_motor_17HS16': nema17_vendor((XM_C[0], PYC0 + XM_FACE_DY, XM_C[1]), '-y')}
def gt2_pulley(c, axis, t0, toothed=True):
    """GT2 20T pulley/idler: flanges r 8, teeth r 6.1, along axis from coordinate t0 (7 mm wide belt part)."""
    def cy(r, a, b):
        p = list(c)
        idx = {'x': 0, 'y': 1, 'z': 2}[axis]
        p.insert(idx, a)
        return cyl(tuple(p), r, b - a, axis)
    s = cy(6.1, t0, t0 + 7.0).fuse([cy(8.0, t0, t0 + 0.8), cy(8.0, t0 + 6.2, t0 + 7.0)])
    if toothed:
        s = s.fuse(cy(8.0, t0 - 6.0, t0))           # hub with grub screws
    p = list(c); p.insert({'x': 0, 'y': 1, 'z': 2}[axis], t0 - 7)
    return s.cut(cyl(tuple(p), 2.5, 20.0, axis))

def belt_loop(c1, c2, plane_axis, a0, a1):
    """Closed GT2 belt between two pulley centres (given in the 2D plane normal to plane_axis), width a0..a1."""
    r_in, r_out = GT2_PD / 2 - 0.7, GT2_PD / 2 + 0.7
    def to3(u, v, a):
        if plane_axis == 'x':
            return V(a, u, v)
        return V(u, a, v)        # plane_axis 'y': (u, v) = (x, z)
    d = AXV = None
    out = None
    (u1, v1), (u2, v2) = c1, c2
    L = math.hypot(u2 - u1, v2 - v1)
    # two straight runs + two half rings
    for s in (1, -1):
        r = (r_in + r_out) / 2
        strip = Part.makePolygon([to3(u1, v1 + s * r_in, a0), to3(u2, v2 + s * r_in, a0), to3(u2, v2 + s * r_out, a0),
                                  to3(u1, v1 + s * r_out, a0), to3(u1, v1 + s * r_in, a0)])
        f = Part.Face(strip).extrude(to3(0, 0, a1 - a0) - to3(0, 0, 0))
        out = f if out is None else out.fuse(f)
    for (u, v), sgn in ((c1, -1), (c2, 1)):
        ax = to3(0, 0, 1) - to3(0, 0, 0)
        ring = Part.makeCylinder(r_out, a1 - a0, to3(u, v, a0), ax).cut(Part.makeCylinder(r_in, a1 - a0, to3(u, v, a0), ax))
        half = Part.makeBox(r_out + 1, 2 * r_out + 2, a1 - a0 + 2)
        if plane_axis == 'x':
            half = Part.makeBox(a1 - a0 + 2, r_out + 1, 2 * r_out + 2, V(a0 - 1, u if sgn > 0 else u - r_out - 1, v - r_out - 1))
        else:
            half = Part.makeBox(r_out + 1, a1 - a0 + 2, 2 * r_out + 2, V(u if sgn > 0 else u - r_out - 1, a0 - 1, v - r_out - 1))
        out = out.fuse(ring.common(half))
    return tidy(out)

RAIL_PITCH, RAIL_HOLE_D, RAIL_CB_D, RAIL_CB_H, RAIL_H = 25.0, 3.5, 6.0, 4.5, 8.0     # MGN12 rail holes (VERIFY on yours)

def rail_holes(L):
    n = int((L - 5.0) // RAIL_PITCH) + 1
    e = (L - (n - 1) * RAIL_PITCH) / 2
    return [e + i * RAIL_PITCH for i in range(n)]

def mgn12_rail(axis, a0, a1, c, z_mount, up):
    """MGN12 rail along 'axis' from a0 to a1, centred on c across, base on z_mount, growing in direction up (+1/-1),
    with counterbored M3 holes from its free face."""
    zf = z_mount + up * RAIL_H
    if axis == 'y':
        r = box(c - 6, a0, min(z_mount, zf), c + 6, a1, max(z_mount, zf))
    else:
        r = box(a0, c - 6, min(z_mount, zf), a1, c + 6, max(z_mount, zf))
    cut = []
    for t in rail_holes(a1 - a0):
        p = (c, a0 + t) if axis == 'y' else (a0 + t, c)
        cut.append(cyl((p[0], p[1], z_mount - up), RAIL_HOLE_D / 2, up * (RAIL_H + 2)))
        cut.append(cyl((p[0], p[1], zf + up), RAIL_CB_D / 2, -up * (RAIL_CB_H + 1)))
    return cut_all(r, cut)

def d2f_switch(p0, body_axis, lever_dir):
    """Omron D2F-01L: body L along body_axis from p0 (min corner), lever as a thin plate."""
    L, Wd, H = D2F['L'], D2F['W'], D2F['H']
    return Part.makeBox(*{'x': (L, Wd, H), 'y': (Wd, L, H), 'z': (Wd, H, L)}[body_axis], V(*p0))

# =============================================================================
# 3. BASE
# =============================================================================
def plywood():
    x0, y0, x1, y1 = PLY
    s = box(x0, y0, Z_PLY0, x1, y1, Z_PLY1)
    s = s.makeFillet(10.0, [e for e in s.Edges if abs(e.Length - Z_PLY) < 1e-6])
    cut = []
    for x, y in FEET:                                         # foot pocket from below (Forstner bit), foot screwed in with a wood screw
        cut.append(cyl((x, y, Z_PLY0 - 1), (FOOT_D + 0.4) / 2, FOOT_POCKET + 1))
    for y in BEAM_BOLTS_Y:                                   # beam M5x20 from below: counterbore for the head, through the riser
        cut.append(cyl((YB_X, y, Z_PLY0 - 1), bolt(5) / 2, Z_PLY + 2))
        cut.append(cyl((YB_X, y, Z_PLY0 - 1), (8.5 + 0.8) / 2, BEAM_CBORE + 1))
    for x, y in ((EB[0] + 4, EB[1] + 4), (EB[2] - 4, EB[1] + 4), (EB[0] + 4, EB[3] - 4), (EB[2] - 4, EB[3] - 4)):
        cut.append(cyl((x, y, Z_PLY0 - 1), bolt(3) / 2, Z_PLY + 2))
        cut.append(Part.makeCone(3.3, bolt(3) / 2, 1.7, V(x, y, Z_PLY0)))
    return cut_all(s, cut)

def rubber_foot(x, y):
    """Screw-on rubber foot 20 x 7 (steel washer inside): 3 mm below the plywood, 4 mm in its pocket."""
    f = cyl((x, y, 0.0), FOOT_D / 2, FOOT_H)
    return f.cut(cyl((x, y, -1), 4.2, 1 + FOOT_SCREW_SINK)).cut(cyl((x, y, -1), 1.9, FOOT_H + 2))

def base_items():
    add('plywood_base', plywood(), kind='bought', colour='wood')
    for i, (x, y) in enumerate(FEET):
        add('rubber_foot_%d' % (i + 1), rubber_foot(x, y), kind='bought', colour='rubber')

# =============================================================================
# 4. Y AXIS (static)
# =============================================================================
def y_motor_mount():
    """Vertical plate between the Y motor and its pulley, flange on the plywood
    with slots for belt tension, two ribs clear of the belt."""
    py, pz = YM_C
    x0, x1 = YM_FACE, YM_FACE + 4.0
    plate = box(x0, py - 27.0, Z_PLY1, x1, py + 27.0, pz + 24.0)
    flange = box(x0, py - 27.0, Z_PLY1, 194.0, py + 27.0, Z_PLY1 + 4.0)
    ribs = [prism_y([(x1, Z_PLY1 + 4.0), (x1 + 6.0, Z_PLY1 + 4.0), (x1, Z_PLY1 + 22.0)], py - 27.0, py - 23.0),
            prism_y([(x1, Z_PLY1 + 4.0), (x1 + 16.0, Z_PLY1 + 4.0), (x1, Z_PLY1 + 30.0)], py + 23.0, py + 27.0)]
    body = fillet_all(tidy(plate.fuse([flange] + ribs)))
    cut = [cyl((x0 - 1, py, pz), (NEMA17['pilot'] + TOL_MOTOR) / 2, 6.0, 'x')]
    for a in (-1, 1):
        for b in (-1, 1):
            cut.append(cyl((x0 - 1, py + a * 15.5, pz + b * 15.5), (3.0 + TOL_MOTOR) / 2, 6.0, 'x'))
    for yy in (py - 16.0, py + 16.0):                       # wood screws 4 mm, slots along Y for belt tension
        cut.append(slot((187.0, yy - 5.0, Z_PLY1 - 1), (187.0, yy + 5.0, Z_PLY1 - 1), bolt(4) / 2, 6.0))
    return cut_all(body, cut)

IDLER_WOOD = [(160.0, 10.0), (223.0, 4.75)]       # 4 mm wood screws (the second clears the beam end plate's x 218)

def y_idler_bracket():
    """Holds the Y idler on an M5 axle (cantilever), bolts to the beam end and the
    plywood; carries the Y home switch."""
    py, pz = YI_C
    base = prism_z([(150.0, 0.0), (244.0, 0.0), (244.0, 10.0), (193.0, 10.0), (193.0, 20.0), (150.0, 20.0)], Z_PLY1, Z_PLY1 + 4.0)
    plate = box(176.0, 0.0, Z_PLY1, 180.0, 40.0, Z_YC0 - 1.5)        # top stays 1.5 mm under the Y carriage
    endp = box(192.0, 4.0, Z_PLY1, 218.0, 10.0, Z_YB1 - 3.5)          # top stays under the Y idler axle nut
    spacer = cyl((180.0, py, pz), 5.1, 2.2, 'x')
    post = box(228.0, 0.0, Z_PLY1, 236.0, 10.0, 47.0 + Y_RISER)      # switch post
    body = fillet_all(tidy(base.fuse([plate, endp, spacer, post])))
    cut = [cyl((175.0, py, pz), bolt(5) / 2, 10.0, 'x'),                      # idler axle
           cyl((YB_X, 3.0, Z_YB1 - 10.0), bolt(5) / 2, 8.0, 'y'),             # M5 into the beam end
           cyl((160.0, 10.0, Z_PLY1 - 1), bolt(4) / 2, 6.0), cyl((IDLER_WOOD[1][0], IDLER_WOOD[1][1], Z_PLY1 - 1), bolt(4) / 2, 6.0)]
    for zz in (40.0 + Y_RISER - D2F['hole_pitch'] / 2 + 0.5, 40.0 + Y_RISER + D2F['hole_pitch'] / 2 + 0.5):   # M2 self-tapping into the post
        cut.append(cyl((236.01, 4.5, zz), W.M2_PILOT / 2, -5.0, 'x'))       # M2x10 self-tapping: 4.2 mm in the post
    return cut_all(body, cut)

def y_beam_riser(y):
    """Block under the Y beam (one of four): lifts the beam 10 mm so cables cross under it.
    Two tongues (6 mm slot - 0.4) sit in the beam's bottom slot and keep it straight;
    the beam's M5 bolt goes up through the block into a T-nut. Prints flat."""
    x0, x1 = YB_X - 12.0, YB_X + 12.0
    body = box(x0, y - 12.0, Z_PLY1, x1, y + 12.0, Z_YB0)
    tw = (6.0 - 2 * TOL_MOVE) / 2                  # 5.2 wide in the 6 mm slot
    tongues = [box(YB_X - tw, ya, Z_YB0, YB_X + tw, yb, Z_YB0 + 1.8) for ya, yb in ((y - 12.0, y - 5.0), (y + 5.0, y + 12.0))]
    body = fillet_all(tidy(body.fuse(tongues)), r_in=0.4, r_out=0.6)    # small root fillet: stays inside the slot opening
    return cut_all(body, [cyl((YB_X, y, Z_PLY1 - 1), bolt(5) / 2, Y_RISER + 4)])

def y_static():
    for y in BEAM_BOLTS_Y:
        add('y_beam_riser_%d' % int(y), y_beam_riser(y))
    add('y_beam_2020', profile2020((YB_X, YB_Y0, Z_YB0 + 10.0), 'y', YB_Y1 - YB_Y0), kind='bought', colour='alu')
    add('y_rail_mgn12_400', mgn12_rail('y', YB_Y0, YB_Y1, YB_X, Z_YB1, +1), kind='bought', colour='steel')
    m = nema17((YM_FACE, YM_C[0], YM_C[1]), '+x')
    add('y_motor_17HS16', m['body'].fuse(m['shaft']), kind='bought', colour='motor')
    add('y_pulley_gt2_20t', gt2_pulley(YM_C, 'x', Y_BELT_X0 - 0.5), kind='bought', colour='steel')
    add('y_idler_gt2_20t', gt2_pulley(YI_C, 'x', Y_BELT_X0 - 0.5, toothed=False), kind='bought', colour='steel')
    add('y_belt_gt2', belt_loop(YI_C, YM_C, 'x', Y_BELT_X0, Y_BELT_X1), kind='bought', colour='belt')
    add('y_motor_mount', y_motor_mount())
    add('y_idler_bracket', y_idler_bracket())
    add('y_home_switch_d2f', d2f_switch((236.0, 1.5, 40.0 + Y_RISER - D2F['L'] / 2 + 3.5), 'z', '+y').fuse(
        box(236.0, 1.5, 40.0 + Y_RISER + D2F['L'] / 2 + 3.5, 236.0 + D2F['W'], 11.0, 40.0 + Y_RISER + D2F['L'] / 2 + 4.3)), kind='bought', colour='black')

# =============================================================================
# 5. Y CARRIAGE (group 'ycar')
# =============================================================================
Y_CLAMP = [(179.4, PYC0 + 5.0), (179.4, PYC0 + 17.0)]
Y_CHAIN_SLOT = ((235.5, PYC0 + 12.0), (235.5, PYC0 + 24.0))   # Y chain moving end link: M3 + nut under the plate, any hole spacing
# zip ties (same layout as W.ZIPS): the Y carriage bundle across the carriage top
ZIPS = {'zip_tie_ycar': ('y_carriage', (230.0, PYC0 - 9.0, Z_YC1), 'y', 'z', 1, Z_YC1 - Z_YC0, 7.0, 10.0, 1.0)}
POST_TIES_Z = (105.0, 120.0)             # ties round the 2020 post and the bundle on its -y face (below the X motor mount arms)
ZT = Y_BELT_Z + GT2_PD / 2               # upper Y belt strand

def y_carriage():
    """Plate on the Y block with a socket for the 2020 post (4 M5 into T-nuts).
    Prints bottom face down. The four block screws are sunk 5 mm; the two
    under the post must go in before the post."""
    plate = box(YC_X0, PYC0 - YC_HALF_Y, Z_YC0, YC_X1, PYC0 + YC_HALF_Y, Z_YC1)
    plate = plate.makeFillet(5.0, [e for e in plate.Edges if abs(e.Length - (Z_YC1 - Z_YC0)) < 1e-6])
    pc = POST_C
    inner, wall = 10.0 + W.SOCKET_GAP, 5.0
    sock = box(pc[0] - inner - wall, pc[1] - inner - wall, Z_YC1, pc[0] + inner + wall, pc[1] + inner + wall, Z_YC1 + SOCKET_H)
    body = fillet_all(tidy(plate.fuse(sock)))         # socket-to-plate corner first: the block-screw counterbores cut through it
    pre = []
    for a in (-1, 1):
        for b in (-1, 1):
            x, y = YB_X + a * 10.0, PYC0 + b * 10.0
            pre.append(cyl((x, y, Z_YC0 - 1), bolt(3) / 2, 12.0))
            # heads sunk 5 mm (M3x8 gives 3 mm in the block); the +x pair crosses the socket corner fillet, so it goes through it (no sliver)
            pre.append(cyl((x, y, Z_YC1 - 5.0), (5.5 + 2 * TOL_MOVE) / 2, 5.0 + (W.FILLET_IN + 0.1 if a > 0 else 0.0)))
    body = fillet_all(cut_all(body, pre))
    body = body.cut(relief_pocket(pc[0] - inner, pc[1] - inner, pc[0] + inner, pc[1] + inner, Z_YC1, Z_YC1 + SOCKET_H + 1))
    cut = []
    zs = Z_YC1 + SOCKET_H / 2
    for d in ('x', 'y'):
        for s in (-1, 1):
            if d == 'x':
                cut.append(cyl((pc[0] + s * (inner - 1), pc[1], zs), bolt(5) / 2, s * (wall + 2), 'x'))
            else:
                cut.append(cyl((pc[0], pc[1] + s * (inner - 1), zs), bolt(5) / 2, s * (wall + 2), 'y'))
    for x, y in Y_CLAMP:
        cut.append(cyl((x, y, Z_YC0 - 0.01), INSERT_D / 2, INSERT_DEPTH))
    (ax, ay), (bx, by) = Y_CHAIN_SLOT
    cut.append(slot((ax, ay, Z_YC0 - 1), (bx, by, Z_YC0 - 1), bolt(3) / 2, Z_YC1 - Z_YC0 + 2))
    cut.append(W.zip_slots(ZIPS['zip_tie_ycar']))                                   # Y carriage bundle on its way to the Y chain
    return cut_all(body, cut)

def y_belt_spacer():
    s = box(175.0, PYC0, ZT + 0.7, 190.5, PYC0 + 22.0, Z_YC0)
    s = fillet_all(s)
    return cut_all(s, [cyl((x, y, ZT), bolt(3) / 2, 10.0) for x, y in Y_CLAMP])

def y_belt_clamp():
    """Clamp plate under the upper Y strand; half-round grooves take the belt teeth."""
    z1 = ZT - 0.7 + 0.3
    s = fillet_all(box(175.0, PYC0, z1 - 3.5, 190.5, PYC0 + 22.0, z1))
    cut = [cyl((x, y, z1 - 5), bolt(3) / 2, 7.0) for x, y in Y_CLAMP]
    y = PYC0 + 3.0
    while y <= PYC0 + 19.0:
        if all(abs(y - yc) > 2.6 for _, yc in Y_CLAMP):
            cut.append(cyl((Y_BELT_X0 - 0.5, y, z1), 0.6, 7.0, 'x'))
        y += 2.0
    return cut_all(s, cut)

def post_cap():
    cap = box(POST_C[0] - 10.5, POST_C[1] - 10.5, Z_POST1, POST_C[0] + 10.5, POST_C[1] + 10.5, Z_POST1 + 4.0)
    cap = fillet_all(cap, r_out=2.0)
    return tidy(cap.fuse(cyl((POST_C[0], POST_C[1], Z_POST1), (4.2 - TOL_PRESS) / 2, -6.0)))

BRACKET_HOLE = 11.0     # hole centre from the corner, on each leg (M5)   VERIFY on your bracket

def corner_bracket(top):
    """Cast 2020 corner bracket (20 x 20 x 20, 3 mm legs, two side walls), one 5.5 hole per leg."""
    zb = Z_BOOM1 if top else Z_BOOM0
    s = 1 if top else -1
    h = box(BOOM_X0, PYC0 - 10, min(zb, zb + 3 * s), BOOM_X0 + 20, PYC0 + 10, max(zb, zb + 3 * s))
    v = box(BOOM_X0, PYC0 - 10, min(zb, zb + 20 * s), BOOM_X0 + 3, PYC0 + 10, max(zb, zb + 20 * s))
    g = [prism_y([(BOOM_X0 + 3, zb + 3 * s), (BOOM_X0 + 17, zb + 3 * s), (BOOM_X0 + 3, zb + 17 * s)], yy, yy + 2.0)
         for yy in (PYC0 - 10.0, PYC0 + 8.0)]
    b = tidy(h.fuse([v] + g))
    b = b.cut(cyl((BOOM_X0 + BRACKET_HOLE, PYC0, zb - 1 * s), 2.75, 5.0 * s))
    return b.cut(cyl((BOOM_X0 - 1, PYC0, zb + BRACKET_HOLE * s), 2.75, 5.0, 'x'))

def x_motor_mount():
    """Plate for the X motor behind the post, two arms bolted to the post's +Y slot
    (counterbored M5), and a tab for the X home switch."""
    fy = PYC0 + XM_FACE_DY
    plate = box(140.0, fy - 4.0, 126.0, 209.0, fy, 196.0)
    arms = []
    for z0, z1 in ((176.0, 196.0), (126.0, 147.0)):
        arms.append(box(184.0, PYC0 + 10.0, z0, 209.0, fy - 4.0, z1))
    body = fillet_all(tidy(plate.fuse(arms)))
    cut = [cyl((XM_C[0], fy + 1, XM_C[1]), (NEMA17['pilot'] + TOL_MOTOR) / 2, -6.0, 'y')]
    for a in (-1, 1):
        for b in (-1, 1):
            cut.append(cyl((XM_C[0] + a * 15.5, fy + 1, XM_C[1] + b * 15.5), (3.0 + TOL_MOTOR) / 2, -6.0, 'y'))
    for zc in (186.0, 136.5):
        cut.append(cyl((199.0, PYC0 + 9.0, zc), bolt(5) / 2, fy - PYC0, 'y'))
        cut.append(cyl((199.0, PYC0 + 21.0, zc), (8.5 + 2 * TOL_MOVE) / 2, fy - PYC0, 'y'))
    for yy in (PYC0 + 19.0 - D2F['hole_pitch'] / 2, PYC0 + 19.0 + D2F['hole_pitch'] / 2):    # X home switch, M2 self-tapping
        cut.append(cyl((210.0, yy, 129.5), W.M2_PILOT / 2, -9.0, 'x'))
    return cut_all(body, cut)

def x_idler_bracket():
    """End cap on the boom with a slotted side plate for the X idler axle (belt tension)."""
    ep = box(BOOM_X1, PYC0 - 12.0, Z_BOOM0 - 2.0, BOOM_X1 + 6.0, PYC0 + 26.0, Z_BOOM1 + 2.0)
    side = box(456.0, PYC0 + XB_DY1 + 1.0, Z_BOOM0 - 2.0, BOOM_X1 + 6.0, PYC0 + XB_DY1 + 5.0, Z_BOOM1 + 2.0)
    body = fillet_all(tidy(ep.fuse(side)))
    cut = [cyl((BOOM_X1 - 1, PYC0, X_BELT_Z), bolt(5) / 2, 8.0, 'x'),
           cyl((BOOM_X1 + 3.0, PYC0, X_BELT_Z), (8.5 + 2 * TOL_MOVE) / 2, 4.0, 'x'),
           slot((XI_C[0] - 4.0, PYC0 + XB_DY1, X_BELT_Z), (XI_C[0] + 4.0, PYC0 + XB_DY1, X_BELT_Z), bolt(5) / 2, 7.0, 'y')]
    return cut_all(body, cut)

def ycar_items():
    G = 'ycar'
    yblk = prism_y([(YB_X - 13.5, Z_YBLK1), (YB_X - 13.5, Z_YBLK0), (YB_X - 6.2, Z_YBLK0), (YB_X - 6.2, Z_YR1 + 0.2),
                    (YB_X + 6.2, Z_YR1 + 0.2), (YB_X + 6.2, Z_YBLK0), (YB_X + 13.5, Z_YBLK0), (YB_X + 13.5, Z_YBLK1)],
                   PYC0 - 22.7, PYC0 + 22.7)
    add('y_block_mgn12h', yblk, G, 'bought', 'steel')
    add('y_carriage', y_carriage(), G)
    add('y_belt_spacer', y_belt_spacer(), G)
    add('y_belt_clamp', y_belt_clamp(), G)
    add('post_2020_%d' % POST_L, profile2020((POST_C[0], POST_C[1], Z_POST0), 'z', Z_POST1 - Z_POST0), G, 'bought', 'alu')
    add('post_cap', post_cap(), G)
    for k, spec in ZIPS.items():
        add(k, W.zip_tie(spec[1], *spec[2:]), G, 'bought', 'black')
    for i, z in enumerate(POST_TIES_Z):          # round the post and the bundle beside it (x 207, y -14 from the post centre)
        x0, x1, y0, y1, t = POST_C[0] - 10.0, 207.0 + 3.5, POST_C[1] - 14.0 - 3.5, POST_C[1] + 10.0, W.TIE_T
        ring = box(x0 - t, y0 - t, z - W.TIE_W / 2, x1 + t, y1 + t, z + W.TIE_W / 2).cut(box(x0, y0, z - 2, x1, y1, z + 2))
        hu, hw, hv = W.TIE_HEAD
        head = box(x0 - t - hw, POST_C[1] - hv / 2, z - hu / 2, x0 - t, POST_C[1] + hv / 2, z + hu / 2)
        add('zip_tie_post_%d' % (i + 1), ring.fuse(head).removeSplitter(), G, 'bought', 'black')
    add('boom_2020_270', profile2020((BOOM_X0, PYC0, (Z_BOOM0 + Z_BOOM1) / 2), 'x', BOOM_X1 - BOOM_X0), G, 'bought', 'alu')
    add('corner_bracket_top', corner_bracket(True), G, 'bought', 'steel')
    add('corner_bracket_bottom', corner_bracket(False), G, 'bought', 'steel')
    add('x_rail_mgn12_250', mgn12_rail('x', XR_X0, XR_X1, PYC0, Z_BOOM0, -1), G, 'bought', 'steel')
    m = nema17((XM_C[0], PYC0 + XM_FACE_DY, XM_C[1]), '-y')
    add('x_motor_17HS16', m['body'].fuse(m['shaft']), G, 'bought', 'motor')
    add('x_pulley_gt2_20t', gt2_pulley(XM_C, 'y', PYC0 + XB_DY0 - 0.5), G, 'bought', 'steel')
    add('x_idler_gt2_20t', gt2_pulley(XI_C, 'y', PYC0 + XB_DY0 - 0.5, toothed=False), G, 'bought', 'steel')
    add('x_belt_gt2', belt_loop(XM_C, XI_C, 'y', PYC0 + XB_DY0, PYC0 + XB_DY1), G, 'bought', 'belt')
    add('x_motor_mount', x_motor_mount(), G)
    add('x_idler_bracket', x_idler_bracket(), G)
    add('x_home_switch_d2f', d2f_switch((209.0, PYC0 + 19.0 - D2F['L'] / 2, 126.5), 'y', '+x').fuse(
        box(209.0 + D2F['H'] - 0.5, PYC0 + 14.0, 131.5, 217.0, PYC0 + 24.0, 132.5)), G, 'bought', 'black')

def base_cable_chain():
    # the chains themselves depend on the pose: chains.x_chain() / chains.y_chain(), placed by assembly.world()
    add('y_chain_guide', chains.y_chain_guide())

# =============================================================================
# 6. CONTROL PANEL AND TRAYS (base)
# =============================================================================
def control_panel():
    """Open-bottom box: stop and start buttons and both LEDs on top, connectors A/B/C
    in the -X wall. Prints top face down; the connector windows have rounded corners."""
    x0, y0, x1, y1, zt = PANEL
    t = 3.0
    outer = box(x0, y0, Z_PLY1, x1, y1, zt)
    outer = outer.makeFillet(6.0, [e for e in outer.Edges if abs(e.Length - (zt - Z_PLY1)) < 1e-6])
    inner = box(x0 + t, y0 + t, Z_PLY1 - 1, x1 - t, y1 - t, zt - t)
    inner = inner.makeFillet(3.0, [e for e in inner.Edges if abs(e.Length - (zt - t - Z_PLY1 + 1)) < 1e-6])
    body = outer.cut(inner)
    bosses = [cyl((x, y, Z_PLY1), 5.0, zt - t - Z_PLY1) for x, y in ((x0 + 6, y0 + 6), (x1 - 6, y0 + 6), (x0 + 6, y1 - 6), (x1 - 6, y1 - 6))]
    pcb_posts = [box(x0 + t, y - 3.5, 21.0, x0 + t + 5.0, y + 3.5, 28.0) for y in (47.0, 96.0)]
    body = fillet_all(tidy(body.fuse(bosses + pcb_posts)))
    cut = [cyl((ESTOP_C[0], ESTOP_C[1], zt - t - 1), (22.0 + TOL_BOLT) / 2, t + 2),
           cyl((START_C[0], START_C[1], zt - t - 1), (16.0 + TOL_BOLT) / 2, t + 2),
           cyl((LED_G[0], LED_G[1], zt - t - 1), (6.0 + TOL_BOLT) / 2, t + 2),
           cyl((LED_R[0], LED_R[1], zt - t - 1), (6.0 + TOL_BOLT) / 2, t + 2)]
    for x, y in ((x0 + 6, y0 + 6), (x1 - 6, y0 + 6), (x0 + 6, y1 - 6), (x1 - 6, y1 - 6)):
        cut.append(cyl((x, y, Z_PLY1 - 1), (3.5 + TOL_BOLT) / 2, zt - Z_PLY1 + 2))
    for yc, n in CONN.values():
        w = n * 2.54 + 0.6
        cut.append(rbox(x0 - 1, yc - w / 2, 30.4, x0 + t + 1, yc + w / 2, 33.6, 0.5, 'x'))
    for y in (47.0, 96.0):
        cut.append(cyl((x0 + t + 5.0 + 0.01, y, 24.5), W.M2_PILOT / 2, -5.0, 'x'))
    cut.append(rbox(x1 - t - 1, 70.0, 18.0, x1 + 1, 84.0, 26.0, 1.0, 'x'))      # cable exit
    return cut_all(body, cut)

BB_EARS = [(BB[0] + 6, BB[1] - 3.0 - 5.5), (BB[0] + 76.5, BB[1] - 3.0 - 5.5), (BB[0] + 6, BB[1] + 54.5 + 3.0 + 5.5), (BB[0] + 76.5, BB[1] + 54.5 + 3.0 + 5.5)]   # screw heads clear the tray wall

def breadboard_tray():
    x0, y0 = BB
    t = 3.0          # 2.4 mm left beside the relief groove
    tray = box(x0 - 0.3 - t, y0 - 0.3 - t, Z_PLY1, x0 + 82.8 + t, y0 + 54.8 + t, Z_PLY1 + 3.0 + 6.0)      # 3 mm floor: 2.4 left under the relief groove
    pocket = relief_pocket(x0 - 0.3, y0 - 0.3, x0 + 82.8, y0 + 54.8, Z_PLY1 + 3.0, Z_PLY1 + 10.0, 1.0)
    ears = [cyl((x, y, Z_PLY1), 5.0, 3.0) for x, y in BB_EARS]
    body = fillet_all(tidy(tray.fuse(ears))).cut(pocket)
    return cut_all(body, [cyl((x, y, Z_PLY1 - 1), (3.5 + TOL_BOLT) / 2, 5.0) for x, y in
                          BB_EARS])

def bt_ears():
    x0, y0, x1, y1 = BT
    return [(x0 - 5.5, y0 + 10), (x1 + 5.5, y0 + 10), (x0 - 5.5, y1 - 10), (x1 + 5.5, y1 - 10)]

def battery_tray():
    x0, y0, x1, y1 = BT
    t = 2.4
    tray = box(x0, y0, Z_PLY1, x1, y1, Z_PLY1 + 2.4 + 10.0)
    tray = tray.cut(box(x0 + t, y0 + t, Z_PLY1 + 2.4, x1 - t, y1 - t, Z_PLY1 + 20.0))
    ears = [cyl((x, y, Z_PLY1), 5.0, 3.0) for x, y in bt_ears()]
    body = fillet_all(tidy(tray.fuse(ears)))
    cut = [cyl((x, y, Z_PLY1 - 1), (3.5 + TOL_BOLT) / 2, 5.0) for x, y in bt_ears()]
    for yy in (y0 + 30.0, y1 - 30.0):                      # strap slots in the floor
        cut.append(slot((x0 + 8.0, yy, Z_PLY1 - 1), (x1 - 8.0, yy, Z_PLY1 - 1), 1.6, 5.0))
    return cut_all(body, cut)

def stop_label():
    """White 'STOP' sticker on the stop button cap (cosmetic, reads from the front, -y)."""
    faces = []
    for ch in Part.makeWireString('STOP', FONT, STOP_TEXT[0], 0):
        try:
            faces.append(Part.Face(ch, 'Part::FaceMakerBullseye'))
        except Exception:
            pass
    s = Part.makeCompound(faces).extrude(V(0, 0, STOP_TEXT[1]))
    bb = s.BoundBox
    s.translate(V(ESTOP_C[0] - (bb.XMin + bb.XMax) / 2, ESTOP_C[1] - (bb.YMin + bb.YMax) / 2, PANEL[4] + 22.0))
    return s

def panel_items():
    add('control_panel', control_panel(), colour='printed2')
    add('estop_22mm_latching', cyl((ESTOP_C[0], ESTOP_C[1], PANEL[4]), 20.0, 22.0).fuse(
        cyl((ESTOP_C[0], ESTOP_C[1], PANEL[4]), 13.5, -30.0)), kind='bought', colour='red')
    if FONT:
        add('estop_label_STOP', stop_label(), kind='bought', colour='white')
    add('start_button_16mm', cyl((START_C[0], START_C[1], PANEL[4]), 9.0, 6.0).fuse(
        cyl((START_C[0], START_C[1], PANEL[4]), 8.0, -22.0)), kind='bought', colour='green')
    add('led_green_5mm', cyl((LED_G[0], LED_G[1], PANEL[4] - 6.0), 2.5, 13.0), kind='bought', colour='green')
    add('led_red_5mm', cyl((LED_R[0], LED_R[1], PANEL[4] - 6.0), 2.5, 13.0), kind='bought', colour='red')
    x0 = PANEL[0]
    add('connector_pcb', box(x0 + 3.0 + 5.0 - 5.0 + 5.0, 42.0, 21.0, x0 + 3.0 + 5.0 + 1.6, 101.0, 36.0), kind='bought', colour='board')
    for nm, (yc, n) in CONN.items():
        add('header_%s_%dpin' % (nm, n), box(x0 - 5.5, yc - n * 1.27, 30.7, x0 + 8.0, yc + n * 1.27, 33.3), kind='bought', colour='black')
    add('breadboard_tray', breadboard_tray())
    add('breadboard_400', rbox(BB[0], BB[1], Z_PLY1 + 3.0, BB[0] + 82.5, BB[1] + 54.5, Z_PLY1 + 3.0 + 8.5, 1.0, 'z'), kind='bought', colour='white')
    add('battery_tray', battery_tray())
    add('battery_4s_2200', rbox(BT[0] + 4.3, BT[1] + 4.3, Z_PLY1 + 2.4, BT[2] - 4.3, BT[3] - 4.3, Z_PLY1 + 2.4 + BAT[2], 3.0, 'z'), kind='bought', colour='battery')
    for y in (BT[1] + 30.0, BT[3] - 30.0):
        add('battery_strap_%d' % int(y), box(BT[0] + 2.5, y - 10.0, Z_PLY1 + 2.4, BT[2] - 2.5, y + 10.0, Z_PLY1 + 33.5).cut(
            box(BT[0] + 3.0, y - 11.0, Z_PLY1 + 2.3, BT[2] - 3.0, y + 11.0, Z_PLY1 + 32.5)), kind='bought', colour='black')
    # electronics: perfboard on 4 standoffs with the main modules
    z = Z_PLY1 + 10.0
    add('perfboard_100x80', box(EB[0], EB[1], z, EB[2], EB[3], z + 1.6), kind='bought', colour='board')
    for i, (x, y) in enumerate(((EB[0] + 4, EB[1] + 4), (EB[2] - 4, EB[1] + 4), (EB[0] + 4, EB[3] - 4), (EB[2] - 4, EB[3] - 4))):
        add('standoff_m3x10_%d' % (i + 1), cyl((x, y, Z_PLY1), 2.75, 10.0), kind='bought', colour='steel')     # solid: the check measures thread engagement
    zt = z + 1.6
    # ESP32-S3-DevKitC-1 on two 1x22 female headers: board, WROOM module (far end), 2 USB-C (-y end)
    bx0, by0 = EB[0] + 5, EB[1] + 5
    bw, bl = ESP32_BOARD
    zb = zt + HDR_H
    for k, xr in (('l', bx0 + (bw - ESP32_PIN_ROWS) / 2), ('r', bx0 + (bw + ESP32_PIN_ROWS) / 2)):
        y0 = by0 + (bl - 22 * 2.54) / 2
        add('header_esp32_%s_1x22' % k, box(xr - 1.27, y0, zt, xr + 1.27, y0 + 22 * 2.54, zb), kind='bought', colour='black')
    add('esp32_s3_devkitc1', box(bx0, by0, zb, bx0 + bw, by0 + bl, zb + 1.6), kind='bought', colour='black')
    add('esp32_s3_wroom1', box(bx0 + (bw - 18.0) / 2, by0 + bl - 25.5, zb + 1.6, bx0 + (bw + 18.0) / 2, by0 + bl, zb + 1.6 + 3.1),
        kind='bought', colour='steel')
    for k, xc in (('1', bx0 + bw / 2 - 6.0), ('2', bx0 + bw / 2 + 6.0)):
        add('esp32_usb_c_%s' % k, rbox(xc - 4.5, by0 - 1.0, zb + 1.6, xc + 4.5, by0 + 6.5, zb + 1.6 + 3.2, 1.0, 'y'), kind='bought', colour='steel')
    # Pololu D36V28F5 / F6 regulators, soldered flat to the board
    for i, nm in enumerate(('pololu_5v_d36v28f5', 'pololu_6v_d36v28f6')):
        x = EB[0] + 36.0 + i * 24.0
        add(nm, box(x, EB[1] + 60, zt, x + 17.8, EB[1] + 80.3, zt + 1.6).fuse(box(x + 3.0, EB[1] + 64, zt + 1.6, x + 12.0, EB[1] + 73, zt + 6.0)),
            kind='bought', colour='board')     # board + inductor

def tmc_fix():
    """Four TMC2209 modules (BIGTREETECH V1.3: 15.3 x 20.3, two 1x8 rows 12.7 apart) in a 2 x 2 grid on female headers."""
    zt = Z_PLY1 + 10.0 + 1.6
    zb = zt + HDR_H
    for i in range(4):
        x = EB[0] + 36.0 + (i % 2) * 21.0             # clear of the board's corner screws
        y = EB[1] + 5.0 + (i // 2) * 25.0
        s = box(x, y, zb, x + 15.3, y + 20.3, zb + 1.6).fuse(box(x + 3.15, y + 5.65, zb + 1.6, x + 12.15, y + 14.65, zb + 1.6 + 7.0))  # board + heatsink
        PARTS['tmc2209_%d' % (i + 1)] = (s, 'base', 'bought', 'board')
        for k, dx in (('a', 1.3), ('b', 1.3 + 12.7)):
            PARTS['header_tmc%d%s_1x8' % (i + 1, k)] = (box(x + dx - 1.27, y + 0.0, zt, x + dx + 1.27, y + 8 * 2.54, zb), 'base', 'bought', 'black')
# =============================================================================
# 7. FIELD REFERENCE (not part of the device)
# =============================================================================
def field_reference():
    out = {}
    out['polygon_600x500'] = (box(0, 0, -1.0, 600, 500, 0.0), 'field')
    out['zone1'] = (box(0, 0, 0.0, 350, 500, 0.1), 'zone1')
    out['zone2_lower'] = (box(350, 0, 0.0, 600, 80, 0.1), 'zone2')
    out['zone2_upper'] = (box(350, 420, 0.0, 600, 500, 0.1), 'zone2')
    out['field_area'] = (box(350, 85, 0.0, 600, 415, 0.1), 'fieldarea')
    out['sheet_a4'] = (box(370, 101.5, 0.1, 580, 398.5, 0.2), 'white')
    dots = None
    for k in range(1, 7):
        for n in range(10):
            if n == 9 and k > 5:
                continue
            c = cyl((564.5 - 28 * k, 116.5 + 28 * n, 0.2), 3.0, 0.1)
            dots = c if dots is None else dots.fuse(c)
    out['cell_centres'] = (dots, 'black')
    for nm, (k, n) in (('marker_27', (0, 0)), ('marker_28', (0, 8)), ('marker_29', (6, 9))):
        x, y = 564.5 - 28 * k, 116.5 + 28 * n
        out[nm] = (box(x - 9, y - 9, 0.2, x + 9, y + 9, 0.3), 'black')
    return out

def build_frame():
    PARTS.clear()
    base_items()
    y_static()
    ycar_items()
    base_cable_chain()
    panel_items()
    tmc_fix()
    return PARTS
