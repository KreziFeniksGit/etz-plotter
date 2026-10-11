"""
ETZ plotter, wrist module v2  (FreeCAD Part script)
==================================================
Run:  freecadcmd -c "exec(open('wrist_module.py').read())"   or with FreeCAD's python:
      python wrist_module.py      (FreeCAD 1.0+ on Linux or Windows)
Writes out/wrist_module_assembly.step.

Coordinates are module-local, in millimetres:
  x  along the X rail (the boom),  0 = servo axis (pivot A, top)
  y  along the Y axis,             0 = centre line of the X rail
  z  height above the table
The module hangs under the MGN12H block of the X rail (block mounting face at z = 139).

Printed parts (each prints on its own without supports, then screws together):
  wrist_carriage   plate under the rail block + servo plate with window + lower pivot boss
  x_belt_riser     lifts the belt clamp to the lower X belt strand
  x_belt_clamp     ribbed plate that squeezes the belt onto the riser
  chain_post       holds the end of the X cable chain above the boom
  arm_top          driven by the servo horn
  arm_bottom       follower arm on a bearing
  end_plate        carries the two B pivots, foot flange bolts to the shelf
  shelf            wrist stepper on top, camera and hall switch below
  wrist_hub        joins the stepper shaft to the electromagnet
"""
import math
import FreeCAD as App
import Part

V = App.Vector

# =============================================================================
# 1. TOLERANCES AND PRINT RULES
# =============================================================================
TOL_MOVE = 0.4        # radial gap between parts that move against each other (rule 0.3..0.5)
TOL_PRESS = 0.12      # added to a diameter for a press fit (rule 0.10..0.15; FDM holes print small)
TOL_BOLT = 0.25       # added to a bolt diameter for a free clearance hole (rule 0.2..0.3)
TOL_MOTOR = 0.2       # added to motor and servo mounting hole sizes (rule)
WALL_MIN = 2.4        # minimum structural wall (rule 2.4..3)
FILLET_IN = 1.5       # internal corner fillet
FILLET_OUT = 1.0      # external edge fillet
INSERT_D = 4.0        # hole for a Ruthex M3 x 5.7 heat-set insert (maker spec 4.0 mm)
INSERT_DEPTH = 6.5    # pocket depth for that insert
NUT_AF = 5.5          # M3 nut across flats
SPACER_GAP = 0.3      # radial gap of the 7 mm nylon spacer in the arm shoulder hole (coupon F3)
SOCKET_GAP = 0.2      # per-side gap of the 2020 post in its socket (coupon F2)
M2_PILOT = 1.8        # pilot hole for M2 self-tapping screws (coupon F3)
ZIP_SLOT = (3.0, 1.8) # zip-tie slot width x thickness (coupon F3)

def bolt(d):
    """Clearance hole diameter for a metric bolt of diameter d."""
    return d + TOL_BOLT

# =============================================================================
# 2. BOUGHT PARTS (datasheet values; values marked VERIFY are measured on the real part)
# =============================================================================
# MGN12H block (HIWIN pattern)
BLK_HOLE_PITCH = 20.0         # 20 x 20 mm, M3, thread depth 3.5
BLK_W, BLK_L, BLK_H = 27.0, 45.4, 10.0
Z_BLOCK_FACE = 139.0
# DSServo DS3218 standard-size servo, 25T spline
SERVO_L, SERVO_W = 40.0, 20.0
SERVO_TAB_SPAN, SERVO_TAB_PITCH = 49.5, 10.0
SERVO_TAB_LEN, SERVO_TAB_THK = 54.5, 2.5
SERVO_TAB_TO_TOP = 10.0       # VERIFY: tab underside to case top (spline side)
SERVO_CASE_H = 36.5           # VERIFY: case bottom to case top
SERVO_SHAFT_FROM_END = 10.2   # VERIFY: spline centre to the near case end
HORN_FACE_ABOVE_TOP = 6.0     # VERIFY: case top to the outer face of the aluminium disc horn
HORN_D = 25.0                 # 25T aluminium disc horn (24..25.4 fit)
HORN_SLOT_R = (7.5, 10.5)     # arm slots cover horn holes on radii 7.5..10.5 mm
# 684ZZ bearing; the outer ring's inner edge is about 7.6 mm, so spacers/shims up to 7 mm OD touch the inner ring only
BRG_ID, BRG_OD, BRG_W = 4.0, 9.0, 4.0
SPACER_OD, SPACER_L = 7.0, 3.0      # nylon round spacer 4.2 x 7 x 3 (reaches the inner ring through the arm shoulder)
SHIM_OD, SHIM_T = 7.0, 0.8          # shim washer 4.2 x 7 x 0.8 between inner ring and end plate
# StepperOnline 11HS12-0674S (NEMA11, 28 x 28 x 31.5)
N11_SQ, N11_LEN = 28.2, 31.5
N11_HOLE_PITCH, N11_HOLE = 23.0, 2.5
N11_PILOT_D, N11_PILOT_H = 22.0, 2.0
N11_SHAFT_D, N11_SHAFT_FLAT, N11_SHAFT_LEN = 5.0, 4.5, 20.0
# electromagnet P20/15, 5 V, M3 thread on top
MAG_D, MAG_H = 20.0, 15.0
# camera board (your choice; change to match it)
CAM_BOARD, CAM_HOLE_PITCH, CAM_HOLE = 32.0, 28.0, 2.0
CAM_LENS_D = 12.0
# TI DRV5023 hall switch, TO-92 (4.0 x 1.5 x 3 mm body)
TO92_W, TO92_T, TO92_H = 4.1, 1.6, 5.0
# GT2 6 mm belt
BELT_W, BELT_T, BELT_PITCH = 6.0, 1.4, 2.0
# zip ties 2.5 mm wide
ZIP_W, ZIP_T = ZIP_SLOT
ZIP_GAP = 6.0

# =============================================================================
# 3. MODULE GEOMETRY
# =============================================================================
R_ARM = 80.0                    # parallelogram arm length
Z_PIVOT_TOP, Z_PIVOT_BOT = 117.0, 77.0
H_MID = 22.5                    # magnet face height with the arms level
H_MIN, H_MAX = 5.0, 40.0        # single checker on the field .. carry height over a 5-stack
MAG_X, MAG_Y = 105.0, 21.0      # magnet axis relative to pivot A
CAM_X = 141.0

# carriage plate (top face = block mounting face)
CP_T = 6.0
Z_CP1 = Z_BLOCK_FACE
Z_CP0 = Z_CP1 - CP_T
CP_X0, CP_X1 = -40.0, 20.0
CP_Y0 = -24.5
CP_Y_ARM = 18.5                 # plate edge above the arms (x > ARM_CLEAR_X)
CP_Y_RISER = 28.0               # plate edge under the belt riser
ARM_CLEAR_X = -16.0
BLOCK_SINK = 3.5                # block screw heads sunk into the plate from below
# servo plate (vertical): the servo tabs bear on its -y face
SP_Y0, SP_T = 4.0, 5.0
SP_Y1 = SP_Y0 + SP_T
SP_Z0 = Z_PIVOT_BOT - 12.0
# servo position (spline axis = pivot A top)
SERVO_X1 = SERVO_SHAFT_FROM_END
SERVO_X0 = SERVO_X1 - SERVO_L
SERVO_XC = (SERVO_X0 + SERVO_X1) / 2
CASE_TOP_Y = SP_Y0 + SERVO_TAB_TO_TOP
HORN_FACE_Y = CASE_TOP_Y + HORN_FACE_ABOVE_TOP
# arms
ARM_T = 6.5                     # leaves a 2.5 mm shoulder behind the 4 mm bearing
ARM_Y0 = HORN_FACE_Y
ARM_Y1 = ARM_Y0 + ARM_T
ARM_BOSS_R = 7.5
ARM_TOP_BOSS_R = 14.5           # carries the horn slots with 2.4 mm walls
WASHER_T = 0.8                  # M4 washer between arm and end plate = moving gap
# end plate and shelf
EP_Y0 = ARM_Y1 + WASHER_T
EP_T = 5.0
EP_Y1 = EP_Y0 + EP_T
EP_X0, EP_X1 = 70.0, 90.0
SH_T = 4.0
Z_SH1 = 67.5                    # shelf top = wrist stepper mounting face
Z_SH0 = Z_SH1 - SH_T
SH_X0, SH_X1 = 58.0, 161.0
SH_Y0, SH_Y1 = 3.0, 39.0
FOOT_T = INSERT_DEPTH + 2.5     # foot pad on the -x side of the pivot nut, holds two inserts
FOOT_X0, FOOT_X1 = 59.0, 75.0     # pivot B nut starts at x 76
# X belt lower strand (pulley axis z 162, 20T pitch dia 12.73), belt width along y
X_BELT_Z = 162.0 - 12.73 / 2
XB_Y0, XB_Y1 = 14.0, 20.0
# belt riser and chain post footprints
RS_X0, RS_X1 = CP_X0, -14.0
RS_Y0, RS_Y1 = 14.5, CP_Y_RISER
CHAIN_X0, CHAIN_X1 = 4.0, 22.0

# =============================================================================
# 4. HELPERS
# =============================================================================
AX = {'x': V(1, 0, 0), 'y': V(0, 1, 0), 'z': V(0, 0, 1)}

def box(x0, y0, z0, x1, y1, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))

def rbox(x0, y0, z0, x1, y1, z1, r, axis):
    """Box with its edges along 'axis' rounded (a pocket/slot tool without sharp corners)."""
    b = box(x0, y0, z0, x1, y1, z1)
    L = {'x': x1 - x0, 'y': y1 - y0, 'z': z1 - z0}[axis]
    es = [e for e in b.Edges if abs(e.Length - L) < 1e-6 and abs(abs((e.Vertexes[1].Point - e.Vertexes[0].Point).normalize().dot(AX[axis])) - 1) < 1e-6]
    return b.makeFillet(r, es)

def cyl(c, r, h, axis='z'):
    """Cylinder from base point c along +axis by h (h may be negative)."""
    d = AX[axis]
    if h < 0:
        c = V(*c) + d * h
        h = -h
    return Part.makeCylinder(r, h, V(*c), d)

def slot(p0, p1, r, h, axis='z'):
    """Stadium slot from p0 to p1, extruded h along axis."""
    a, b = V(*p0), V(*p1)
    s = cyl(a, r, h, axis).fuse(cyl(b, r, h, axis))
    d = b - a
    if d.Length > 1e-6:
        side = d.cross(AX[axis]); side.normalize()
        pts = [a + side * r, b + side * r, b - side * r, a - side * r, a + side * r]
        s = s.fuse(Part.Face(Part.makePolygon(pts)).extrude(AX[axis] * h))
    return s.removeSplitter()

def prism_x(pts, x0, x1):
    """Polygon in (y, z), extruded along x."""
    w = Part.makePolygon([V(x0, y, z) for y, z in pts] + [V(x0, pts[0][0], pts[0][1])])
    return Part.Face(w).extrude(V(x1 - x0, 0, 0))

def prism_y(pts, y0, y1):
    """Polygon in (x, z), extruded along y."""
    w = Part.makePolygon([V(x, y0, z) for x, z in pts] + [V(pts[0][0], y0, pts[0][1])])
    return Part.Face(w).extrude(V(0, y1 - y0, 0))

def prism_z(pts, z0, z1):
    """Polygon in (x, y), extruded along z."""
    w = Part.makePolygon([V(x, y, z0) for x, y in pts] + [V(pts[0][0], pts[0][1], z0)])
    return Part.Face(w).extrude(V(0, 0, z1 - z0))

def _across(along, axis):
    return [k for k in 'xyz' if k not in (along, axis)][0]

def zip_pair(c, along, axis, h, gap=ZIP_GAP):
    """Two rounded zip-tie slots for a cable running along 'along' over a plate pierced along 'axis' (depth h).
    The slots sit on either side of the cable (centres c +- gap/2 across it); each slot is long along the
    cable (the tie's width) and narrow across it (the tie's thickness), so the tie wraps the cable."""
    a, n = AX[along], AX[_across(along, axis)]
    out = None
    for s in (-1, 1):
        p = V(*c) + n * (s * gap / 2)
        half = a * ((ZIP_W - ZIP_T) / 2)
        sl = slot(p - half, p + half, ZIP_T / 2, h, axis)
        out = sl if out is None else out.fuse(sl)
    return out

TIE_W, TIE_T = 2.5, 1.0           # zip tie band (2.5 x 1.0 fits the 3.0 x 1.8 slot)
TIE_HEAD = (4.0, 3.0, 4.5)        # lock head: along the cable, out from the band, along the band

def _frame(u, w):
    """Matrix taking local (u along the cable, v across it, w out of the face toward the cable) to world."""
    v = w.cross(u)
    return App.Matrix(u.x, v.x, w.x, 0, u.y, v.y, w.y, 0, u.z, v.z, w.z, 0, 0, 0, 0, 1)

def _ring(v0, v1, w0, w1, t, wid):
    """Rectangular band of thickness t around the box v0..v1 x w0..w1 (local v, w), width wid along u."""
    outer = Part.makeBox(wid, v1 - v0 + 2 * t, w1 - w0 + 2 * t, V(-wid / 2, v0 - t, w0 - t))
    inner = Part.makeBox(wid + 2, v1 - v0, w1 - w0, V(-wid / 2 - 1, v0, w0))
    return outer.cut(inner)

def zip_tie_at(c, u, w, plate_t, cable_d, gap, lift=0.0):
    """A closed zip tie: down one slot, across the back of the plate (thickness plate_t), up the other slot
    and over the cable. c = point on the cable-side face between the slots, u = cable direction,
    w = unit normal of that face toward the cable, gap = slot centre distance, lift = face-to-cable gap."""
    band = _ring(-gap / 2 + TIE_T / 2, gap / 2 - TIE_T / 2, -plate_t, lift + cable_d, TIE_T, TIE_W)
    hu, hw, hv = TIE_HEAD
    head = Part.makeBox(hu, hw, hv, V(-hu / 2, gap / 2 + TIE_T / 2, max(0.1, lift + cable_d / 2 - hv / 2)))   # beside the cable, clear of the face
    s = band.fuse(head).removeSplitter()
    s.transformShape(_frame(u, w))
    s.translate(V(*c))
    return s

def zip_tie(c, along, axis, sign, plate_t, cable_d, gap, lift=0.0):
    """zip_tie_at for a face normal to 'axis'; sign = +1/-1: the cable is on the +axis / -axis side."""
    return zip_tie_at(c, AX[along], AX[axis] * sign, plate_t, cable_d, gap, lift)

def zip_slots(spec):
    """The zip_pair matching a ZIPS entry (through the whole plate)."""
    _, c, along, axis, sign, plate_t, cable_d, gap, lift = spec
    start = V(*c) - AX[axis] * (plate_t + 1.0 if sign > 0 else 1.0)
    return zip_pair(start, along, axis, plate_t + 2.0, gap)

def is_line(e):
    try:
        return e.Curve.__class__.__name__ == 'Line'
    except Exception:
        return False

def _concave(shape, edge, eps=0.05):
    """True if the edge is an internal (concave) corner of the solid."""
    faces = shape.ancestorsOfType(edge, Part.Face)
    if len(faces) != 2:
        return None
    p = edge.valueAt((edge.FirstParameter + edge.LastParameter) / 2)
    ns = []
    for f in faces:
        u, v = f.Surface.parameter(p)
        ns.append(f.normalAt(u, v))
    q1 = p + ns[0] * eps - ns[1] * eps
    q2 = p + ns[1] * eps - ns[0] * eps
    return shape.isInside(q1, 1e-4, True) or shape.isInside(q2, 1e-4, True)

FILLET_LOG = []

def tidy(shape):
    s = shape.removeSplitter()
    if s.ShapeType == 'Compound' and len(s.Solids) == 1:
        s = s.Solids[0]
    return s

def _fillet(shape, r, edges):
    """makeFillet on a copy that also rejects a broken result: in FreeCAD 1.1 a failed fillet can damage
    the shape it was called on, and can return a broken solid without raising."""
    src, c = shape.Edges, shape.copy()
    idx = [next(i for i, e2 in enumerate(src) if e2.isSame(e)) for e in edges]
    s = tidy(c.makeFillet(r, [c.Edges[i] for i in idx]))
    s.check(True)                        # strict check: raises on a broken result (isValid() can miss it)
    return s

def fillet_all(shape, r_in=FILLET_IN, r_out=FILLET_OUT, min_len=2.0):
    """Fillet straight edges: internal corners r_in, external r_out. Edges the
    kernel refuses are retried with a smaller radius, then skipped (logged)."""
    groups = {'in': [], 'out': []}
    for e in shape.Edges:
        if not is_line(e) or e.Length < min_len:
            continue
        c = _concave(shape, e)
        if c is None:
            continue
        groups['in' if c else 'out'].append(e)
    out = shape
    skipped = 0
    for key, r in (('in', r_in), ('out', r_out)):
        es0 = groups[key]
        if not es0:
            continue
        def find(es):
            res = []
            for e in es:
                m = e.valueAt((e.FirstParameter + e.LastParameter) / 2)
                for e2 in out.Edges:
                    if is_line(e2) and abs(e2.Length - e.Length) < 1e-4 and e2.distToShape(Part.Vertex(m))[0] < 1e-5:
                        res.append(e2)
                        break
            return res
        es = find(es0)
        try:
            out = tidy(_fillet(out, r, es))
            continue
        except Exception:
            pass
        ok, bad = [], []
        for e in es:
            try:
                _fillet(out, r, ok + [e]); ok.append(e)
            except Exception:
                bad.append(e)
        if ok:
            out = tidy(_fillet(out, r, ok))
        for e0 in bad:                       # retry one by one on the updated shape with smaller radii
            for rr in (r, r * 0.8, r * 2 / 3, r / 2, r * 0.35, r * 0.25):
                e = find([e0])
                try:
                    out = tidy(_fillet(out, rr, e))
                    break
                except Exception:
                    pass
            else:
                skipped += 1
    FILLET_LOG.append(skipped)
    return tidy(out)

def cut_all(body, tools):
    for t in tools:
        if t is not None and not t.isNull():
            body = body.cut(t)
    return tidy(body)

# =============================================================================
# 5. PRINTED PARTS
# =============================================================================
BLOCK_HOLES = [(a * BLK_HOLE_PITCH / 2, b * BLK_HOLE_PITCH / 2) for a in (-1, 1) for b in (-1, 1)]
RISER_MOUNT = [(-31.0, 19.0), (-23.0, 19.0)]                # riser to carriage, inserts in the riser bottom
CLAMP_SCREWS = [(RS_X0 + 5.0, 23.0), (RS_X1 - 5.0, 23.0)]   # clamp plate to riser, inserts in the riser top
CHAIN_MOUNT = [(9.5, -19.25), (16.5, -19.25)]               # chain post to carriage, inserts in the post foot
SERVO_TAB_HOLES = [(SERVO_XC + a * SERVO_TAB_SPAN / 2, Z_PIVOT_TOP + b * SERVO_TAB_PITCH / 2) for a in (-1, 1) for b in (-1, 1)]

def wrist_carriage():
    """Carriage plate and servo plate as one stiff L-part.
    Prints top face (block face) down: the servo plate, ribs and boss grow up.
    The servo window has a W-shaped 45 deg roof in print orientation, so it
    needs no bridge; the lower pivot boss is a teardrop for the same reason."""
    outline = [(CP_X0, CP_Y0), (CP_X1, CP_Y0), (CP_X1, CP_Y_ARM), (ARM_CLEAR_X, CP_Y_ARM), (ARM_CLEAR_X, CP_Y_RISER), (CP_X0, CP_Y_RISER)]
    plate = prism_z(outline, Z_CP0, Z_CP1)
    wall = box(CP_X0, SP_Y0, SP_Z0, CP_X1, SP_Y1, Z_CP0)
    # ribs: +y side at both ends, -y side at the left end (outside the servo tabs)
    ribs = [prism_x([(SP_Y1, Z_CP0), (SP_Y1 + 7.0, Z_CP0), (SP_Y1, Z_CP0 - 7.0)], x0, x0 + 4.0) for x0 in (CP_X0, CP_X1 - 4.0)]   # 7: clear of the servo tab nuts
    # teardrop boss for the lower A pivot (tip toward +z = down in print)
    r = 7.5
    tip = Z_PIVOT_BOT + r * math.sqrt(2)
    td_pts = [(0.0, tip), (r / math.sqrt(2), Z_PIVOT_BOT + r / math.sqrt(2)), (-r / math.sqrt(2), Z_PIVOT_BOT + r / math.sqrt(2))]
    boss = cyl((0.0, SP_Y1, Z_PIVOT_BOT), r, ARM_Y0 - 0.5 - SP_Y1, 'y').fuse(prism_y(td_pts, SP_Y1, ARM_Y0 - 0.5))
    body = tidy(plate.fuse([wall, boss] + ribs))
    # servo window: case + 0.4 per side, W-shaped roof below (print-up direction)
    wx0, wx1 = SERVO_X0 - TOL_MOVE, SERVO_X1 + TOL_MOVE
    wz0, wz1 = Z_PIVOT_TOP - SERVO_W / 2 - TOL_MOVE, Z_PIVOT_TOP + SERVO_W / 2 + TOL_MOVE
    q = (wx1 - wx0) / 4
    win = prism_y([(wx0, wz1), (wx0, wz0), (wx0 + q, wz0 - q), (wx0 + 2 * q, wz0), (wx0 + 3 * q, wz0 - q), (wx1, wz0), (wx1, wz1)],
                  SP_Y0 - 1, SP_Y1 + 1)
    # round the window's corners on the tool itself (r 0.5 keeps 0.35 mm around the case corners)
    win = win.makeFillet(0.5, [e for e in win.Edges if is_line(e) and abs(e.Length - (SP_T + 2)) < 1e-6
                               and _concave(win, e) is False])
    body = fillet_all(body)
    body = cut_all(body, [win])
    cut = []
    for x, y in BLOCK_HOLES:                       # M3x6 from below, heads sunk
        cut.append(cyl((x, y, Z_CP0 - 1), bolt(3) / 2, CP_T + 2))
        cut.append(cyl((x, y, Z_CP0 - 1), (5.5 + 2 * TOL_MOVE) / 2, 1 + BLOCK_SINK))
    for x, y in RISER_MOUNT + CHAIN_MOUNT:          # M3 from below into inserts in the add-on parts
        cut.append(cyl((x, y, Z_CP0 - 1), bolt(3) / 2, CP_T + 2))
    for x, z in SERVO_TAB_HOLES:                    # M3 bolt + nyloc; servo tab holes (4.5) give the play
        cut.append(cyl((x, SP_Y0 - 1, z), bolt(3) / 2, SP_T + 2, 'y'))
    cut.append(cyl((0.0, SP_Y0 - 1, Z_PIVOT_BOT), bolt(4) / 2, ARM_Y0 - SP_Y0 + 2, 'y'))   # M4 pivot bolt
    cut.append(zip_slots(ZIPS['zip_servo']))                                              # servo lead under the plate
    return cut_all(body, cut)

def x_belt_riser():
    """Block on top of the carriage plate that lifts the clamp jaw to the lower belt strand."""
    top = X_BELT_Z - BELT_T / 2
    body = fillet_all(box(RS_X0, RS_Y0, Z_CP1, RS_X1, RS_Y1, top))
    cut = [cyl((x, y, top + 0.01), INSERT_D / 2, -INSERT_DEPTH) for x, y in CLAMP_SCREWS]
    cut += [cyl((x, y, Z_CP1 - 0.01), INSERT_D / 2, INSERT_DEPTH) for x, y in RISER_MOUNT]
    return cut_all(body, cut)

def x_belt_clamp():
    """Plate pressing the belt onto the riser; half-round grooves at 2 mm pitch
    take the belt teeth, so the belt cannot slip."""
    z0 = X_BELT_Z + BELT_T / 2 - 0.3            # 0.3 mm squeeze on the belt
    body = fillet_all(box(RS_X0, RS_Y0, z0, RS_X1, RS_Y1, z0 + 3.5))
    cut = [cyl((x, y, z0 - 1), bolt(3) / 2, 6) for x, y in CLAMP_SCREWS]
    x = RS_X0 + 9.0
    while x <= RS_X1 - 9.0:
        cut.append(cyl((x, XB_Y0 - 0.5, z0), 0.6, BELT_W + 1.0, 'y'))
        x += BELT_PITCH
    return cut_all(body, cut)

CHAIN_TOP = 208.0                # top of the chain post = underside of the X chain's upper run (boom top 172 + 2 x R18)
CHAIN_PLATE_T = 4.0
CHAIN_PLATE_X0, CHAIN_PLATE_X1 = 4.0, 26.0     # carries the 20 mm end link (x 5..25)
CHAIN_POST_T = 5.0               # upright, on the -y side of the boom
CHAIN_CLEAR_Y = -13.0            # chain lower run spans y -11.5..11.5 under the plate

def chain_post():
    """Holds the moving end of the X cable chain on top, 36 mm above the chain's lower run
    lying on the boom. Upright on the -y side of the boom, plate across the top, 45 deg brace.
    The end link screws through a slot (any hole spacing), nuts underneath.
    Prints on its -y face."""
    z1 = CHAIN_TOP
    z0 = z1 - CHAIN_PLATE_T
    foot = box(CHAIN_X0, CP_Y0, Z_CP1, CHAIN_X1, CP_Y0 + 10.5, Z_CP1 + INSERT_DEPTH + WALL_MIN)
    post = box(CHAIN_X0, CP_Y0, Z_CP1, CHAIN_X1, CP_Y0 + CHAIN_POST_T, z1)
    top = box(CHAIN_PLATE_X0, CP_Y0, z0, CHAIN_PLATE_X1, 12.5, z1)
    yb = CP_Y0 + CHAIN_POST_T
    d = CHAIN_CLEAR_Y - yb
    brace = prism_x([(yb, z0), (CHAIN_CLEAR_Y, z0), (yb, z0 - d)], CHAIN_X0, CHAIN_X1)
    lower = prism_x([(yb, Z_CP1 + INSERT_DEPTH + WALL_MIN), (CP_Y0 + 10.5, Z_CP1 + INSERT_DEPTH + WALL_MIN),
                     (yb, Z_CP1 + INSERT_DEPTH + WALL_MIN + 10.5 - CHAIN_POST_T)], CHAIN_X0, CHAIN_X1)   # 45 deg foot gusset
    body = fillet_all(tidy(foot.fuse([post, top, brace, lower])))
    cut = [cyl((x, y, Z_CP1 - 0.01), INSERT_D / 2, INSERT_DEPTH) for x, y in CHAIN_MOUNT]
    for k in ('zip_chain_post_1', 'zip_chain_post_2'):
        cut.append(zip_slots(ZIPS[k]))
    cut.append(slot((CHAIN_PLATE_X0 + 4.0, 0.0, z0 - 1), (CHAIN_PLATE_X1 - 4.0, 0.0, z0 - 1), bolt(3) / 2, CHAIN_PLATE_T + 2))
    return cut_all(body, cut)

def _arm_shape(r_a):
    """Tangent hull of a circle r_a at A and r 7.5 at B (x-z plane), extruded along y."""
    da = cyl((0, 0, 0), r_a, ARM_T, 'y')
    db = cyl((R_ARM, 0, 0), ARM_BOSS_R, ARM_T, 'y')
    a = math.asin((r_a - ARM_BOSS_R) / R_ARM)
    t1a, t1b = (-r_a * math.sin(a), r_a * math.cos(a)), (R_ARM - ARM_BOSS_R * math.sin(a), ARM_BOSS_R * math.cos(a))
    t2a, t2b = (-r_a * math.sin(a), -r_a * math.cos(a)), (R_ARM - ARM_BOSS_R * math.sin(a), -ARM_BOSS_R * math.cos(a))
    web = prism_y([t1a, t1b, t2b, t2a], 0, ARM_T)
    return tidy(da.fuse([db, web]))

def _arm(top):
    za = Z_PIVOT_TOP if top else Z_PIVOT_BOT
    body = _arm_shape(ARM_TOP_BOSS_R if top else ARM_BOSS_R)
    cut = [slot((20.0, -1, 0), (R_ARM - 18.0, -1, 0), 3.0, ARM_T + 2, 'y')]   # lightening slot, about 25 % of the web
    def bearing(x):
        return [cyl((x, ARM_T + 0.01, 0), (BRG_OD + TOL_PRESS) / 2, -BRG_W - 0.01, 'y'),        # press seat from the end-plate side
                cyl((x, -1, 0), (SPACER_OD + 2 * SPACER_GAP) / 2, ARM_T + 2, 'y')]                    # shoulder hole: spacer + 0.3 radial, keeps a 0.76 mm ledge for the outer ring
    cut += bearing(R_ARM)
    if top:
        cut.append(cyl((0, -1, 0), 3.5, ARM_T + 2, 'y'))                                         # clears the horn screw head
        for k in range(4):
            ang = math.radians(45 + 90 * k)
            p0 = (HORN_SLOT_R[0] * math.cos(ang), -1, HORN_SLOT_R[0] * math.sin(ang))
            p1 = (HORN_SLOT_R[1] * math.cos(ang), -1, HORN_SLOT_R[1] * math.sin(ang))
            cut.append(slot(p0, p1, bolt(3) / 2, ARM_T + 2, 'y'))
    else:
        cut += bearing(0.0)
    body = cut_all(body, cut)
    # round the whole outer outline (tangent arcs + straight sides) on both faces in one call
    def outline(e):
        try:
            c = e.Curve
        except Exception:
            return False
        if c.__class__.__name__ == 'Line':
            return e.Length > 60.0
        if c.__class__.__name__ == 'Circle':
            return c.Radius >= ARM_BOSS_R - 0.05
        return False
    body = tidy(body.makeFillet(0.8, [e for e in body.Edges if outline(e)]))
    # slot rims: fillet each slot outline as one tangent chain (lines + its end arcs)
    for x0, x1, r in [(20.0, R_ARM - 18.0, 3.0)]:
        rim = [e for e in body.Edges if (is_line(e) and abs(e.Length - (x1 - x0)) < 1e-6) or
               (not is_line(e) and hasattr(e, 'Curve') and e.Curve.__class__.__name__ == 'Circle' and abs(e.Curve.Radius - r) < 1e-6)]
        try:
            body = tidy(body.makeFillet(0.5, rim))
        except Exception:
            FILLET_LOG.append(len(rim))
    if top:
        rim = [e for e in body.Edges if (is_line(e) and abs(e.Length - (HORN_SLOT_R[1] - HORN_SLOT_R[0])) < 1e-6) or
               (not is_line(e) and e.Curve.__class__.__name__ == 'Circle' and abs(e.Curve.Radius - bolt(3) / 2) < 1e-6)]
        try:
            body = tidy(body.makeFillet(0.4, rim))
        except Exception:
            FILLET_LOG.append(len(rim))
    body.translate(V(0, ARM_Y0, za))
    return body

def arm_top():
    return _arm(True)

def arm_bottom():
    return _arm(False)

FOOT_SCREWS = [(FOOT_X0 + 2.5 + INSERT_D / 2, SH_Y1 - 2.4 - INSERT_D / 2), (FOOT_X1 - 2.5 - INSERT_D / 2, SH_Y1 - 2.4 - INSERT_D / 2)]

def end_plate():
    """Carries both B pivots; the foot flange (+y side, clear of the arms)
    bolts to the shelf with two M3 into inserts. Prints on its -y face."""
    plate = box(EP_X0, EP_Y0, Z_SH1, EP_X1, EP_Y1, Z_PIVOT_TOP + 10.0)
    foot = box(FOOT_X0, EP_Y0, Z_SH1, FOOT_X1, SH_Y1, Z_SH1 + FOOT_T)
    body = fillet_all(tidy(plate.fuse(foot)))
    cut = [cyl((R_ARM, EP_Y0 - 1, z), bolt(4) / 2, EP_T + 2, 'y') for z in (Z_PIVOT_TOP, Z_PIVOT_BOT)]
    cut += [cyl((x, y, Z_SH1 - 0.01), INSERT_D / 2, INSERT_DEPTH) for x, y in FOOT_SCREWS]  # inserts; M3x10 comes up through the shelf
    cut.append(zip_slots(ZIPS['zip_end_plate']))                                          # wrist harness, between the pivot nuts
    return cut_all(body, cut)

HALL_POS = (MAG_X, MAG_Y + 9.7 + 0.8 + 3.2)     # 0.8 mm from the flag magnet to the sensor face
HALL_LEAD_HOLE = (86.0, 35.0)                    # hall leads come up through the shelf here (beside the end plate, clear of the stepper)
CAM_POSTS = [(CAM_X + a * CAM_HOLE_PITCH / 2, MAG_Y + b * CAM_HOLE_PITCH / 2) for a in (-1, 1) for b in (-1, 1)]

def shelf():
    """Wrist stepper on top, camera and hall switch below. Prints top face down
    (stepper face flat on the bed); the under-rib and posts grow up."""
    body = box(SH_X0, SH_Y0, Z_SH0, SH_X1, SH_Y1, Z_SH1)
    notch = box(SH_X0 - 1, ARM_Y0 - TOL_MOVE - 0.5, Z_SH0, EP_X1 + 1.0, ARM_Y1 + 0.5, Z_SH1 + 1)   # lower arm clears at full lift
    ny0, ny1 = ARM_Y0 - TOL_MOVE - 0.5, ARM_Y1 + 0.5                            # notch edges
    under = box(76.0, SH_Y0, Z_SH0 - 10.0, 81.0, ny0, Z_SH0).fuse(box(76.0, ny1, Z_SH0 - 10.0, 81.0, SH_Y1, Z_SH0))   # rib under the end plate, flush with the notch
    posts = [cyl((x, y, Z_SH0), 3.55, -4.0) for x, y in CAM_POSTS]             # 2.4 mm wall around the M2 hole
    hall = box(HALL_POS[0] - 4.6, HALL_POS[1] - 3.2, Z_SH0 - 9.0, HALL_POS[0] + 4.6, HALL_POS[1] + 3.2, Z_SH0)
    body = tidy(body.cut(notch).fuse([under, hall] + posts))
    body = fillet_all(body)
    cut = [cyl((MAG_X, MAG_Y, Z_SH0 - 1), (N11_PILOT_D + TOL_MOTOR) / 2, SH_T + 2)]
    for a in (-1, 1):
        for b in (-1, 1):
            cut.append(cyl((MAG_X + a * N11_HOLE_PITCH / 2, MAG_Y + b * N11_HOLE_PITCH / 2, Z_SH0 - 1), (N11_HOLE + TOL_MOTOR) / 2, SH_T + 2))
    for x, y in CAM_POSTS:
        cut.append(cyl((x, y, Z_SH0 - 5), (CAM_HOLE + TOL_BOLT) / 2, SH_T + 7))
    cut.append(cyl((CAM_X, MAG_Y, Z_SH0 - 1), 5.0, SH_T + 2))                  # camera cable pass
    for x, y in FOOT_SCREWS:
        cut.append(cyl((x, y, Z_SH0 - 1), bolt(3) / 2, SH_T + 2))
    # TO-92 pocket (press, from below, leads down), flat face toward the hub flag, rounded pocket corners
    pocket = rbox(HALL_POS[0] - (TO92_W + TOL_PRESS) / 2, HALL_POS[1] - 3.2 - 1.0, Z_SH0 - 9.0 - 1.0,
                  HALL_POS[0] + (TO92_W + TOL_PRESS) / 2, HALL_POS[1] - 3.2 + TO92_T + TOL_PRESS, Z_SH0 - 9.0 + TO92_H, 0.4, 'z')
    ztop = Z_SH0 - 9.0 + TO92_H
    cut.append(tidy(pocket.makeFillet(0.3, [e for e in pocket.Edges if abs(e.BoundBox.ZMin - ztop) < 1e-6 and abs(e.BoundBox.ZMax - ztop) < 1e-6])))   # rounded pocket roof
    cut.append(cyl((HALL_LEAD_HOLE[0], HALL_LEAD_HOLE[1], Z_SH0 - 1), 1.5, SH_T + 2))   # hall leads up (the sensor sits leads-down in its pocket)
    cut.append(zip_slots(ZIPS['zip_camera']))                                             # camera cable
    return cut_all(body, cut)

def wrist_hub():
    """D-bore press fit on the stepper shaft; the magnet hangs on one M3 screw.
    The flag carries a 3 x 2 magnet past the hall switch for homing."""
    z0, z1 = H_MID + MAG_H, Z_SH1 - N11_SHAFT_LEN + 12.5
    body = cyl((MAG_X, MAG_Y, z0), 7.0, z1 - z0)
    flag = box(MAG_X - 4.25, MAG_Y + 5.0, z1 - 8.0, MAG_X + 4.25, MAG_Y + 9.7, z1)
    body = fillet_all(tidy(body.fuse(flag)), r_out=0.6, min_len=2.0)
    cut = [cyl((MAG_X, MAG_Y, z0 - 1), bolt(3) / 2, 4.0),
           cyl((MAG_X, MAG_Y, z0 + 2.5), (5.5 + 2 * TOL_MOVE) / 2, 4.0)]
    bore = cyl((MAG_X, MAG_Y, z0 + 6.5), (N11_SHAFT_D + TOL_PRESS) / 2, z1 - z0)
    flat = box(MAG_X + (N11_SHAFT_FLAT - N11_SHAFT_D / 2) + TOL_PRESS / 2, MAG_Y - 4, z0 + 6.4, MAG_X + 4, MAG_Y + 4, z1 + 1)
    cut.append(bore.cut(flat))
    cut.append(cyl((MAG_X, MAG_Y + 9.7 + 0.01, z1 - 4.0), (3.0 + TOL_PRESS) / 2, -2.2, 'y'))   # 3 x 2 magnet, press
    return cut_all(body, cut)

# =============================================================================
# 5b. ZIP TIES AND THE WRIST HARNESS
# =============================================================================
# name: (part, point on the cable-side face between the slots, cable direction, plate normal axis,
#        side of the cable (+1/-1 along that axis), plate thickness, cable diameter, slot centre gap, face-to-cable gap)
ZIPS = {
    'zip_servo': ('wrist_carriage', (-32.0, -19.0, Z_CP0), 'y', 'z', -1, CP_T, 3.5, 5.5, 0.2),
    'zip_chain_post_1': ('chain_post', ((CHAIN_X0 + CHAIN_X1) / 2, CP_Y0, 165.0), 'z', 'y', -1, CHAIN_POST_T, 7.0, 10.0, 0.5),
    'zip_chain_post_2': ('chain_post', ((CHAIN_X0 + CHAIN_X1) / 2, CP_Y0, 192.0), 'z', 'y', -1, CHAIN_POST_T, 7.0, 10.0, 0.5),
    'zip_end_plate': ('end_plate', ((EP_X0 + EP_X1) / 2, EP_Y1, 98.0), 'z', 'y', 1, EP_T, 6.0, 8.0, 0.1),
    'zip_camera': ('shelf', (CAM_X, 30.0, Z_SH1), 'y', 'z', 1, SH_T, 3.5, 5.5, 0.1),
}
HARNESS_D = 6.0                   # wrist harness: stepper 4 + hall 3 + camera (USB) wires
HARNESS_LIFT = 0.3                # harness above the top arm's upper edge
ARM_TIES_X = (26.0, 56.0)         # ties round the top arm's upper web, through the lightening slot

def arm_top_edge():
    """Upper straight edge of the top arm (level pose): start point, unit direction, outward unit normal (x-z)."""
    a = math.asin((ARM_TOP_BOSS_R - ARM_BOSS_R) / R_ARM)
    pa = V(-ARM_TOP_BOSS_R * math.sin(a), 0, Z_PIVOT_TOP + ARM_TOP_BOSS_R * math.cos(a))
    pb = V(R_ARM - ARM_BOSS_R * math.sin(a), 0, Z_PIVOT_TOP + ARM_BOSS_R * math.cos(a))
    d = pb - pa
    d.normalize()
    return pa, d, V(-math.sin(a), 0, math.cos(a))

def arm_harness_point(x):
    """Harness centre above the top arm's upper edge at x (level pose)."""
    pa, d, n = arm_top_edge()
    p = pa + d * ((x - pa.x) / d.x)
    return p + n * (HARNESS_LIFT + HARNESS_D / 2) + V(0, (ARM_Y0 + ARM_Y1) / 2, 0)

# wrist harness paths, level pose, module coordinates: (group the point moves with, point). Built per pose in
# frame/cables.py. The leads meet at J beside the stepper, the bundle climbs the end plate's +y face between the
# pivot nuts, crosses its top edge, rides the top arm's upper edge (2 ties), leaves the arm beyond the carriage
# plate and passes under the X block to the chain post bundle. Magnet leads (they turn with the wrist) are not drawn.
J = (84.0, 36.5, 84.0)                         # junction; everything stays at y < 39.9 (parked inside zone 2)
def harness_paths():
    E, A, X = 'end', 'armT', 'xcar'
    return {
        'cable_wrist_harness': (HARNESS_D, [(E, J), (E, (80.0, 35.4, 90.0)), (E, (80.0, 35.4, 106.0)), (E, (87.5, 35.4, 113.0)),
                                            (E, (87.5, 35.4, 132.0)), (E, (82.0, 29.6, 133.5)),
                                            (A, tuple(arm_harness_point(74.0))), (A, tuple(arm_harness_point(32.0))),
                                            (X, (31.7, 8.0, 136.5)), (X, (31.7, -27.6, 136.5)), (X, (13.0, -28.5, 142.0))]),
        'cable_wrist_camera': (3.5, [(E, (CAM_X, MAG_Y, 61.3)), (E, (CAM_X, MAG_Y, 69.35)), (E, (CAM_X, 35.5, 69.35)),
                                     (E, (133.0, 37.1, 71.2)), (E, (92.0, 37.1, 71.2)), (E, J)]),     # over the camera screw head
        'cable_wrist_hall': (2.5, [(E, (HALL_POS[0], 33.8, Z_SH0 - 10.3)), (E, (HALL_POS[0], 37.6, Z_SH0 - 10.3)),     # out of the boss bottom, clear of the flag
                                   (E, (88.0, 37.6, Z_SH0 - 10.3)), (E, (HALL_LEAD_HOLE[0], HALL_LEAD_HOLE[1], Z_SH0 - 7.5)),
                                   (E, (HALL_LEAD_HOLE[0], HALL_LEAD_HOLE[1], Z_SH1 + 2.5)), (E, J)]),
        'cable_wrist_stepper': (4.0, [(E, (MAG_X, MAG_Y + N11_SQ / 2 + 2.4, 92.0)), (E, (89.5, MAG_Y + N11_SQ / 2 + 2.4, 86.0)), (E, J)]),   # VERIFY: lead exit side of the NEMA11
    }

def arm_tie(x):
    """Zip tie round the top arm's upper web (through the lightening slot) and the harness on its edge."""
    pa, d, n = arm_top_edge()
    p = pa + d * ((x - pa.x) / d.x) + V(0, (ARM_Y0 + ARM_Y1) / 2, 0)
    web = (p.z - (Z_PIVOT_TOP + 3.0 - 0.2)) / n.z + TIE_W / 2 * abs(d.z)     # down to just under the web (slot top z +3)
    return zip_tie_at(p, d, n, web, HARNESS_D, ARM_T + TIE_T + 0.2, HARNESS_LIFT)
# =============================================================================
# 6. BOUGHT PARTS AS SIMPLE SOLIDS (interference checks, viewer)
# =============================================================================
def bought():
    B = {}
    B['mgn12h_block'] = box(-BLK_L / 2, -BLK_W / 2, Z_BLOCK_FACE, BLK_L / 2, BLK_W / 2, Z_BLOCK_FACE + BLK_H).cut(
        box(-BLK_L / 2 - 1, -6.2, Z_BLOCK_FACE + 4.8, BLK_L / 2 + 1, 6.2, Z_BLOCK_FACE + BLK_H + 1))     # rail channel (rail base 5 mm inside)
    B['servo_case'] = box(SERVO_X0, CASE_TOP_Y - SERVO_CASE_H, Z_PIVOT_TOP - SERVO_W / 2, SERVO_X1, CASE_TOP_Y, Z_PIVOT_TOP + SERVO_W / 2)
    B['servo_tabs'] = box(SERVO_XC - SERVO_TAB_LEN / 2, SP_Y0 - SERVO_TAB_THK, Z_PIVOT_TOP - SERVO_W / 2,
                          SERVO_XC + SERVO_TAB_LEN / 2, SP_Y0, Z_PIVOT_TOP + SERVO_W / 2)
    B['servo_spline'] = cyl((0, CASE_TOP_Y, Z_PIVOT_TOP), 3.0, HORN_FACE_ABOVE_TOP - 2.0, 'y')
    B['servo_horn'] = cyl((0, HORN_FACE_Y - 2.0, Z_PIVOT_TOP), HORN_D / 2, 2.0, 'y')
    B['nema11'] = box(MAG_X - N11_SQ / 2, MAG_Y - N11_SQ / 2, Z_SH1, MAG_X + N11_SQ / 2, MAG_Y + N11_SQ / 2, Z_SH1 + N11_LEN)
    B['nema11_pilot'] = cyl((MAG_X, MAG_Y, Z_SH1), N11_PILOT_D / 2, -N11_PILOT_H)
    sh = cyl((MAG_X, MAG_Y, Z_SH1), N11_SHAFT_D / 2, -N11_SHAFT_LEN)
    B['nema11_shaft'] = sh.cut(box(MAG_X + N11_SHAFT_FLAT - N11_SHAFT_D / 2, MAG_Y - 3, Z_SH1 - N11_SHAFT_LEN - 1, MAG_X + 3, MAG_Y + 3, Z_SH1 + 1))
    B['electromagnet'] = cyl((MAG_X, MAG_Y, H_MID), MAG_D / 2, MAG_H)
    B['camera_board'] = box(CAM_X - CAM_BOARD / 2, MAG_Y - CAM_BOARD / 2, Z_SH0 - 4.0 - 1.6, CAM_X + CAM_BOARD / 2, MAG_Y + CAM_BOARD / 2, Z_SH0 - 4.0)
    B['camera_lens'] = cyl((CAM_X, MAG_Y, Z_SH0 - 5.6), CAM_LENS_D / 2, -11.0)
    for nm, (x, z) in {'brg_AL': (0.0, Z_PIVOT_BOT), 'brg_BT': (R_ARM, Z_PIVOT_TOP), 'brg_BL': (R_ARM, Z_PIVOT_BOT)}.items():
        B[nm] = cyl((x, ARM_Y1, z), BRG_OD / 2, -BRG_W, 'y').cut(cyl((x, ARM_Y1 + 1, z), BRG_ID / 2, -BRG_W - 2, 'y'))
    for nm, (x, z) in {'spacer_AL': (0.0, Z_PIVOT_BOT), 'spacer_BT': (R_ARM, Z_PIVOT_TOP), 'spacer_BL': (R_ARM, Z_PIVOT_BOT)}.items():
        B[nm] = cyl((x, ARM_Y1 - BRG_W, z), SPACER_OD / 2, -SPACER_L, 'y').cut(cyl((x, ARM_Y1, z), 2.1, -BRG_W - SPACER_L - 1, 'y'))
    for nm, (x, z) in {'shim_BT': (R_ARM, Z_PIVOT_TOP), 'shim_BL': (R_ARM, Z_PIVOT_BOT), 'shim_AL': (0.0, Z_PIVOT_BOT)}.items():
        B[nm] = cyl((x, ARM_Y1, z), SHIM_OD / 2, SHIM_T, 'y').cut(cyl((x, ARM_Y1 - 1, z), 2.1, SHIM_T + 2, 'y'))
    B['x_belt'] = box(CP_X0 - 30, XB_Y0, X_BELT_Z - BELT_T / 2, CP_X1 + 30, XB_Y1, X_BELT_Z + BELT_T / 2)
    for k, spec in ZIPS.items():
        B[k] = zip_tie(spec[1], *spec[2:])
    for i, x in enumerate(ARM_TIES_X):
        B['zip_arm_%d' % (i + 1)] = arm_tie(x)
    return B

GROUP = {'wrist_carriage': 'xcar', 'x_belt_riser': 'xcar', 'x_belt_clamp': 'xcar', 'chain_post': 'xcar',
         'arm_top': 'armT', 'arm_bottom': 'armB', 'end_plate': 'end', 'shelf': 'end', 'wrist_hub': 'wrist',
         'mgn12h_block': 'xcar', 'servo_case': 'xcar', 'servo_tabs': 'xcar', 'servo_spline': 'armT', 'servo_horn': 'armT',
         'nema11': 'end', 'nema11_pilot': 'end', 'nema11_shaft': 'wrist', 'electromagnet': 'wrist', 'camera_board': 'end',
         'camera_lens': 'end', 'brg_AL': 'armB', 'brg_BT': 'armT', 'brg_BL': 'armB', 'x_belt': 'xcar',
         'spacer_AL': 'xcar', 'spacer_BT': 'end', 'spacer_BL': 'end', 'shim_BT': 'end', 'shim_BL': 'end', 'shim_AL': 'xcar'}
GROUP.update({k: GROUP[spec[0]] for k, spec in ZIPS.items()})
GROUP.update({'zip_arm_%d' % (i + 1): 'armT' for i in range(len(ARM_TIES_X))})

PRINTED = {
    # name: (builder, (axis, degrees) to print orientation, how it lies, qty)
    'wrist_carriage': (wrist_carriage, (V(1, 0, 0), 180), 'block face down, servo plate up', 1),
    'x_belt_riser': (x_belt_riser, (V(1, 0, 0), 0), 'standing on its bottom face', 1),
    'x_belt_clamp': (x_belt_clamp, (V(1, 0, 0), 180), 'grooved face up', 1),
    'chain_post': (chain_post, (V(1, 0, 0), 90), 'lying on its -y face', 1),
    'arm_top': (arm_top, (V(1, 0, 0), 90), 'flat, horn face down', 1),
    'arm_bottom': (arm_bottom, (V(1, 0, 0), 90), 'flat', 1),
    'end_plate': (end_plate, (V(1, 0, 0), 90), '-y face on the bed', 1),
    'shelf': (shelf, (V(1, 0, 0), 180), 'stepper face (top) down', 1),
    'wrist_hub': (wrist_hub, (V(1, 0, 0), 180), 'shaft end down', 1),
}

def pose(shape, group, h=H_MID, wrist_deg=0.0):
    """Move a solid from the level pose to magnet face height h and wrist angle."""
    th = math.degrees(math.asin((h - H_MID) / R_ARM))
    s = shape.copy()
    if group == 'armT':
        s.rotate(V(0, 0, Z_PIVOT_TOP), V(0, -1, 0), th)
    elif group == 'armB':
        s.rotate(V(0, 0, Z_PIVOT_BOT), V(0, -1, 0), th)
    elif group in ('end', 'wrist'):
        t = math.radians(th)
        if group == 'wrist':
            s.rotate(V(MAG_X, MAG_Y, 0), V(0, 0, 1), wrist_deg)
        s.translate(V(R_ARM * math.cos(t) - R_ARM, 0, R_ARM * math.sin(t)))
    return s

def build_all():
    del FILLET_LOG[:]
    parts = {name: spec[0]() for name, spec in PRINTED.items()}
    return parts, bought()

if __name__ == '__main__':
    import os
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
    os.makedirs(out, exist_ok=True)
    parts, B = build_all()
    for name, s in parts.items():
        print('%-15s valid=%s solids=%d vol=%8.1f mm3' % (name, s.isValid(), len(s.Solids), s.Volume))
    print('edges the kernel could not fillet, per call:', FILLET_LOG)
    Part.makeCompound(list(parts.values()) + list(B.values())).exportStep(os.path.join(out, 'wrist_module_assembly.step'))
