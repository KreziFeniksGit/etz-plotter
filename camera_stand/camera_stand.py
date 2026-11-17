"""
Camera test stand (FreeCAD Part script)
=======================================
Holds the webcam board over the field at an adjustable height, so the vision code can be written and tested
before the plotter exists. Not part of the plotter.

    base   - foot plate with a socket for the post; stands on the field
    post   - 20 x 10 bar with a long slot (height adjust) and a notch every 10 mm (height scale)
    slider - rides on the post, clamped by one M3 bolt through the slot; its arm ends in a blank camera plate.
             The camera board (taken out of the Sandberg Flex 1080P case) is screwed UNDER the plate, lens down.
             The plate has no screw holes: drill them to match the board (top grooves mark the plate centre).

Bought parts: M3x20 bolt + M3 nut + 2 washers (clamp), 2x M3x12 (post to base, cut their own thread in the post).
Plate underside height above the table: 20 mm (slider on the socket) .. 88 mm (bolt at the slot top).
On the plotter the lens is 30..65 mm above the field: test there first.

Run with FreeCAD's python:  ..\\fcpy.bat camera_stand.py   -> out/*.step (print parts + assembly), out/dfm.json
Print parts are exported in print orientation (flat on z = 0).
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'wrist')]
import FreeCAD as App
import Part
import wrist_module as W
from wrist_module import box, cyl, rbox, slot, fillet_all, cut_all, tidy, TOL_BOLT, TOL_MOVE, ZIP_SLOT
V = App.Vector

# ------------------------------------------------------------------ parameters (mm)
POST_W, POST_T, POST_L = 20.0, 10.0, 110.0     # post section (y, x) and length: covers the wrist camera heights (lens 30..65)
BASE_X0, BASE_X1, BASE_Y, BASE_T = -110.0, 5.0, 40.0, 5.0   # foot plate (half width BASE_Y), behind the post
SOCK_H, SOCK_WALL, SOCK_FLOOR = 20.0, 6.0, 6.0  # post socket block: top height, wall, floor under the post
SOCK_GAP = W.SOCKET_GAP                         # per side, post in its socket (coupon F2)
M3_PILOT = 2.5                                  # M3 machine screw cutting its own thread in PETG (common practice, VERIFY on a scrap)
HEAD_D, HEAD_H = 6.0, 3.2                       # M3 socket head counterbore (from below)
SLOT_Z0, SLOT_Z1 = 30.0, 110.0                  # clamp slot in the post, absolute z
SLOT_W = 3.0 + TOL_MOVE                         # M3 bolt slides in it
NOTCH = (1.2, 0.6)                              # height scale notch width x depth (round groove r 0.6), every 10 mm on the +y face
SL_H, SL_FRONT, SL_WALL = 35.0, 4.4, 2.6        # slider height, front wall, side walls
SL_GAP = TOL_MOVE / 2                           # per side, slider on the post
BOLT_Z = 22.0                                   # clamp bolt above the slider bottom
ARM_T, ARM_X1 = 6.0, 50.0                       # arm thickness, end (x from the post front face); width = slider width
PLATE_X, PLATE_Y, PLATE_T = 70.0, 50.0, 3.0     # blank camera plate, starts at ARM_X1
GROOVE = (1.2, 0.6)                             # centre-mark grooves on the plate top (round, r 0.6)
# Camera: Sandberg USB Webcam Flex 1080P HD (133-97), fixed focus, 72 deg horizontal FOV (retailer spec, VERIFY).
# The board inside is NOT measured: placeholder only. Egor measures it when it is out of the case.
CAM_PCB = (60.0, 22.0, 1.6)                     # VERIFY: board size
CAM_LENS = (8.0, 7.0)                           # VERIFY: lens holder diameter, height under the board
PLATE_CX = ARM_X1 + PLATE_X / 2                 # camera centre, x from the post front face

# post: x -POST_T..0, y -POST_W/2..POST_W/2; the arm points to +x.
POST_Z0 = SOCK_FLOOR
SOCK = (-POST_T - SOCK_GAP - SOCK_WALL, SL_FRONT + SL_GAP, POST_W / 2 + SOCK_GAP + SOCK_WALL)   # x0, x1, half y
BASE_SCREWS = [(-POST_T / 2, -5.0), (-POST_T / 2, 5.0)]

def base():
    b = rbox(BASE_X0, -BASE_Y, 0, BASE_X1, BASE_Y, BASE_T, 6.0, 'z')
    b = b.fuse(box(SOCK[0], -SOCK[2], 0, SOCK[1], SOCK[2], SOCK_H))
    b = fillet_all(tidy(b))
    g = SOCK_GAP
    cuts = [rbox(-POST_T - g, -POST_W / 2 - g, SOCK_FLOOR, g, POST_W / 2 + g, SOCK_H + 1, 0.5, 'z')]   # post edges are r 0.6
    for x, y in BASE_SCREWS:
        cuts += [cyl((x, y, -1), (3.0 + TOL_BOLT) / 2, SOCK_FLOOR + 2), cyl((x, y, -1), HEAD_D / 2, HEAD_H + 1)]
    return fillet_all(cut_all(b, cuts), r_in=0.5, r_out=0.5)      # pocket floor corners (post edges are r 0.6)

def post():
    p = fillet_all(box(-POST_T, -POST_W / 2, POST_Z0, 0, POST_W / 2, POST_Z0 + POST_L), r_in=1.5, r_out=0.6)
    cuts = [slot((-POST_T - 1, 0, SLOT_Z0), (-POST_T - 1, 0, SLOT_Z1), SLOT_W / 2, POST_T + 2, 'x')]
    for x, y in BASE_SCREWS:
        cuts.append(cyl((x, y, POST_Z0 - 1), M3_PILOT / 2, 13.0))
    for z in range(30, int(POST_Z0 + POST_L), 10):      # notch at every 10 mm of plate height (z of the slider bottom)
        cuts.append(cyl((-POST_T - 1, POST_W / 2, z), NOTCH[1], POST_T + 2, 'x'))      # round groove, no sharp corner
    return cut_all(p, cuts)

def slider(z=SOCK_H):
    g, yo = SL_GAP, POST_W / 2 + SL_GAP + SL_WALL
    s = box(-POST_T + 1.0, -yo, z, SL_FRONT + g, yo, z + SL_H)               # around the post, open at the back
    s = s.fuse(box(0, -yo, z, ARM_X1 + 1, yo, z + ARM_T))                    # arm, as wide as the slider
    s = s.fuse(rbox(ARM_X1, -PLATE_Y / 2, z, ARM_X1 + PLATE_X, PLATE_Y / 2, z + PLATE_T, 5.0, 'z'))
    s = fillet_all(tidy(s), r_in=1.0)
    cuts = [rbox(-POST_T - 1, -POST_W / 2 - g, z - 1, g, POST_W / 2 + g, z + SL_H + 1, 0.5, 'z'),
            cyl((-1, 0, z + BOLT_Z), (3.0 + TOL_BOLT) / 2, SL_FRONT + 3, 'x')]
    for xz in (ARM_X1 - 22, ARM_X1 - 10):                                     # zip-tie slots for the USB cable
        for sy in (-1, 1):
            yc = sy * (yo - 4.5)
            cuts.append(rbox(xz - ZIP_SLOT[1] / 2, yc - ZIP_SLOT[0] / 2, z - 1, xz + ZIP_SLOT[1] / 2, yc + ZIP_SLOT[0] / 2, z + ARM_T + 1, 0.6, 'z'))
    cx, w, d = PLATE_CX, GROOVE[0] / 2, GROOVE[1]
    cuts += [cyl((cx, -PLATE_Y / 2 + 4, z + PLATE_T), d, PLATE_Y - 8, 'y'),        # round grooves (r = depth)
             cyl((ARM_X1 + 4, 0, z + PLATE_T), d, PLATE_X - 8, 'x')]
    return cut_all(s, cuts)

def camera(z=SOCK_H):
    """Placeholder webcam board under the plate, lens down (VERIFY all sizes)."""
    L, Wd, T = CAM_PCB
    pcb = box(PLATE_CX - L / 2, -Wd / 2, z - T, PLATE_CX + L / 2, Wd / 2, z)
    return pcb.fuse(cyl((PLATE_CX, 0, z - T), CAM_LENS[0] / 2, -CAM_LENS[1]))

def lens_height(z_slider):
    """Lens tip above the table for a slider bottom at z (with the placeholder sizes)."""
    return z_slider - CAM_PCB[2] - CAM_LENS[1]

if __name__ == '__main__':
    import dfm
    out = os.path.join(HERE, 'out')
    os.makedirs(out, exist_ok=True)
    z_show = 40.0
    parts = {'base': base(), 'post': post(), 'slider': slider(z_show)}
    printing = {'base': dfm.orient(parts['base'], V(1, 0, 0), 0),
                'post': dfm.orient(parts['post'], V(0, 1, 0), 90),      # lies on its 20 mm face, slot vertical
                'slider': dfm.orient(parts['slider'], V(1, 0, 0), 0)}
    R = {}
    for k, s in printing.items():
        s.exportStep(os.path.join(out, 'camera_stand_%s.step' % k))
        r = dfm.report(s, parts[k])
        R[k] = {kk: r[kk] for kk in ('size', 'fits_220', 'mass_g', 'min_wall', 'thin_samples', 'steep_overhang_mm2',
                                     'widest_bridge_mm', 'n_sharp', 'sharp_internal_edges', 'thin_examples')}
        R[k]['valid'] = s.isValid()
        print(k, R[k])
    cam = camera(z_show)
    asm = Part.makeCompound([parts['base'], parts['post'], parts['slider'], cam])
    asm.exportStep(os.path.join(out, 'camera_stand_assembly.step'))
    clash = {a + '/' + b: round(parts[a].common(parts[b]).Volume, 3) for a, b in (('base', 'post'), ('base', 'slider'), ('post', 'slider'))}
    clash['camera/slider'] = round(cam.common(parts['slider']).Volume, 3)
    R['interference_mm3'] = clash
    R['plate_underside_range'] = [SOCK_H, SLOT_Z1 - BOLT_Z]
    R['lens_tip_range_placeholder'] = [round(lens_height(SOCK_H), 1), round(lens_height(SLOT_Z1 - BOLT_Z), 1)]
    R['fillets_skipped'] = sum(W.FILLET_LOG)
    print('interference', clash, 'lens tip', R['lens_tip_range_placeholder'])
    json.dump(R, open(os.path.join(out, 'dfm.json'), 'w'), indent=1)
