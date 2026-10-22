"""
ETZ plotter v2: cable chains (FreeCAD Part script)
=================================================
Two 10 x 15 mm cable chains (inner 10 high x 15 wide, outer 15 x 23, bend radius R18,
total bend height 51 mm: vxb.com data for the generic 10x15 R18 open chain).

  X chain: lies on top of the boom. Fixed end on the boom top (2 M3 drop-in T-nuts),
           lower run rests on the boom, U-bend toward +X, upper run back to the moving
           end on top of the wrist module's chain post.
  Y chain: lies in a printed guide on the plywood (y_chain_guide). Fixed end in the guide
           (2 zip ties), lower run in the guide, U-bend toward +Y, upper run back to the
           moving end on top of the Y carriage (M3 + nut in a slot).

Both chains are built for a given pose: the bend sits where the chain length says it must.
    u_bend = (L - pi R + u_fixed + u_moving) / 2      (moves at half the carriage speed)
"""
import math
import FreeCAD as App
import Part
from wrist_module import box, cyl, slot, zip_pair, fillet_all, cut_all, tidy, bolt, rbox, TOL_MOVE, WALL_MIN

V = App.Vector

# =============================================================================
# 1. CHAIN PARAMETERS (generic 10x15 R18 open chain)
# =============================================================================
CH_W, CH_H = 23.0, 15.0           # outer width, outer height
CH_WI, CH_HI = 15.0, 10.0         # inner width, inner height (cable space)
CH_R = 18.0                       # bend radius at the chain centre line (2R + H = 51 mm total bend height)
CH_P = 17.5                       # link pitch   VERIFY on the chain you buy (only changes the drawing)
CH_GAP = 0.8                      # drawn gap between links
CH_END_L = 20.0                   # end link length   VERIFY

# =============================================================================
# 2. X CHAIN LAYOUT (world X along the boom, at y = PYC)
# =============================================================================
Z_BOOM_TOP = 172.0
XC_V_LOW = Z_BOOM_TOP + CH_H / 2          # lower run centre (rests on the boom)
XC_FIX_U = 250.0                          # fixed end link x 230..250 (corner bracket ends at x 229)
XC_MOVE_DX = 25.0                         # moving end = PXB + 25 (end link x PXB+5..PXB+25 on the chain post)
XC_L = 280.0                              # chain length between the end links (cut to whole links)
XC_POST_TOP = XC_V_LOW + 2 * CH_R - CH_H / 2   # 208: top of the chain post plate

# =============================================================================
# 3. Y CHAIN LAYOUT (world Y, in the lane x = YC_LANE_X)
# =============================================================================
GUIDE_BOLTS_Y = (250.0, 300.0, 350.0, 405.0)  # Y chain guide through-bolts
YC_LANE_X = 235.5                       # between the Y beam (x <= 215) and the electronics board (x >= 246, y <= 210)
Z_PLY1 = 15.0
Z_CARRIAGE_TOP = 68.0                     # Y carriage top (frame.Z_YC1, checked there)
GUIDE_FLOOR = Z_CARRIAGE_TOP - Z_PLY1 - 2 * CH_R    # 17: raises the lower run so the upper run meets the carriage top
GUIDE_WALL_H = 8.0
YC_V_LOW = Z_PLY1 + GUIDE_FLOOR + CH_H / 2
YC_FIX_U = 236.0                          # fixed end link y 216..236
YC_MOVE_DY = 30.0                         # moving end = PYC + 30 (carriage +y edge), end link y PYC+10..PYC+30
YC_L = 250.0
GUIDE_Y0, GUIDE_Y1 = 213.0, 421.0         # 208 mm: fits the 220 bed

def bend_u(L, u_fix, u_move):
    return (L - math.pi * CH_R + u_fix + u_move) / 2

# =============================================================================
# 4. CHAIN SOLIDS
# =============================================================================
def _path_point(s, u_fix, u_b, v_low):
    """Point and tangent angle at arc length s from the fixed end (lower run first)."""
    L1 = u_b - u_fix
    La = math.pi * CH_R
    if s <= L1:
        return u_fix + s, v_low, 0.0
    if s <= L1 + La:
        phi = -math.pi / 2 + (s - L1) / CH_R
        return u_b + CH_R * math.cos(phi), v_low + CH_R + CH_R * math.sin(phi), phi + math.pi / 2
    return u_b - (s - L1 - La), v_low + 2 * CH_R, math.pi

def _link(length, inner=True):
    """Link in local coordinates: x along the chain (0..length), y across, z up, centred on y and z."""
    s = box(0, -CH_W / 2, -CH_H / 2, length, CH_W / 2, CH_H / 2)
    if inner:
        s = s.cut(box(-1, -CH_WI / 2, -CH_HI / 2, length + 1, CH_WI / 2, CH_HI / 2))
    return s

def chain_solid(L, u_fix, u_move, v_low, end_links=True):
    """All links of one chain in the local (u, w, v) frame = (x, y, z). Returns (compound, u_bend)."""
    u_b = bend_u(L, u_fix, u_move)
    if u_b < u_move - 1e-6:
        raise ValueError('chain too short: bend %.1f behind the moving end %.1f' % (u_b, u_move))
    links = []
    s = 0.0
    while s < L - 1e-6:
        ln = min(CH_P, L - s) - CH_GAP
        if ln > 1.0:
            u0, v0, a0 = _path_point(s, u_fix, u_b, v_low)
            u1, v1, a1 = _path_point(s + ln, u_fix, u_b, v_low)
            ang = math.atan2(v1 - v0, u1 - u0)
            lk = _link(math.hypot(u1 - u0, v1 - v0))
            lk.rotate(V(0, 0, 0), V(0, 1, 0), -math.degrees(ang))
            lk.translate(V(u0, 0, v0))
            links.append(lk)
        s += CH_P
    if end_links:
        fe = _link(CH_END_L, inner=False).cut(box(-1, -CH_WI / 2, -CH_HI / 2 + 2.0, CH_END_L + 1, CH_WI / 2, CH_HI / 2 + 4))
        fe.translate(V(u_fix - CH_END_L, 0, v_low))
        me = _link(CH_END_L, inner=False).cut(box(-1, -CH_WI / 2, -CH_HI / 2 + 2.0, CH_END_L + 1, CH_WI / 2, CH_HI / 2 + 4))   # floor 4.5 mm, screwed from inside
        me.translate(V(u_move - CH_END_L, 0, v_low + 2 * CH_R))
        links += [fe, me]
    return Part.makeCompound(links), u_b

def x_chain(PYC, PXB):
    u_move = PXB + XC_MOVE_DX
    c, u_b = chain_solid(XC_L, XC_FIX_U, u_move, XC_V_LOW)
    c.translate(V(0, PYC, 0))
    return c, u_b

def y_chain(PYC):
    u_move = PYC + YC_MOVE_DY
    c, u_b = chain_solid(YC_L, YC_FIX_U, u_move, YC_V_LOW)
    # local x -> world +y, local y -> world -x: rotate +90 deg about z, then move to the lane
    c.rotate(V(0, 0, 0), V(0, 0, 1), 90)
    c.translate(V(YC_LANE_X, 0, 0))
    return c, u_b

# =============================================================================
# 5. PRINTED PART: Y CHAIN GUIDE (on the plywood)
# =============================================================================
def y_chain_guide():
    """U-channel under the lower run of the Y chain. The 7 mm floor lifts the chain so the
    upper run meets the carriage top. Fixed end held by two zip ties; four M3 through-bolts
    in counterbores (heads below the floor top, nuts under the plywood). Prints floor down."""
    xc = YC_LANE_X
    half_in = CH_W / 2 + TOL_MOVE + 0.1         # 0.5 mm side play
    wall = WALL_MIN + 0.6
    x0, x1 = xc - half_in - wall, xc + half_in + wall
    z0, zf, zt = Z_PLY1, Z_PLY1 + GUIDE_FLOOR, Z_PLY1 + GUIDE_FLOOR + GUIDE_WALL_H
    ear = 4.0                                    # thicker walls at the fixed end carry the zip-tie slots
    body = box(x0, GUIDE_Y0, z0, x1, GUIDE_Y1, zt).fuse(box(x0 - ear, GUIDE_Y0, z0, x1 + ear, GUIDE_Y0 + 25.0, zt))
    body = fillet_all(tidy(body))
    # channel with a round inside edge along the floor (no sharp corner)
    chan = rbox(xc - half_in, GUIDE_Y0 - 1, zf, xc + half_in, GUIDE_Y1 + 1, zt + 1, 1.0, 'y')
    body = body.cut(chan)
    # lightening pockets from below (open to the bed): 9 mm wide roofs bridge, 3 mm skin under the chain
    cut = []
    pk_h = GUIDE_FLOOR - 3.0
    for xs in (xc - 6.0, xc + 6.0):
        for ya, yb in ((258.0, 292.0), (308.0, 342.0), (358.0, 397.0)):
            t = box(xs - 4.5, ya, z0 - 1, xs + 4.5, yb, z0 + pk_h)
            t = t.makeFillet(1.0, [e for e in t.Edges if e.BoundBox.ZMin > z0 - 0.5 or e.BoundBox.ZLength > 1])
            cut.append(t)
    for y in GUIDE_BOLTS_Y:                          # M3x25 button bolts (head 1.65), seat 2.5 mm down, nut under the plywood
        cut.append(cyl((xc, y, z0 - 1), bolt(3) / 2, GUIDE_FLOOR + 2))
        cut.append(cyl((xc, y, zf - 2.5), (7.0 + 2 * TOL_MOVE) / 2, 4.0))      # button head 1.65 mm: top 0.85 under the floor
    for y in (220.0, 231.0):                         # zip ties around the fixed end link: down a wall, under the floor, up the other wall
        for s in (-1, 1):
            xs = xc + s * (half_in + (wall + ear) / 2)
            cut.append(slot((xs, y - (3.0 - 1.8) / 2 - 0.3, z0 - 1), (xs, y + (3.0 - 1.8) / 2 + 0.3, z0 - 1), 0.9 + 0.2, GUIDE_FLOOR + GUIDE_WALL_H + 2))
        cut.append(cyl((x0 - ear - 1, y, z0), 1.4, x1 - x0 + 2 * ear + 2, 'x'))     # half-round groove under the floor
    return cut_all(body, cut)
