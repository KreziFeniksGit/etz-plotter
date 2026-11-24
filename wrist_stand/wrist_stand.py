"""
Wrist test stand (FreeCAD Part script)
======================================
Holds the REAL wrist module (wrist_carriage + servo + arms + end plate + shelf + pancake stepper + magnet + camera)
at its real height over the desk, so the lift servo, the magnet, the wrist stepper, the distance sensor and the camera
can be tested before the rails and the frame exist. Not part of the plotter.

    base  - U-shaped foot with a socket for the post; the desk between its legs is the "field"
    post  - 20 x 20 bar, two zip-tie slot pairs for the wrist harness
    head  - copy of the MGN12H block's underside (3 Ruthex inserts on the block's 20 x 20 hole pattern) on an arm,
            with a socket that slips over the post top. The wrist carriage screws to it exactly as to the X block.

Coordinates = wrist module coordinates (wrist/wrist_module.py): x along the boom (0 = servo axis), y across,
z up from the desk. The head's underside is at z = W.Z_BLOCK_FACE (139), so the magnet face is at the real
h 5..40 mm above the desk and the firmware's servo pulses mean the same heights as on the plotter.

Bought parts: 3x Ruthex M3 inserts (head), 3x M3x8 (carriage to head, the plotter uses M3x6 into the block: both fit),
4x M3x12 (post to base and head, they cut their own thread in the 2.5 mm holes, try on a scrap first).
Optional: 4 wood screws (3.5 mm) through the foot corners into a board, or a clamp, if it rocks.

Run with FreeCAD's python:  ..\\fcpy.bat wrist_stand.py  -> out/*.step (print parts + assembly), out/check.json
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'wrist')]
import FreeCAD as App
import Part
import wrist_module as W
from wrist_module import box, cyl, rbox, prism_y, fillet_all, cut_all, tidy, TOL_BOLT, ZIP_SLOT, INSERT_D, INSERT_DEPTH
V = App.Vector

# ------------------------------------------------------------------ parameters (mm)
PX0, PX1, PY = -92.0, -72.0, 10.0          # post section x PX0..PX1, y -PY..PY: behind the belt riser (x >= -53)
GAP = W.SOCKET_GAP                          # per side, post in its sockets (coupon F2)
SOCK_WALL, SOCK_FLOOR, SOCK_H = 6.0, 6.0, 20.0   # base socket: wall, floor under the post, top height
BASE_T = 5.0
BASE_X0, BASE_X1, BASE_Y = -120.0, 90.0, 70.0    # foot outline (half width BASE_Y)
OPEN_X0, OPEN_Y = -40.0, 45.0                    # U opening: x from OPEN_X0, |y| < OPEN_Y (magnet at y 18.5, x 100..120)
Z_FACE = W.Z_BLOCK_FACE                     # 139: head underside = MGN12H block mounting face
PAD = (W.BLK_L / 2, 17.0, 2.0)              # pad under the arm: half x (= block), half y (block 13.5 + 3.5: 2.4 mm walls round
                                            # the inserts; covers the belt riser's place, so the riser and clamp stay off), height
ARM_T = 12.0                                # arm above the pad
Z_ARM0 = Z_FACE + PAD[2]
Z_TOP = Z_ARM0 + ARM_T                      # 153
HEAD_SOCK_D = 26.0                          # head socket depth (down over the post)
CEIL = 6.0                                  # head material over the post top
POST_Z0 = SOCK_FLOOR
POST_Z1 = Z_TOP - CEIL                      # 147
GUSSET = 20.0                               # 45 deg gusset under the arm, out from the head socket
M3_PILOT = 2.5                              # M3 cutting its own thread in PETG (camera stand uses the same, VERIFY on a scrap)
HEAD_D, HEAD_H = 6.0, 3.2                   # M3 socket head counterbore
SOCK_X0, SOCK_X1, SOCK_Y = PX0 - GAP - SOCK_WALL, PX1 + GAP + SOCK_WALL, PY + GAP + SOCK_WALL
POST_SCREWS = [((PX0 + PX1) / 2, -5.0), ((PX0 + PX1) / 2, 5.0)]
FOOT_HOLES = [(BASE_X0 + 8, -BASE_Y + 8), (BASE_X0 + 8, BASE_Y - 8), (BASE_X1 - 8, -BASE_Y + 8), (BASE_X1 - 8, BASE_Y - 8)]
POST_ZIPS = (60.0, 110.0)                   # zip-tie slot pairs through the post (along x), harness on the +x face
BLOCK_HOLES = W.BLOCK_HOLES[:3]             # the carriage uses 3 of the 4 block holes (see wrist_carriage)

def base():
    b = rbox(BASE_X0, -BASE_Y, 0, BASE_X1, BASE_Y, BASE_T, 8.0, 'z').cut(
        rbox(OPEN_X0, -OPEN_Y, -1, BASE_X1 + 20, OPEN_Y, BASE_T + 1, 8.0, 'z'))
    b = b.fuse(box(SOCK_X0, -SOCK_Y, 0, SOCK_X1, SOCK_Y, SOCK_H))
    b = fillet_all(tidy(b))
    cuts = [rbox(PX0 - GAP, -PY - GAP, SOCK_FLOOR, PX1 + GAP, PY + GAP, SOCK_H + 1, 0.5, 'z')]
    for x, y in POST_SCREWS:
        cuts += [cyl((x, y, -1), (3.0 + TOL_BOLT) / 2, SOCK_FLOOR + 2), cyl((x, y, -1), HEAD_D / 2, HEAD_H + 1)]
    for x, y in FOOT_HOLES:
        cuts.append(cyl((x, y, -1), 3.8 / 2, BASE_T + 2))
    for x in (OPEN_X0 - 12, OPEN_X0 - 24):          # zip-tie slots for the harness to the breadboard, beside the socket
        cuts.append(rbox(x - ZIP_SLOT[1] / 2, SOCK_Y + 4, -1, x + ZIP_SLOT[1] / 2, SOCK_Y + 4 + ZIP_SLOT[0], BASE_T + 1, 0.6, 'z'))
    return fillet_all(cut_all(b, cuts), r_in=0.5, r_out=0.5)

def post():
    p = fillet_all(box(PX0, -PY, POST_Z0, PX1, PY, POST_Z1), r_in=1.5, r_out=0.6)
    cuts = []
    for x, y in POST_SCREWS:
        cuts += [cyl((x, y, POST_Z0 - 1), M3_PILOT / 2, 13.0), cyl((x, y, POST_Z1 + 1), M3_PILOT / 2, -13.0)]
    for z in POST_ZIPS:                              # two slots either side of the harness, through along x
        for sy in (-1, 1):
            yc = sy * 4.5
            cuts.append(rbox(PX0 - 1, yc - ZIP_SLOT[1] / 2, z - ZIP_SLOT[0] / 2, PX1 + 1, yc + ZIP_SLOT[1] / 2, z + ZIP_SLOT[0] / 2, 0.6, 'x'))
    return cut_all(p, cuts)

def head():
    hy = max(SOCK_Y, PAD[1])                                                                    # as wide as the arm: no step
    s = box(SOCK_X0, -hy, Z_TOP - HEAD_SOCK_D - CEIL, SOCK_X1, hy, Z_TOP)                      # socket block
    s = s.fuse(box(SOCK_X1 - 1, -PAD[1], Z_ARM0, PAD[0], PAD[1], Z_TOP))                        # arm
    s = s.fuse(box(-PAD[0], -PAD[1], Z_FACE, PAD[0], PAD[1], Z_ARM0))                           # block pad
    zg = Z_TOP - HEAD_SOCK_D - CEIL
    g = min(GUSSET, Z_ARM0 - zg)
    s = s.fuse(prism_y([(SOCK_X1 - 1, Z_ARM0 + 0.01), (SOCK_X1 - 1, Z_ARM0 - g), (SOCK_X1 + g, Z_ARM0 + 0.01)], -PAD[1], PAD[1]))
    s = fillet_all(tidy(s), r_in=1.5)
    cuts = [rbox(PX0 - GAP, -PY - GAP, zg - 1, PX1 + GAP, PY + GAP, POST_Z1, 0.5, 'z')]
    for x, y in POST_SCREWS:
        cuts += [cyl((x, y, POST_Z1 - 1), (3.0 + TOL_BOLT) / 2, CEIL + 2), cyl((x, y, Z_TOP - HEAD_H), HEAD_D / 2, HEAD_H + 1)]
    for x, y in BLOCK_HOLES:                         # inserts from below, like the MGN12H block's threads
        cuts.append(cyl((x, y, Z_FACE - 0.01), INSERT_D / 2, INSERT_DEPTH))
    for x in (SOCK_X1 + 8, SOCK_X1 + 20):            # zip-tie slots on the arm (harness along x, over the arm)
        for sy in (-1, 1):
            yc = sy * (PAD[1] - 4.0)
            cuts.append(rbox(x - ZIP_SLOT[0] / 2, yc - ZIP_SLOT[1] / 2, Z_ARM0 - 1, x + ZIP_SLOT[0] / 2, yc + ZIP_SLOT[1] / 2, Z_TOP + 1, 0.6, 'z'))
    return fillet_all(cut_all(s, cuts), r_in=0.5, r_out=0.5)

# ------------------------------------------------------------------ the real wrist, for the checks
SKIP = ('mgn12h_block', 'x_belt', 'x_belt_riser', 'x_belt_clamp', 'chain_post', 'zip_chain_post_1', 'zip_chain_post_2')   # not on the stand
MASS_G = {'servo_case': 55, 'servo_horn': 8, 'nema17p': 140, 'electromagnet': 35, 'camera_board': 8, 'camera_lens': 4,
          'tof_board': 2}                    # same grams as tools/stability.py; other bought bits ~0

def wrist_parts():
    parts, B = W.build_all()
    allp = {k: (s, W.GROUP.get(k, 'xcar'), True) for k, s in parts.items()}
    allp.update({k: (s, W.GROUP.get(k, 'xcar'), False) for k, s in B.items()})
    return {k: v for k, v in allp.items() if k not in SKIP}

def grams(name, s, printed):
    if printed:
        return s.Volume / 1000.0 * 1.27 * 0.65       # PETG, 4 walls 40 % gyroid (as tools/stability.py)
    return MASS_G.get(name, 0.0)

if __name__ == '__main__':
    import dfm
    out = os.path.join(HERE, 'out')
    os.makedirs(out, exist_ok=True)
    parts = {'base': base(), 'post': post(), 'head': head()}
    printing = {'base': dfm.orient(parts['base'], V(1, 0, 0), 0),
                'post': dfm.orient(parts['post'], V(0, 1, 0), 90),      # lies on its x face, zip slots vertical
                'head': dfm.orient(parts['head'], V(1, 0, 0), 180)}     # top face down, socket opening up
    R = {}
    for k, s in printing.items():
        s.exportStep(os.path.join(out, 'wrist_stand_%s.step' % k))
        r = dfm.report(s, parts[k])
        R[k] = {kk: r[kk] for kk in ('size', 'fits_220', 'mass_g', 'min_wall', 'thin_samples', 'steep_overhang_mm2',
                                     'widest_bridge_mm', 'n_sharp', 'sharp_internal_edges', 'thin_examples')}
        R[k]['valid'] = s.isValid()
        print(k, R[k])
    stand = Part.makeCompound(list(parts.values()))
    R['stand_clash_mm3'] = {a + '/' + b: round(parts[a].common(parts[b]).Volume, 3)
                            for a, b in (('base', 'post'), ('base', 'head'), ('post', 'head'))}
    # wrist over the lift range and wrist angles: nothing may touch the stand (the carriage only touches the pad face)
    WP = wrist_parts()
    worst, clear = {}, {}
    for h in (W.H_MIN, 10.0, W.H_MID, 30.0, W.H_MAX):
        for wd in (0.0, 90.0, 180.0, 270.0):
            for k, (s, g, pr) in WP.items():
                ps = W.pose(s, g, h, wd)
                for sk, ss in parts.items():
                    v = ps.common(ss).Volume
                    if v > 1e-3:
                        worst['%s/%s h%g w%g' % (k, sk, h, wd)] = round(v, 3)
    for k, (s, g, pr) in WP.items():                # smallest gap at the lowest and highest lift
        d = min(W.pose(s, g, hh, 0.0).distToShape(stand)[0] for hh in (W.H_MIN, W.H_MAX))
        if d < 5.0:
            clear[k] = round(d, 2)
    R['wrist_vs_stand_mm3'] = worst
    R['wrist_gap_under_5mm'] = clear
    # magnet face height and tipping (no screws to a board)
    mag = W.pose(WP['electromagnet'][0], 'wrist', W.H_MIN, 0).BoundBox.ZMin
    R['magnet_face_h_range'] = [round(mag, 2), round(W.pose(WP['electromagnet'][0], 'wrist', W.H_MAX, 0).BoundBox.ZMin, 2)]
    tip = {}
    for h in (W.H_MIN, W.H_MAX):
        M, mx, my = 0.0, 0.0, 0.0
        for k, (s, g, pr) in WP.items():
            m = grams(k, s, pr)
            c = W.pose(s, g, h, 0).CenterOfMass if hasattr(s, 'CenterOfMass') else s.BoundBox.Center
            M += m; mx += m * c.x; my += m * c.y
        wm = M
        for k, s in parts.items():
            m = grams(k, s, True)
            c = s.CenterOfMass
            M += m; mx += m * c.x; my += m * c.y
        cx, cy = mx / M, my / M
        margin = min(cx - BASE_X0, BASE_X1 - cx, cy + BASE_Y, BASE_Y - cy)   # foot outline is a rectangle (U legs reach BASE_X1)
        tip['h%g' % h] = {'wrist_g': round(wm), 'total_g': round(M), 'com_xy': [round(cx, 1), round(cy, 1)], 'edge_margin_mm': round(margin, 1)}
    R['tipping'] = tip
    R['fillets_skipped'] = sum(W.FILLET_LOG)
    print('stand clash', R['stand_clash_mm3'], 'wrist vs stand', worst, 'gaps', clear)
    print('magnet h', R['magnet_face_h_range'], 'tipping', tip)
    # assembly STEP: stand + wrist at h 22.5 (level arms)
    asm = [parts['base'], parts['post'], parts['head']] + [W.pose(s, g, W.H_MID, 0) for k, (s, g, pr) in WP.items()]
    Part.makeCompound(asm).exportStep(os.path.join(out, 'wrist_stand_assembly.step'))
    json.dump(R, open(os.path.join(out, 'check.json'), 'w'), indent=1)
