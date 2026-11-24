"""
ETZ plotter v2: frame, Y axis, X axis and base items  (FreeCAD Part script)
==========================================================================
World coordinates (mm), the machine frame:
  X  along the 600 mm side; the polygon starts at x = FIELD_DX (13): zone 1 x 13..363, field from x 363,
  Y  along the 500 mm side,
  Z  up from the table.
Everything that rides on the Y carriage is built at the parked position
PYC0 = 40 (Y carriage centre) and moved by (0, PYC - PYC0, 0).
The wrist module (wrist/wrist_module.py) hangs under the X rail block at (PXB, PYC).

Printed parts in this file: y_carriage, y_belt_spacer, y_belt_clamp, y_motor_mount,
y_idler_bracket, y_idler_slider, x_motor_mount, x_idler_bracket, x_idler_slider, post_cap, control_panel,
breadboard_tray, battery_tray, foot (x4).
"""
import math, os, sys
import FreeCAD as App
import Part
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'wrist'))
import wrist_module as W
import chains
from wrist_module import (box, cyl, slot, prism_x, prism_y, prism_z, rbox, zip_pair, fillet_all, cut_all, tidy, bolt,
                          TOL_MOVE, TOL_PRESS, TOL_BOLT, TOL_MOTOR, INSERT_D, INSERT_DEPTH, WALL_MIN, TOL_PANEL, VTONGUE_GAP)

V = App.Vector

# =============================================================================
# 1. LAYOUT PARAMETERS
# =============================================================================
PYC0, PXB0 = 40.0, 287.0                  # parked Y carriage centre, parked wrist pivot X (magnet at x 397, first cell column)
PYC_RANGE = (40.0, 376.0)
PXB_RANGE = (287.0, 452.0)                 # magnet x 397..562 (MAG_X 110) = polygon x 384..549: covers the worst sheet placement
                                           # (5 mm off, 3 deg turned: cells at polygon x 385.1..548.1, laptop/machine.py). At 287 the
                                           # wrist carriage is 2 mm clear of the Y carriage (x 245); at 452 the belt clamp is 3 mm clear
                                           # of the X idler lug (x 444) and the block 4 mm from the rail end (v2.17)
FIELD_DX = 13.0                            # v2.17: the machine stands 13 mm further from the field: polygon x = machine x - 13
                                           # (plywood -x edge 77 mm from the polygon edge). Moves the reach 13 mm toward zone 1
# base
Z_FOOT, Z_PLY = 9.0, 6.0                  # printed feet (below the plywood), plywood thickness (Egor's board: 6 mm)
Z_PLY0, Z_PLY1 = Z_FOOT, Z_FOOT + Z_PLY
PLY = (90.0, 0.0, 340.0, 470.0)           # plywood outline (corner radius 10)
FEET = [(100.0, 22.0), (330.0, 22.0), (100.0, 458.0), (330.0, 458.0)]
FOOT_D, FOOT_H, FOOT_POCKET = 20.0, 9.0, 0.0     # printed PETG foot 20 x 9, flat under the plywood (Egor, 22 Oct: the plywood shop
                                                 # makes through holes only - no recesses); plywood top stays at z 15
FOOT_EDGE_R = 1.5                                # rounded bottom edge of the foot
PLY_DRILL = {3: 3.5, 4: 4.5, 5: 5.5}                    # hand-drilled bolt holes in the plywood (drill sizes, not print tolerances)
PLY_CSK_D = 0.0                                  # no countersinks (through holes only): the foot bolts are button heads on the top
# Everything on the plywood is held by bolts through it, a washer and a hex nut underneath (no wood screws):
# the nuts and bolt tips stay >= 2 mm above the table (the feet give 9 mm).
BEAM_CBORE = 0.0                                 # no counterbore (through holes only): the M5 heads sit under the plywood, 4 mm above the table
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
YM_FACE = 169.5                           # Y motor face (motor body on the -X side)
YM_T = 6.0                                # Y motor plate thickness (pulley hub starts 1 mm in front of it)
YI_C = (12.0, Y_BELT_Z)                   # Y idler axis as assembled (y 12: the axle nut stays clear of the parked Y block, y >= 17.3)
YI_TRAVEL = 3.0                           # tension travel: the idler slides to y 9 (6 mm of belt = 3 teeth; the clamp sets the rest)
YI_PLATE = (174.0, 180.0)                 # Y idler plate, x (axle slot in it)
YI_SLIDER = (169.0, 3.0, 20.0, 37.0, 56.0)   # x0, y0, y1, z0, z1 of the Y idler slider (x1 = the plate)
YI_LUG_Y = (22.0, 32.0)                   # lug the tension screw threads into (insert from its +y face)
YI_PUSH_X = 170.5                         # tension screw line (along -y, at the axle height)
# Y carriage
YC_X0, YC_X1 = 165.0, 245.0
YC_HALF_Y = 30.0
Z_YC0, Z_YC1 = Z_YBLK1, Z_YBLK1 + 10.0
assert abs(Z_YC1 - chains.Z_CARRIAGE_TOP) < 1e-6
POST_C = (199.0, PYC0)
POST_L = 140.0 - Y_RISER                  # post length keeps the boom at z 152..172
Z_POST0, Z_POST1 = Z_YC1, Z_YC1 + POST_L
SOCKET_H = 25.0
SOCKET_WALL_X, SOCKET_WALL_Y = 5.0, 6.0   # post socket walls; the y walls are thicker: the block-screw notches cut into them
# X axis (boom, rail)
BOOM_X0, BOOM_X1 = 209.0, 479.0
Z_BOOM0, Z_BOOM1 = 152.0, 172.0
XR_X0, XR_X1 = 229.0, 479.0               # MGN12 rail 250
X_BELT_Z = 162.0
XB_DY0, XB_DY1 = 14.0, 20.0               # belt width (along Y), relative to PYC
XM_C = (165.0, X_BELT_Z)                  # X motor axis (X, Z)
XM_FACE_DY = 31.5                         # motor face, relative to PYC
XM_T = 6.0                                # X motor plate thickness
XM_ARMS_Z = ((176.0, 196.0), (126.0, 147.0))  # arms on the post (+y face) with cheeks on its -x face
XM_CHEEK_X0 = 182.0                       # cheeks x 182..189 (on the post's -x face)
XM_ARM_X0 = 184.0                         # arms x 184..209 (the motor screw heads at x 180.5 stay clear)
XM_POST_BOLTS = [(199.0, 186.0), (199.0, 136.5)]   # (x, z) M5 into the post's +y slot
XM_SIDE_BOLTS = [(PYC0, 186.0), (PYC0, 136.5)]     # (y, z) M5 into the post's -x slot
XM_FLANGE = (140.0, 52.0 - PYC0, 5.0)     # top / bottom flanges behind the plate: x0, y0 (rel. PYC), thickness
XI_C = (470.0, X_BELT_Z)                  # X idler axis as assembled (slot x 464..476)
XI_SLOT = (464.0, 476.0)
XI_PLATE_DY = (21.0, 27.0)                # idler side plate, y relative to PYC
XI_SLIDER = (461.0, 475.0, 27.0, 36.0)    # x0, x1, y0, y1 (rel. PYC) of the X idler slider; z = XI_Z
XI_Z = (155.0, 174.0)                     # slider: z 155 up (the wrist harness passes under the idler parts at X 380..410, z <= 154)
XI_CAP_T = 12.0                           # end cap thickness (6 in v2.6: it bent under the belt pull)
XI_TOP = (176.0, 182.0)                   # top flange over the slider: side plate + flange + lug + end wall make a stiff channel
XI_LUG_X = (444.0, 453.0)                 # lug at the -x end of the side plate; the M3 push screw threads into it (v2.17: -x face 444 for belt clamp clearance at PXB 452, +x face 453 keeps 2.5 mm behind the 6.5 insert pocket)
XI_PUSH = (31.5, X_BELT_Z)                # (y rel. PYC, z) of the push screw: in line with the axle, so the slider does not tilt
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
ELECTRONICS_ON_BASE = False               # Egor, 22 Oct: control board, panel, breadboard and battery are placed and drilled by hand;
                                          # not in the model / DXF (their cables stay drawn). True brings the old layout back.

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
# 2020 V-slot (OpenBuilds geometry, as in bd_warehouse's VSlotLinearRailProfile): one slot drawn on the +x face,
# (depth from the centre, half width). Mouth 9.16 at the face, 45 deg V down to the 6.25 throat at 1.455 deep,
# lips end 1.8 below the face (drop-in T-nuts sit under them), cavity 11 wide, floor 6.1 below the face.
# Centre hole 4.2 (tapped M5 at the ends). Corner radius 1.5.   VERIFY on the profile you buy (Soberizavod / others)
VSLOT_GROOVE = [(3.69, 0.0), (3.9, 0.21), (3.9, 2.8393), (6.5607, 5.5), (8.2, 5.5), (8.2, 3.125), (8.545, 3.125), (10.0, 4.58)]
VSLOT_CORNER_R, VSLOT_HOLE_D = 1.5, 4.2
VSLOT_LIP = 1.8                           # face to the underside of the slot lips

def vtongue(x_c, a0, a1, z_face, gap=VTONGUE_GAP, axis='y'):
    """Tongue that sits in a 2020 V-slot from below (slot mouth on the plane z = z_face, slot along 'axis' from a0 to a1):
    the V-slot mouth shape (9.16 at the face, 45 deg down to the 6.25 throat at 1.455) with every half-width 'gap' smaller,
    then straight to 1.8 deep (just above the lips' underside). Self-centres the profile."""
    m, th, dv, lip = VSLOT_GROOVE[-1][1], VSLOT_GROOVE[-2][1], VSLOT_GROOVE[-1][0] - VSLOT_GROOVE[-2][0], VSLOT_LIP
    sec = [(-(m - gap), 0.0), (m - gap, 0.0), (th - gap, dv), (th - gap, lip - 0.2), (-(th - gap), lip - 0.2), (-(th - gap), dv)]
    if axis == 'y':
        pts = [V(x_c + u, a0, z_face + w) for u, w in sec]
        d = V(0, a1 - a0, 0)
    else:
        pts = [V(a0, x_c + u, z_face + w) for u, w in sec]
        d = V(a1 - a0, 0, 0)
    return Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(d)

def profile2020(p0, axis, length):
    """2020 V-slot aluminium profile (6 mm slot opening, V-groove, 4.2 centre hole) from p0 along +axis."""
    s = Part.makeBox(20, 20, length, V(-10, -10, 0))
    s = s.makeFillet(VSLOT_CORNER_R, [e for e in s.Edges if abs(e.Length - length) < 1e-6])
    half = VSLOT_GROOVE + [(11.0, 4.58)]
    pts = half + [(u, -v) for u, v in reversed(half) if v > 0]
    groove = Part.Face(Part.makePolygon([V(u, v, -1) for u, v in pts] + [V(pts[0][0], pts[0][1], -1)])).extrude(V(0, 0, length + 2))
    for ang in (0, 90, 180, 270):
        g = groove.copy()
        g.rotate(V(0, 0, 0), V(0, 0, 1), ang)
        s = s.cut(g)
    s = s.cut(Part.makeCylinder(VSLOT_HOLE_D / 2, length + 2, V(0, 0, -1)))
    s = s.removeSplitter()
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
    for x, y in FEET:                                         # foot pocket from below (Forstner bit); M3 csk bolt from the top into the foot's insert
        if FOOT_POCKET > 0:
            cut.append(cyl((x, y, Z_PLY0 - 1), (FOOT_D + 0.4) / 2, FOOT_POCKET + 1))
        cut.append(cyl((x, y, Z_PLY0 - 1), PLY_DRILL[3] / 2, Z_PLY + 2))
        if PLY_CSK_D > 0:
            cut.append(Part.makeCone(PLY_DRILL[3] / 2, PLY_CSK_D / 2, (PLY_CSK_D - PLY_DRILL[3]) / 2, V(x, y, Z_PLY1 - (PLY_CSK_D - PLY_DRILL[3]) / 2)))
            cut.append(cyl((x, y, Z_PLY1), PLY_CSK_D / 2, 1.0))
    for x, y, d in base_bolts():                              # through-bolts of the parts on the plywood
        cut.append(cyl((x, y, Z_PLY0 - 1), PLY_DRILL[d] / 2, Z_PLY + 2))
    for y in BEAM_BOLTS_Y:                                   # beam M5x20 from below: counterbore for the head, through the riser
        cut.append(cyl((YB_X, y, Z_PLY0 - 1), PLY_DRILL[5] / 2, Z_PLY + 2))
        if BEAM_CBORE > 0:
            cut.append(cyl((YB_X, y, Z_PLY0 - 1), (8.5 + 0.8) / 2, BEAM_CBORE + 1))
    for x, y in ((EB[0] + 4, EB[1] + 4), (EB[2] - 4, EB[1] + 4), (EB[0] + 4, EB[3] - 4), (EB[2] - 4, EB[3] - 4)) if ELECTRONICS_ON_BASE else ():
        cut.append(cyl((x, y, Z_PLY0 - 1), bolt(3) / 2, Z_PLY + 2))
        cut.append(Part.makeCone(3.3, bolt(3) / 2, 1.7, V(x, y, Z_PLY0)))
    return cut_all(s, cut)

def foot(x, y):
    """Printed PETG foot 20 x 9, flat under the plywood. A Ruthex M3 insert in its top takes an M3x10 button-head
    bolt from the plywood top. Prints bottom down (the table face is the smooth first layer)."""
    f = cyl((x, y, 0.0), FOOT_D / 2, FOOT_H)
    f = f.makeFillet(FOOT_EDGE_R, [e for e in f.Edges if e.BoundBox.ZMax < 0.01])
    f = f.makeFillet(0.5, [e for e in f.Edges if e.BoundBox.ZMin > FOOT_H - 0.01])
    return cut_all(f, [cyl((x, y, FOOT_H + 0.01), INSERT_D / 2, -INSERT_DEPTH)])

def base_bolts():
    """(x, y, M) of every bolt that goes through the plywood with a nut underneath (feet, standoffs and beam excluded)."""
    x0, y0, x1, y1, zt = PANEL
    L = [(x, y, 4) for x, y in YM_BOLTS] + [(x, y, 4) for x, y in IDLER_BOLTS]
    if ELECTRONICS_ON_BASE:
        L += [(x, y, 3) for x, y in panel_bolts()] + [(x, y, 3) for x, y in BB_EARS] + [(x, y, 3) for x, y in bt_ears()]
    L += [(chains.YC_LANE_X, y, 3) for y in chains.GUIDE_BOLTS_Y]
    return L

def base_items():
    add('plywood_base', plywood(), kind='bought', colour='wood')
    for i, (x, y) in enumerate(FEET):
        add('foot_%d' % (i + 1), foot(x, y))

# =============================================================================
# 4. Y AXIS (static)
# =============================================================================
YM_BASE = (152.0, 196.0, 5.0)             # base flange x0, x1, thickness (on the plywood, both sides of the plate)
YM_BOLTS = [(157.0, YM_C[0] - 12.0), (157.0, YM_C[0] + 12.0), (191.0, YM_C[0] - 12.0), (191.0, YM_C[0] + 12.0)]   # M4 through-bolts, heads clear of the gussets

def y_motor_mount():
    """Rigid stand for the Y motor: 6 mm plate between the motor and its pulley, a 5 mm base on both
    sides with four M4 through-bolts and four gussets (two each side) that make it a box.
    No tension slots any more: the belt is an open length, tensioned at the Y idler (y_idler_slider).
    The -x screws sit under the motor: screw the mount down first, then bolt the motor on from the
    pulley side. Prints base down."""
    py, pz = YM_C
    x0, x1 = YM_FACE, YM_FACE + YM_T
    bx0, bx1, bt = YM_BASE
    ya, yb = py - 27.0, min(py + 27.0, PLY[3])            # plate width (the plywood ends at y 470)
    zb = Z_PLY1 + bt
    plate = box(x0, ya, Z_PLY1, x1, yb, pz + 24.0)
    base = box(bx0, ya, Z_PLY1, bx1, yb, zb)
    g = 4.5                                                # gusset thickness (1.35 mm clear of the motor body)
    # motor side (-x): full triangles beside the motor body
    gus = [prism_y([(x0, zb), (bx0, zb), (x0, pz + 16.0)], y0, y0 + g) for y0 in (ya, yb - g)]
    # pulley side (+x): the +y one is free; the -y one keeps x <= 181.5 above z 36 (the belt runs at x 183..189 from z 39.4)
    gus.append(prism_y([(x1, zb), (bx1, zb), (x1, pz + 16.0)], yb - g, yb))
    gus.append(prism_y([(x1, zb), (bx1 - 2.0, zb), (Y_BELT_X0 - 1.5, 36.0), (Y_BELT_X0 - 1.5, pz + 10.0), (x1, pz + 16.0)], ya, ya + g))
    body = fillet_all(tidy(plate.fuse([base] + gus)))
    cut = [cyl((x0 - 1, py, pz), (NEMA17['pilot'] + TOL_MOTOR) / 2, YM_T + 2, 'x')]
    for a in (-1, 1):
        for b in (-1, 1):
            cut.append(cyl((x0 - 1, py + a * 15.5, pz + b * 15.5), (3.0 + TOL_MOTOR) / 2, YM_T + 2, 'x'))
    for x, y in YM_BOLTS:
        cut.append(cyl((x, y, Z_PLY1 - 1), bolt(4) / 2, bt + 2))
    return cut_all(body, cut)

IDLER_BOLTS = [(160.0, 10.0), (223.0, 4.75)]      # M4 through-bolts (the second clears the beam end plate's x 218)

def y_idler_bracket():
    """Holds the Y idler and its tension slider, bolts to the beam end and the plywood; carries the
    Y home switch. The idler axle (M5) runs in a slot along y; the slider on the -x face carries the
    axle head, and an M3 screw in the lug pushes the slider (and the idler) toward -y: belt tension.
    The belt pulls the idler toward the motor (+y), so the screw works in compression."""
    py, pz = YI_C
    px0, px1 = YI_PLATE
    sx0, sy0, sy1, sz0, sz1 = YI_SLIDER
    base = prism_z([(150.0, 0.0), (244.0, 0.0), (244.0, 10.0), (193.0, 10.0), (193.0, 20.0), (150.0, 20.0)], Z_PLY1, Z_PLY1 + 4.0)
    plate = box(px0, 0.0, Z_PLY1, px1, 40.0, Z_YC0 - 1.5)        # top stays 1.5 mm under the Y carriage
    # lug on the plate's -x face, 45 deg underside (prints without support); the push screw insert goes in from its +y face
    lug = prism_y([(px0, sz0 - 9.0), (sx0 - 3.0, sz0 - 1.0), (sx0 - 3.0, Z_YC0 - 1.5), (px0, Z_YC0 - 1.5)], YI_LUG_Y[0], YI_LUG_Y[1])   # top flush with the plate
    endp = box(192.0, 4.0, Z_PLY1, 218.0, 10.0, Z_YB1 - 3.5)          # top stays under the Y idler axle nut
    spacer = slot((px1, py - YI_TRAVEL - 0.5, pz), (px1, py, pz), bolt(5) / 2 + WALL_MIN + 0.05, 2.2, 'x')   # bears on the idler's inner ring
    post = box(228.0, 0.0, Z_PLY1, 236.0, 10.0, 47.0 + Y_RISER)      # switch post
    body = fillet_all(tidy(base.fuse([plate, lug, endp, spacer, post])))
    cut = [slot((px0 - 1, py - YI_TRAVEL - 0.5, pz), (px0 - 1, py, pz), bolt(5) / 2, px1 - px0 + 4.0, 'x'),   # idler axle slot
           cyl((YB_X, 3.0, Z_YB1 - 10.0), bolt(5) / 2, 8.0, 'y'),             # M5 into the beam end
           cyl((IDLER_BOLTS[0][0], IDLER_BOLTS[0][1], Z_PLY1 - 1), bolt(4) / 2, 6.0), cyl((IDLER_BOLTS[1][0], IDLER_BOLTS[1][1], Z_PLY1 - 1), bolt(4) / 2, 6.0),
           cyl((YI_PUSH_X, YI_LUG_Y[1] + 0.01, pz), INSERT_D / 2, -INSERT_DEPTH, 'y'),          # tension screw insert
           cyl((YI_PUSH_X, YI_LUG_Y[1], pz), bolt(3) / 2, -(YI_LUG_Y[1] - YI_LUG_Y[0] + 1.0), 'y')]
    for zz in (40.0 + Y_RISER - D2F['hole_pitch'] / 2 + 0.5, 40.0 + Y_RISER + D2F['hole_pitch'] / 2 + 0.5):   # M2 self-tapping into the post
        cut.append(cyl((236.01, 4.5, zz), W.M2_PILOT / 2, -5.0, 'x'))       # M2x10 self-tapping: 4.2 mm in the post
    return cut_all(body, cut)

def y_idler_slider(dy=0.0):
    """Block on the -x face of the idler plate: the idler axle passes through it (head on its -x face);
    the tension screw pushes its +y end. dy = how far it has moved toward -y (0 = as assembled)."""
    py, pz = YI_C
    sx0, sy0, sy1, sz0, sz1 = YI_SLIDER
    s = fillet_all(box(sx0, sy0 - dy, sz0, YI_PLATE[0], sy1 - dy, sz1))
    return s.cut(cyl((sx0 - 1, py - dy, pz), bolt(5) / 2, YI_PLATE[0] - sx0 + 2, 'x'))

def y_beam_riser(y):
    """Block under the Y beam (one of four): lifts the beam 10 mm so cables cross under it.
    Two V-shaped tongues (the V-slot mouth, 0.2 smaller per side) sit in the beam's bottom slot and keep it straight;
    the beam's M5 bolt goes up through the block into a T-nut. Prints flat."""
    x0, x1 = YB_X - 12.0, YB_X + 12.0
    body = box(x0, y - 12.0, Z_PLY1, x1, y + 12.0, Z_YB0)
    tongues = [vtongue(YB_X, ya, yb, Z_YB0) for ya, yb in ((y - 12.0, y - 5.0), (y + 5.0, y + 12.0))]
    body = fillet_all(tidy(body.fuse(tongues)), r_in=0.4, r_out=0.4)    # small root fillet: stays inside the slot mouth
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
    belt = belt_loop(YI_C, YM_C, 'x', Y_BELT_X0, Y_BELT_X1)         # open belt: its ends meet in the Y carriage clamp
    belt = belt.cut(box(Y_BELT_X0 - 1, Y_BELT_GAP - 1.0, ZT - 1.5, Y_BELT_X1 + 1, Y_BELT_GAP + 1.0, ZT + 1.5))
    add('y_belt_gt2', belt, kind='bought', colour='belt')
    add('y_motor_mount', y_motor_mount())
    add('y_idler_bracket', y_idler_bracket())
    add('y_idler_slider', y_idler_slider())
    add('y_home_switch_d2f', d2f_switch((236.0, 1.5, 40.0 + Y_RISER - D2F['L'] / 2 + 3.5), 'z', '+y').fuse(
        box(236.0, 1.5, 40.0 + Y_RISER + D2F['L'] / 2 + 3.5, 236.0 + D2F['W'], 11.0, 40.0 + Y_RISER + D2F['L'] / 2 + 4.3)), kind='bought', colour='black')

# =============================================================================
# 5. Y CARRIAGE (group 'ycar')
# =============================================================================
Y_CLAMP_BOX = (174.5, 190.5, PYC0, PYC0 + YC_HALF_Y)   # belt clamp and spacer, x0 x1 y0 y1 (to the carriage edge)
Y_CLAMP = [(178.9, PYC0 + 4.5), (178.9, PYC0 + 15.0), (178.9, PYC0 + 25.5)]   # M3 into inserts in the carriage
Y_BELT_GAP = PYC0 + 15.0                 # the two belt ends meet here (over the middle screw)
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
    inner, wx, wy = 10.0 + W.SOCKET_GAP, SOCKET_WALL_X, SOCKET_WALL_Y
    sock = box(pc[0] - inner - wx, pc[1] - inner - wy, Z_YC1, pc[0] + inner + wx, pc[1] + inner + wy, Z_YC1 + SOCKET_H)
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
    # assembly: the block screw heads overlap the socket walls by up to 2.6 mm, so each gets a vertical notch
    # through the wall from its counterbore to the socket top (the screw and the hex key come down through it)
    rn = (5.5 + 2 * TOL_MOVE) / 2
    notches = [cyl((YB_X + a * 10.0, PYC0 + b * 10.0, Z_YC1 - 5.0), rn, SOCKET_H + 6.0) for a in (-1, 1) for b in (-1, 1)]
    zs = Z_YC1 + SOCKET_H / 2
    for b in (-1, 1):                            # the -x notches cross the +-y socket bolt holes: join them (no sliver)
        yi = pc[1] + b * inner                   # socket inner face: a round 2.95 deep recess round the bolt hole meets the notch
        notches.append(cyl((pc[0], yi - b * 1.0, zs), 4.5, b * (rn - 0.2 + 1.0), 'y'))
    body = fillet_all(cut_all(body, notches))
    cut = []
    zs = Z_YC1 + SOCKET_H / 2
    for d in ('x', 'y'):
        for s in (-1, 1):
            if d == 'x':
                cut.append(cyl((pc[0] + s * (inner - 1), pc[1], zs), bolt(5) / 2, s * (wx + 2), 'x'))
            else:
                cut.append(cyl((pc[0], pc[1] + s * (inner - 1), zs), bolt(5) / 2, s * (wy + 2), 'y'))
    for x, y in Y_CLAMP:
        cut.append(cyl((x, y, Z_YC0 - 0.01), INSERT_D / 2, INSERT_DEPTH))
    (ax, ay), (bx, by) = Y_CHAIN_SLOT
    cut.append(slot((ax, ay, Z_YC0 - 1), (bx, by, Z_YC0 - 1), bolt(3) / 2, Z_YC1 - Z_YC0 + 2))
    cut.append(W.zip_slots(ZIPS['zip_tie_ycar']))                                   # Y carriage bundle on its way to the Y chain
    return cut_all(body, cut)

def y_belt_spacer():
    """Block between the carriage and the upper Y strand (the belt is pressed against it)."""
    x0, x1, y0, y1 = Y_CLAMP_BOX
    s = fillet_all(box(x0, y0, ZT + 0.7, x1, y1, Z_YC0))
    return cut_all(s, [cyl((x, y, ZT), bolt(3) / 2, 10.0) for x, y in Y_CLAMP])

def belt_grooves(a0, a1, gap, at, axis, t0, length):
    """Half-round grooves (r 0.6) at the 2 mm belt pitch from a0 to a1 along the strand, none over the
    belt-end gap; each groove runs across the belt ('axis') from t0. 'at' places the groove line."""
    out = []
    a = a0
    while a <= a1 + 1e-6:
        if abs(a - gap) > 1.5:
            out.append(cyl(at(a, t0), 0.6, length, axis))
        a += 2.0
    return out

def y_belt_clamp():
    """Clamp plate under the upper Y strand. The belt is an open length: its two ends meet over the
    middle screw (2 mm gap), each end held by 6 teeth in half-round grooves and two screws."""
    x0, x1, y0, y1 = Y_CLAMP_BOX
    z1 = ZT - 0.7 + 0.3
    s = fillet_all(box(x0, y0, z1 - 3.5, x1, y1, z1))
    cut = [cyl((x, y, z1 - 5), bolt(3) / 2, 7.0) for x, y in Y_CLAMP]
    cut += belt_grooves(y0 + 3.0, y1 - 3.0, Y_BELT_GAP, lambda a, t: (t, a, z1), 'x', Y_BELT_X0 - 0.5, Y_BELT_X1 - Y_BELT_X0 + 1.0)
    return cut_all(s, cut)

def post_cap():
    cap = box(POST_C[0] - 10.5, POST_C[1] - 10.5, Z_POST1, POST_C[0] + 10.5, POST_C[1] + 10.5, Z_POST1 + 4.0)
    cap = fillet_all(cap, r_out=2.0)
    return tidy(cap.fuse(cyl((POST_C[0], POST_C[1], Z_POST1), (4.2 - TOL_PRESS) / 2, -6.0)))

BRACKET_HOLE = 11.0     # hole centre from the corner, on each leg (M5)   VERIFY on your bracket

def corner_bracket(top):
    """Cast 2020 corner bracket (Soberizavod 20x20 slot 6 T01; 20 x 20 x 20, 3 mm legs, two side walls), one 5.5 hole per leg.
    Its legs sit flat on the V-slot faces; VERIFY the hole position and whether it has keys for the slot."""
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
    """X motor plate behind the post. Each arm wraps the post corner: one M5 into the post's +y slot
    (counterbored) and one into its -x slot (the cheek), so the mount cannot rock about the post
    (v2.6 had one bolt per arm on one face). 6 mm plate with top and bottom flanges (an open box)
    carries the belt pull to the arms. Tab for the X home switch. Prints with the plate on the bed."""
    P0 = PYC0
    fy = P0 + XM_FACE_DY
    py0 = fy - XM_T
    px0 = POST_C[0] - 10.0                       # post -x face
    fx0, fdy, ft = XM_FLANGE
    plate = box(140.0, py0, 126.0, 209.0, fy, 196.0)
    parts = []
    for z0, z1 in XM_ARMS_Z:
        parts.append(box(XM_ARM_X0, P0 + 10.0, z0, 209.0, py0, z1))        # arm on the post's +y face
        parts.append(box(XM_CHEEK_X0, P0 - 10.0, z0, px0, P0 + 14.0, z1))  # cheek on its -x face (joins the arm)
    parts.append(box(fx0, P0 + fdy, 196.0 - ft, XM_ARM_X0, py0, 196.0))  # top flange
    parts.append(box(fx0, P0 + fdy, 126.0, XM_ARM_X0, py0, 126.0 + ft))  # bottom flange
    body = fillet_all(tidy(plate.fuse(parts)))
    # the inside corner round the post's edge: keep the post's envelope clear, with a round relief groove (no sharp corner)
    body = body.cut(box(px0, P0 - 11.0, 120.0, 210.0, P0 + 10.0, 200.0).fuse(cyl((px0, P0 + 10.0, 120.0), 1.0, 80.0)))
    cut = [cyl((XM_C[0], fy + 1, XM_C[1]), (NEMA17['pilot'] + TOL_MOTOR) / 2, -(XM_T + 2), 'y')]
    for a in (-1, 1):
        for b in (-1, 1):
            cut.append(cyl((XM_C[0] + a * 15.5, fy + 1, XM_C[1] + b * 15.5), (3.0 + TOL_MOTOR) / 2, -(XM_T + 2), 'y'))
    for x, zc in XM_POST_BOLTS:
        cut.append(cyl((x, P0 + 9.0, zc), bolt(5) / 2, fy - P0, 'y'))
        cut.append(cyl((x, P0 + 21.0, zc), (8.5 + 2 * TOL_MOVE) / 2, fy - P0, 'y'))
    for y, zc in XM_SIDE_BOLTS:
        cut.append(cyl((XM_CHEEK_X0 - 1, y, zc), bolt(5) / 2, px0 - XM_CHEEK_X0 + 2, 'x'))
    for b in (-1, 1):                            # assembly: the +x motor screw heads (x 180.5) pass the cheeks in a groove
        cut.append(cyl((XM_C[0] + 15.5, P0 - 11.0, XM_C[1] + b * 15.5), 3.4, 27.0, 'y'))
    for yy in (P0 + 19.0 - D2F['hole_pitch'] / 2, P0 + 19.0 + D2F['hole_pitch'] / 2):    # X home switch, M2 self-tapping
        cut.append(cyl((210.0, yy, 129.5), W.M2_PILOT / 2, -9.0, 'x'))
    return cut_all(body, cut)

def x_idler_bracket():
    """End cap on the boom with a 6 mm side plate for the X idler. The idler axle runs in a slot along x;
    the slider on the outside of the side plate carries it, and an M3 screw in the lug at the plate's -x end
    pushes the slider toward +x, in line with the axle: belt tension. The belt pulls the slider back onto the
    screw (compression). v2.6 held the belt only by the friction of the axle nut on a 4 mm plate.
    Prints end cap down."""
    P0 = PYC0
    z0, z1 = XI_Z
    py0, py1 = P0 + XI_PLATE_DY[0], P0 + XI_PLATE_DY[1]
    zt = XI_TOP[1]
    ys = P0 + XI_SLIDER[3]
    ep = box(BOOM_X1, P0 - 12.0, Z_BOOM0 - 2.0, BOOM_X1 + XI_CAP_T, py0, Z_BOOM1)
    side = box(XI_LUG_X[0], py0, z0, BOOM_X1 + XI_CAP_T, py1, zt)
    lug = box(XI_LUG_X[0], py1, z0, XI_LUG_X[1], ys, zt)
    top = box(XI_LUG_X[0], py1, XI_TOP[0], BOOM_X1 + XI_CAP_T, ys, zt)
    wall = box(BOOM_X1, py1, z0, BOOM_X1 + XI_CAP_T, ys, zt)              # end wall: also stops the slider after 4 mm
    floor = box(XI_LUG_X[0], py1, z0, XI_SLIDER[0] - 2.0, ys, z0 + 5.0)   # short bottom flange at the lug (the slider never goes -x)
    r = W.FILLET_IN                                                  # end cap to side plate corner, filleted by hand
    cove = box(BOOM_X1 - r, py0 - r, z0, BOOM_X1, py0, Z_BOOM1).cut(cyl((BOOM_X1 - r, py0 - r, z0 - 1), r, 30.0))  # top = end cap top (v2.17: +2 left a knife edge)
    body = fillet_all(tidy(ep.fuse([side, lug, top, wall, floor, cove])))
    yp, zp = P0 + XI_PUSH[0], XI_PUSH[1]
    cut = [cyl((BOOM_X1 - 1, P0, X_BELT_Z), bolt(5) / 2, 8.0, 'x'),
           cyl((BOOM_X1 + 3.0, P0, X_BELT_Z), (8.5 + 2 * TOL_MOVE) / 2, XI_CAP_T, 'x'),   # head 3 mm from the boom, deep counterbore
           slot((XI_SLOT[0], py0 - 1, X_BELT_Z), (XI_SLOT[1], py0 - 1, X_BELT_Z), bolt(5) / 2, py1 - py0 + 2, 'y'),
           cyl((XI_LUG_X[0] - 0.01, yp, zp), INSERT_D / 2, INSERT_DEPTH, 'x'),             # push screw insert
           cyl((XI_LUG_X[0], yp, zp), bolt(3) / 2, XI_LUG_X[1] - XI_LUG_X[0] + 1.0, 'x')]
    return cut_all(body, cut)

def x_idler_slider():
    """Block on the outside of the X idler side plate: the axle passes through it (nyloc outside);
    the push screw bears on its -x end."""
    P0 = PYC0
    x0, x1, y0, y1 = XI_SLIDER
    s = fillet_all(box(x0, P0 + y0, XI_Z[0], x1, P0 + y1, XI_Z[1]))
    return s.cut(cyl((XI_C[0], P0 + y0 - 1, X_BELT_Z), bolt(5) / 2, y1 - y0 + 2, 'y'))

# FEA (tools/fea.py): mesh nodes held by what each part carries
def y_idler_held(x, y, z):
    """axle stack at mid-travel (head/slider face, spacer face, slot sides) and the tension screw insert"""
    py, pz = YI_C
    lug = YI_LUG_Y[0] - 0.05 <= y <= YI_LUG_Y[1] + 0.05 and math.hypot(x - YI_PUSH_X, z - pz) <= INSERT_D / 2 + 0.05
    return math.hypot(y - (py - YI_TRAVEL / 2), z - pz) <= 4.0 or lug

def x_idler_held(x, y, z):
    """axle stack (slot sides, faces under the slider) and the push screw insert in the lug"""
    if math.hypot(x - XI_C[0], z - X_BELT_Z) <= 4.0:
        return True
    return XI_LUG_X[0] - 0.05 <= x <= XI_LUG_X[1] + 0.05 and math.hypot(y - (PYC0 + XI_PUSH[0]), z - XI_PUSH[1]) <= INSERT_D / 2 + 0.05

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
    gx = PXB0 + W.X_BELT_GAP                     # open belt: its ends meet in the wrist carriage clamp (drawn at the parked X)
    add('x_belt_gt2', belt_loop(XM_C, XI_C, 'y', PYC0 + XB_DY0, PYC0 + XB_DY1).cut(
        box(gx - 1.0, PYC0 + XB_DY0 - 1, X_BELT_Z - GT2_PD / 2 - 1.5, gx + 1.0, PYC0 + XB_DY1 + 1, X_BELT_Z - GT2_PD / 2 + 1.5)), G, 'bought', 'belt')
    add('x_motor_mount', x_motor_mount(), G)
    add('x_idler_bracket', x_idler_bracket(), G)
    add('x_idler_slider', x_idler_slider(), G)
    add('x_home_switch_d2f', d2f_switch((209.0, PYC0 + 19.0 - D2F['L'] / 2, 126.5), 'y', '+x').fuse(
        box(209.0 + D2F['H'] - 0.5, PYC0 + 14.0, 131.5, 217.0, PYC0 + 24.0, 132.5)), G, 'bought', 'black')

def base_cable_chain():
    # the chains themselves depend on the pose: chains.x_chain() / chains.y_chain(), placed by assembly.world()
    add('y_chain_guide', chains.y_chain_guide())

# =============================================================================
# 6. CONTROL PANEL AND TRAYS (base)
# =============================================================================
def panel_bolts():
    x0, y0, x1, y1, zt = PANEL
    return [(x0 + 6, y0 + 6), (x1 - 6, y0 + 6), (x0 + 6, y1 - 6), (x1 - 6, y1 - 6)]

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
    cut = [cyl((ESTOP_C[0], ESTOP_C[1], zt - t - 1), (22.0 + TOL_PANEL) / 2, t + 2),
           cyl((START_C[0], START_C[1], zt - t - 1), (16.0 + TOL_PANEL) / 2, t + 2),
           cyl((LED_G[0], LED_G[1], zt - t - 1), (6.0 + TOL_PANEL) / 2, t + 2),
           cyl((LED_R[0], LED_R[1], zt - t - 1), (6.0 + TOL_PANEL) / 2, t + 2)]
    for x, y in panel_bolts():
        cut.append(cyl((x, y, Z_PLY1 - 1), bolt(3) / 2, zt - Z_PLY1 + 2))
    for yc, n in CONN.values():
        w = n * 2.54 + 0.6
        cut.append(rbox(x0 - 1, yc - w / 2, 30.4, x0 + t + 1, yc + w / 2, 33.6, 0.5, 'x'))
    for y in (47.0, 96.0):
        cut.append(cyl((x0 + t + 5.0 + 0.01, y, 24.5), W.M2_PILOT / 2, -5.0, 'x'))
    cut.append(rbox(x1 - t - 1, 70.0, 18.0, x1 + 1, 84.0, 26.0, 1.0, 'x'))      # cable exit
    for y in (47.0, 96.0):                       # assembly: screwdriver access to the connector board screws through the +x wall
        cut.append(rbox(x1 - t - 1, y - 3.0, 21.5, x1 + 1, y + 3.0, 27.5, 1.0, 'x'))
    return cut_all(body, cut)

BB_EARS = [(BB[0] + 6, BB[1] - 3.0 - 5.5), (BB[0] + 76.5, BB[1] - 3.0 - 5.5), (BB[0] + 6, BB[1] + 54.5 + 3.0 + 5.5), (BB[0] + 76.5, BB[1] + 54.5 + 3.0 + 5.5)]   # screw heads clear the tray wall

def breadboard_tray():
    x0, y0 = BB
    t = 3.0          # 2.4 mm left beside the relief groove
    tray = box(x0 - 0.3 - t, y0 - 0.3 - t, Z_PLY1, x0 + 82.8 + t, y0 + 54.8 + t, Z_PLY1 + 3.0 + 6.0)      # 3 mm floor: 2.4 left under the relief groove
    pocket = relief_pocket(x0 - 0.3, y0 - 0.3, x0 + 82.8, y0 + 54.8, Z_PLY1 + 3.0, Z_PLY1 + 10.0, 1.0)
    ears = [cyl((x, y, Z_PLY1), 5.0, 3.0) for x, y in BB_EARS]
    body = fillet_all(tidy(tray.fuse(ears))).cut(pocket)
    return cut_all(body, [cyl((x, y, Z_PLY1 - 1), bolt(3) / 2, 5.0) for x, y in BB_EARS])

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
    cut = [cyl((x, y, Z_PLY1 - 1), bolt(3) / 2, 5.0) for x, y in bt_ears()]
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
    for s, col in out.values():                    # drawn in polygon coordinates above, placed in the machine frame here
        s.translate(V(FIELD_DX, 0, 0))
    return out

def build_frame():
    PARTS.clear()
    base_items()
    y_static()
    ycar_items()
    base_cable_chain()
    if ELECTRONICS_ON_BASE:
        panel_items()
        tmc_fix()
    return PARTS
