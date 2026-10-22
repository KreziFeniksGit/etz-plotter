"""
ETZ plotter v2: every screw, nut, washer, heat-set insert and T-nut as a solid (FreeCAD Part script)
==================================================================================================
Each fastener is placed where the model's holes are. The check (assembly.fastener_check) then makes sure
  - no head, nut, washer or shank cuts into a part it should not touch (holes exist, nothing clips),
  - the thread engages enough: insert >= 4 mm, T-nut >= 3 mm (M3: 2.5), nut fully, tapped metal >= its minimum,
  - blind screws end inside their target (not bottoming out, not poking out of the far side).

Coordinates: wrist fasteners in wrist-module coordinates (x from PXB, y from PYC, absolute z) with their
motion group; Y-carriage fasteners at the parked Y (PYC0 = 40); base fasteners in world coordinates.
Head shapes: ISO 4762 cap, ISO 7380 button, ISO 10642 countersunk, pan (wood screws, M2 self-tapping).
"""
import math
import FreeCAD as App
import Part

V = App.Vector

HEAD = {'cap': {2: (3.8, 2.0), 2.5: (4.5, 2.5), 3: (5.5, 3.0), 4: (7.0, 4.0), 5: (8.5, 5.0)},
        'button': {2.5: (4.7, 1.5), 3: (5.7, 1.65), 4: (7.6, 2.2), 5: (9.5, 2.75)},
        'csk': {3: (6.0, 1.7), 4: (8.0, 2.3), 5: (10.0, 2.8)},
        'pan': {2: (3.8, 1.6), 3.5: (7.0, 2.4), 4: (8.0, 2.8)},
        'set': {3: (0.0, 0.0)}}                      # ISO 4026 set screw (no head)
NUT = {'hex': {2: (4.0, 1.6), 2.5: (5.0, 2.0), 3: (5.5, 2.4), 4: (7.0, 3.2), 5: (8.0, 4.0)},
       'nyloc': {2: (4.0, 3.0), 3: (5.5, 4.0), 4: (7.0, 5.0), 5: (8.0, 5.0)}}
WASHER = {2: (6.0, 0.8), 3: (7.0, 0.5), 4: (9.0, 0.8), 5: (10.0, 1.0)}   # M2: DIN 9021 large washer (covers the 4.5 servo tab hole)
WOOD_MIN = 4.0                                 # wood screw engagement in the 6 mm plywood (none may come out underneath)
INSERT_L, INSERT_D = 5.7, 4.0                  # Ruthex RX-M3x5.7 (drawn solid: its thread is what the screw engages)
TNUT_W, TNUT_L, TNUT_T, TNUT_DEPTH = 5.8, 9.5, 3.5, 1.8   # 2020 V-slot drop-in T-nut, under the lips (frame.VSLOT_LIP = 1.8); fits the 11 mm cavity

def _perp(d):
    a = V(1, 0, 0) if abs(d.x) < 0.9 else V(0, 1, 0)
    u = d.cross(a); u.normalize()
    w = d.cross(u); w.normalize()
    return u, w

def _cyl(p, d, r, L):
    return Part.makeCylinder(r, L, p, d)

def _hex(p, d, af, m):
    u, w = _perp(d)
    R = af / math.sqrt(3)
    pts = [p + u * (R * math.cos(math.radians(30 + 60 * k))) + w * (R * math.sin(math.radians(30 + 60 * k))) for k in range(6)]
    return Part.Face(Part.makePolygon(pts + [pts[0]])).extrude(d * m)

def _obox(c, d, axis, t, L, W):
    """Box centred on c: thickness t along d, length L along axis, width W across."""
    ax = V(*axis); ax.normalize()
    acr = d.cross(ax); acr.normalize()
    p0 = c - d * (t / 2) - ax * (L / 2) - acr * (W / 2)
    pts = [p0, p0 + ax * L, p0 + ax * L + acr * W, p0 + acr * W, p0]
    return Part.Face(Part.makePolygon(pts)).extrude(d * t)

class F:
    """One fastener. p = the surface the head (or its washer) sits on; d = direction from head to tip.
    For countersunk heads p is the flush top of the head."""
    def __init__(self, name, std, dia, L, p, d, group, target, extra=(), head_washer=False, nut=None, nut_washer=False,
                 insert=None, tnut=None, note=''):
        self.name, self.std, self.dia, self.L, self.group, self.extra, self.note = name, std, dia, L, group, tuple(extra), note
        self.p, self.d = V(*p), V(*d)
        self.d.normalize()
        self.target = target              # (kind, prefix or None, min engagement, max engagement or None)
        self.head_washer, self.nut, self.nut_washer, self.insert, self.tnut = head_washer, nut, nut_washer, insert, tnut

    def label(self):
        n = {'cap': 'ISO 4762', 'button': 'ISO 7380', 'csk': 'ISO 10642', 'pan': 'pan head', 'set': 'ISO 4026 set screw'}[self.std]
        if self.std == 'pan' and self.dia == 2:
            return 'M2 x %g pan head self-tapping' % self.L
        if self.std == 'pan' and self.dia in (3.5, 4):
            return 'wood screw %gx%g (pan head)' % (self.dia, self.L)
        return 'M%g x %g %s' % (self.dia, self.L, n)

    def pieces(self):
        """{suffix: (shape, allowed prefixes)}"""
        p, d, r = self.p, self.d, self.dia / 2
        own = self.name + '_'
        out = {}
        D, H = HEAD[self.std][self.dia]
        if self.std == 'set':
            out['shank'] = (_cyl(p, d, r, self.L), None)
            self.s0 = p
            self.len_shank = self.L
        elif self.std == 'csk':
            out['head'] = (Part.makeCone(D / 2, r, H, p, d), (own,))
            out['shank'] = (_cyl(p + d * H, d, r, self.L - H), None)
            self.s0 = p + d * H
            self.len_shank = self.L - H
        else:
            q = p
            if self.head_washer:
                wd, wt = WASHER[self.dia]
                out['washer'] = (_cyl(p - d * wt, d, wd / 2, wt).cut(_cyl(p - d * (wt + 1), d, r + 0.2, wt + 2)), (own,))
                q = p - d * wt
            out['head'] = (_cyl(q - d * H, d, D / 2, H), (own,))
            out['shank'] = (_cyl(q, d, r, self.L), None)
            self.s0 = q
            self.len_shank = self.L
        if self.nut:
            kind, at = self.nut
            a = p + d * at
            if self.nut_washer:
                wd, wt = WASHER[self.dia]
                out['nutwasher'] = (_cyl(a, d, wd / 2, wt).cut(_cyl(a - d, d, r + 0.2, wt + 2)), (own,))
                a = a + d * wt
            af, m = NUT[kind][self.dia]
            out['nut'] = (_hex(a, d, af, m), (own,))
            self.nut_m = m
        if self.insert:
            host, at = self.insert
            out['insert'] = (_cyl(p + d * at, d, INSERT_D / 2, INSERT_L), (own, host))
        if self.tnut:
            surf, axis, profile = self.tnut
            c = p + d * (surf + TNUT_DEPTH + TNUT_T / 2)
            out['tnut'] = (_obox(c, d, axis, TNUT_T, TNUT_L, TNUT_W), (own,))
        # what the shank may touch
        allow = [own] + list(self.extra)
        kind, pref = self.target[0], self.target[1]
        if pref:
            allow.append(pref)
        out['shank'] = (out['shank'][0], tuple(allow))
        return out

    def target_name(self):
        k = self.target[0]
        if k == 'insert':
            return self.name + '_insert'
        if k == 'tnut':
            return self.name + '_tnut'
        if k == 'nut':
            return self.name + '_nut'
        return self.target[1]

    def tip(self):
        return self.s0 + self.d * self.len_shank

# =============================================================================
# FASTENER LIST
# =============================================================================
def wrist_fasteners():
    import wrist_module as W
    L = []
    zf = W.Z_BLOCK_FACE
    for i, (x, y) in enumerate(W.BLOCK_HOLES):
        if i == 3:
            continue                                 # (+10, +10): no access past the servo plate; the block is held by 3 screws
        L.append(F('wm_f_block%d' % i, 'cap', 3, 6, (x, y, W.Z_CP0 + W.BLOCK_SINK), (0, 0, 1), 'xcar', ('blind', 'wm_mgn12h_block', 3.0, 3.5),
                   note='carriage plate to X rail block, heads sunk 3.5'))
    for i, (x, y) in enumerate(W.RISER_MOUNT):
        L.append(F('wm_f_riser%d' % i, 'cap', 3, 10, (x, y, W.Z_CP0), (0, 0, 1), 'xcar', ('insert', None, 4.0, None),
                   insert=('wm_x_belt_riser', W.CP_T), note='belt riser, from below'))
    for i, (x, y) in enumerate(W.CHAIN_MOUNT):
        L.append(F('wm_f_post%d' % i, 'cap', 3, 10, (x, y, W.Z_CP0), (0, 0, 1), 'xcar', ('insert', None, 4.0, None),
                   insert=('wm_chain_post', W.CP_T), note='chain post, from below'))
    ztop = W.X_BELT_Z + W.BELT_T / 2 - 0.3 + 3.5
    zris = W.X_BELT_Z - W.BELT_T / 2
    for i, (x, y) in enumerate(W.CLAMP_SCREWS):
        L.append(F('wm_f_clamp%d' % i, 'cap', 3, 10, (x, y, ztop), (0, 0, -1), 'xcar', ('insert', None, 4.0, None),
                   insert=('wm_x_belt_riser', ztop - zris), note='belt clamp into the riser'))
    for i, (x, z) in enumerate(W.SERVO_TAB_HOLES):
        y0 = W.SP_Y0 - W.SERVO_TAB_THK
        L.append(F('wm_f_servo%d' % i, 'pan', 2, 8, (x, y0, z), (0, 1, 0), 'xcar', ('self', 'wm_wrist_carriage', 3.5, None), extra=('wm_servo_tabs', 'wm_servo_case'),
                   head_washer=True, note='servo tabs: M2 self-tapping into the servo plate, large washer under the head (4.5 tab hole)'))
    L.append(F('wm_f_pivotA', 'cap', 4, 30, (0, W.SP_Y0, W.Z_PIVOT_BOT), (0, 1, 0), 'xcar', ('nut', None, 5.0, None),
               extra=('wm_spacer_AL', 'wm_brg_AL', 'wm_shim_AL'), nut=('nyloc', W.EP_Y0 - W.SP_Y0),
               note='lower A pivot: boss, spacer, bearing, shim, nyloc'))
    for i, z in enumerate((W.Z_PIVOT_TOP, W.Z_PIVOT_BOT)):
        y0 = W.ARM_Y1 - W.BRG_W - W.SPACER_L
        L.append(F('wm_f_pivotB%d' % i, 'cap', 4, 20, (W.R_ARM, y0, z), (0, 1, 0), 'end', ('nut', None, 5.0, None), head_washer=True,
                   extra=('wm_spacer_B', 'wm_brg_B', 'wm_shim_B'), nut=('nyloc', W.EP_Y1 - y0),
                   note='B pivots: washer, spacer, bearing, shim, end plate, nyloc'))
    L.append(F('wm_f_horn0', 'button', 3, 10, (W.HORN_SCREW_R, W.ARM_Y1, W.Z_PIVOT_TOP), (0, -1, 0), 'armT',
               ('through', 'wm_servo_horn', 1.8, None), note='top arm to the horn arm (M3 tapped hole at r 24, VERIFY)'))
    L.append(F('wm_f_spline', 'button', 3, 6, (0, W.HORN_FACE_Y, W.Z_PIVOT_TOP), (0, -1, 0), 'armT', ('blind', 'wm_servo_spline', 3.0, 5.0),
               extra=('wm_servo_horn',), note='horn centre screw into the servo spline'))
    for i, (x, y) in enumerate(W.FOOT_SCREWS):
        L.append(F('wm_f_shelf%d' % i, 'cap', 3, 10, (x, y, W.Z_SH0), (0, 0, 1), 'end', ('insert', None, 4.0, None),
                   insert=('wm_end_plate', W.SH_T), note='shelf to end plate foot, from below'))
    for i, (x, y) in enumerate(W.MOTOR_HOLES):
        L.append(F('wm_f_n17p_%d' % i, 'button', 3, 8, (x, y, W.Z_SH0), (0, 0, 1), 'end', ('blind', 'wm_nema17p', 3.0, 4.5),
                   note='wrist stepper (NEMA17 pancake) from below (motor thread depth VERIFY, about 4.5)'))
    zt = W.Z_SH0 - W.TOF_POST_H - W.TOF_PCB_T
    for i, (x, y) in enumerate(W.TOF_HOLES):
        L.append(F('wm_f_tof%d' % i, 'pan', 2, 6, (x, y, zt), (0, 0, 1), 'end', ('self', 'wm_shelf', 3.5, None), extra=('wm_tof_board',),
                   note='distance sensor (TOF400C), M2 self-tapping from below into the shelf posts'))
    zb = W.Z_SH0 - W.CAM_POST_H - 1.6
    for i, (x, y) in enumerate(W.CAM_POSTS):
        L.append(F('wm_f_cam%d' % i, 'pan', 2, 6, (x, y, zb), (0, 0, 1), 'end', ('self', 'wm_shelf', 3.5, None), extra=('wm_camera_board',),
                   note='camera board, M2 self-tapping from below into the shelf posts'))
    zh = W.H_MID + W.MAG_H                          # hub bottom = magnet top
    L.append(F('wm_f_magnet', 'set', 3, 8, (W.MAG_X, W.MAG_Y, zh + 4.5), (0, 0, -1), 'wrist', ('blind', 'wm_electromagnet', 3.0, 4.0),
               insert=('wm_wrist_hub', 4.5 - INSERT_L),
               note='magnet stud: set screw in an insert in the hub bottom, magnet spun on with Loctite 243 (magnet thread depth VERIFY)'))
    for i, x in enumerate((10.0, 20.0)):
        L.append(F('wm_f_xchain%d' % i, 'cap', 3, 12, (x, 0.0, W.CHAIN_TOP + 4.5), (0, 0, -1), 'xcar', ('nut', None, 2.4, None),
                   extra=('cable_chain_x',), nut=('hex', 4.5 + W.CHAIN_PLATE_T), note='X chain moving end link on the chain post'))
    return L

def frame_fasteners():
    import frame as Fr
    L = []
    P0 = Fr.PYC0
    # ---------------- Y carriage group (at PYC0)
    for i, (a, b) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        L.append(F('f_yblock%d' % i, 'cap', 3, 8, (Fr.YB_X + 10 * a, P0 + 10 * b, Fr.Z_YC1 - 5.0), (0, 0, -1), 'ycar',
                   ('blind', 'y_block_mgn12h', 2.5, 3.5), note='Y carriage to the Y block, heads sunk 5'))
    pc, zs = Fr.POST_C, Fr.Z_YC1 + Fr.SOCKET_H / 2
    ox, oy = 10.2 + Fr.SOCKET_WALL_X, 10.2 + Fr.SOCKET_WALL_Y
    for nm, p, d, o, L5 in (('px', (pc[0] + ox, pc[1], zs), (-1, 0, 0), ox, 10), ('mx', (pc[0] - ox, pc[1], zs), (1, 0, 0), ox, 10),
                            ('py', (pc[0], pc[1] + oy, zs), (0, -1, 0), oy, 12), ('my', (pc[0], pc[1] - oy, zs), (0, 1, 0), oy, 12)):
        L.append(F('f_socket_' + nm, 'cap', 5, L5, p, d, 'ycar', ('tnut', None, 3.0, None), tnut=(o - 10.0, (0, 0, 1), 'post_2020'),
                   note='post in its socket, T-nut in the post slot'))
    zc0 = Fr.ZT - 0.7 + 0.3 - 3.5
    for i, (x, y) in enumerate(Fr.Y_CLAMP):
        L.append(F('f_yclamp%d' % i, 'cap', 3, 14, (x, y, zc0), (0, 0, 1), 'ycar', ('insert', None, 4.0, None),
                   insert=('y_carriage', Fr.Z_YC0 - zc0), note='Y belt clamp + spacer into the carriage'))
    (ax, ay), (bx, by) = Fr.Y_CHAIN_SLOT
    for i, y in enumerate((ay + 1.0, by - 1.0)):
        L.append(F('f_ychain%d' % i, 'button', 3, 20, (ax, y, Fr.Z_YC1 + 4.5), (0, 0, -1), 'ycar', ('nut', None, 2.4, None),
                   extra=('cable_chain_y',), nut=('hex', 4.5 + (Fr.Z_YC1 - Fr.Z_YC0)), note='Y chain moving end link, nut under the carriage'))
    fy = P0 + Fr.XM_FACE_DY
    for i, (a, b) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        L.append(F('f_xmotor%d' % i, 'cap', 3, 10, (Fr.XM_C[0] + 15.5 * a, fy - Fr.XM_T, Fr.XM_C[1] + 15.5 * b), (0, 1, 0), 'ycar',
                   ('blind', 'x_motor_17HS16', 3.0, 4.5), note='X motor (thread depth 4.5)'))
    for i, (x, zc) in enumerate(Fr.XM_POST_BOLTS):
        L.append(F('f_xmount%d' % i, 'cap', 5, 16, (x, P0 + 21.0, zc), (0, -1, 0), 'ycar', ('tnut', None, 3.0, None),
                   tnut=(11.0, (0, 0, 1), 'post_2020'), note='X motor mount to the post (+y slot), heads in the counterbore'))
    for i, (y, zc) in enumerate(Fr.XM_SIDE_BOLTS):
        L.append(F('f_xmount_side%d' % i, 'cap', 5, 12, (Fr.XM_CHEEK_X0, y, zc), (1, 0, 0), 'ycar', ('tnut', None, 3.0, None),
                   tnut=(Fr.POST_C[0] - 10.0 - Fr.XM_CHEEK_X0, (0, 0, 1), 'post_2020'), note='X motor mount cheek to the post (-x slot)'))
    for i, s in enumerate((-1, 1)):
        L.append(F('f_xswitch%d' % i, 'pan', 2, 10, (209.0 + Fr.D2F['W'], P0 + 19.0 + s * Fr.D2F['hole_pitch'] / 2, 129.5), (-1, 0, 0), 'ycar',
                   ('self', 'x_motor_mount', 3.5, None), extra=('x_home_switch',), note='X home switch, M2 self-tapping'))
    xb = Fr.BOOM_X0 + Fr.BRACKET_HOLE
    for nm, p, d, surf, axis, prof in (('top_h', (xb, P0, Fr.Z_BOOM1 + 3), (0, 0, -1), 3.0, (1, 0, 0), 'boom_2020'),
                                       ('top_v', (Fr.BOOM_X0 + 3, P0, Fr.Z_BOOM1 + Fr.BRACKET_HOLE), (-1, 0, 0), 3.0, (0, 0, 1), 'post_2020'),
                                       ('bot_h', (xb, P0, Fr.Z_BOOM0 - 3), (0, 0, 1), 3.0, (1, 0, 0), 'boom_2020'),
                                       ('bot_v', (Fr.BOOM_X0 + 3, P0, Fr.Z_BOOM0 - Fr.BRACKET_HOLE), (-1, 0, 0), 3.0, (0, 0, 1), 'post_2020')):
        L.append(F('f_bracket_' + nm, 'button', 5, 8, p, d, 'ycar', ('tnut', None, 3.0, None), extra=('corner_bracket',),
                   tnut=(surf, axis, prof), note='corner bracket'))
    for i, t in enumerate(Fr.rail_holes(Fr.XR_X1 - Fr.XR_X0)):
        L.append(F('f_xrail%02d' % i, 'cap', 3, 8, (Fr.XR_X0 + t, P0, Fr.Z_BOOM0 - Fr.RAIL_H + Fr.RAIL_CB_H), (0, 0, 1), 'ycar',
                   ('tnut', None, 2.5, None), extra=('x_rail',), tnut=(Fr.RAIL_H - Fr.RAIL_CB_H, (1, 0, 0), 'boom_2020'),
                   note='X rail to the boom (bottom slot)'))
    L.append(F('f_xidler_end', 'cap', 5, 12, (Fr.BOOM_X1 + 3.0, P0, Fr.X_BELT_Z), (-1, 0, 0), 'ycar', ('tapped', 'boom_2020', 6.0, None),
               note='X idler bracket into the tapped boom end (tap M5)'))
    L.append(F('f_xidler_axle', 'button', 5, 30, (Fr.XI_C[0], P0 + Fr.XB_DY0 - 0.5, Fr.X_BELT_Z), (0, 1, 0), 'ycar', ('nut', None, 4.7, None),
               extra=('x_idler_gt2', 'x_idler_bracket', 'x_idler_slider'), nut=('nyloc', Fr.XI_SLIDER[3] - Fr.XB_DY0 + 0.5),
               note='X idler axle: head between boom and idler (fit it before the bracket goes on the boom), nyloc outside the slider, snug'))
    xh = Fr.XI_SLIDER[0] - 25.0                          # M3x25: the tip touches the slider's -x end as assembled
    L.append(F('f_xidler_push', 'cap', 3, 25, (xh, P0 + Fr.XI_PUSH[0], Fr.XI_PUSH[1]), (1, 0, 0), 'ycar', ('insert', None, 4.0, None),
               extra=('x_idler_slider',), insert=('x_idler_bracket', Fr.XI_LUG_X[0] - xh), nut=('hex', Fr.XI_LUG_X[0] - xh - 2.4),
               note='X belt tension: pushes the idler slider toward +x; hex nut locks it on the lug'))
    for i, x in enumerate((235.0, 245.0)):
        L.append(F('f_xchain_fix%d' % i, 'button', 3, 10, (x, P0, Fr.Z_BOOM1 + 4.5), (0, 0, -1), 'ycar', ('tnut', None, 2.5, None),
                   extra=('cable_chain_x',), tnut=(4.5, (1, 0, 0), 'boom_2020'), note='X chain fixed end link on the boom top'))
    # ---------------- base
    py, pz = Fr.YI_C
    sx0 = Fr.YI_SLIDER[0]
    L.append(F('f_yidler_axle', 'cap', 5, 25, (sx0, py, pz), (1, 0, 0), 'base', ('nut', None, 3.7, None),
               extra=('y_idler_gt2', 'y_idler_bracket', 'y_idler_slider'), nut=('hex', Fr.Y_BELT_X0 + 6.5 - sx0),
               note='Y idler axle through the slider and the slotted plate (cantilever), nut snug'))
    ly = Fr.YI_LUG_Y[1]
    L.append(F('f_yidler_push', 'cap', 3, 16, (Fr.YI_PUSH_X, ly + 4.0, pz), (0, -1, 0), 'base', ('insert', None, 4.0, None),
               extra=('y_idler_slider',), insert=('y_idler_bracket', 4.0), nut=('hex', 4.0 - 2.4),
               note='Y belt tension: pushes the idler slider toward -y; hex nut locks it on the lug'))
    L.append(F('f_ybeam_end', 'button', 5, 12, (Fr.YB_X, 4.0, Fr.Z_YB1 - 10.0), (0, 1, 0), 'base', ('tapped', 'y_beam_2020', 5.0, None),
               note='Y idler bracket into the tapped beam end (tap M5)'))
    def through(name, std, dia, L_, x, y, seat, note):
        # bolt from the top through a printed part and the plywood; washer + hex nut under the plywood
        return F(name, std, dia, L_, (x, y, seat), (0, 0, -1), 'base', ('nut', None, NUT['hex'][dia][1], None),
                 nut=('hex', seat - Fr.Z_PLY0), nut_washer=True, note=note)
    for i, (x, y) in enumerate(Fr.IDLER_BOLTS):
        L.append(through('f_yidler_bolt%d' % i, 'button', 4, 16, x, y, Fr.Z_PLY1 + 4.0, 'Y idler bracket through the plywood'))
    for i, s in enumerate((-1, 1)):
        zz = 40.0 + Fr.Y_RISER + s * Fr.D2F['hole_pitch'] / 2 + 0.5
        L.append(F('f_yswitch%d' % i, 'pan', 2, 10, (236.0 + Fr.D2F['W'], 4.5, zz), (-1, 0, 0), 'base', ('self', 'y_idler_bracket', 3.5, None),
                   extra=('y_home_switch',), note='Y home switch, M2 self-tapping'))
    for i, (a, b) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        L.append(F('f_ymotor%d' % i, 'cap', 3, 10, (Fr.YM_FACE + Fr.YM_T, Fr.YM_C[0] + 15.5 * a, Fr.YM_C[1] + 15.5 * b), (-1, 0, 0), 'base',
                   ('blind', 'y_motor_17HS16', 3.0, 4.5), note='Y motor'))
    for i, (x, yy) in enumerate(Fr.YM_BOLTS):
        L.append(through('f_ymotor_bolt%d' % i, 'button', 4, 16, x, yy, Fr.Z_PLY1 + Fr.YM_BASE[2],
                         'Y motor mount through the plywood (bolt it down before the motor goes on)'))
    for i, y in enumerate(Fr.BEAM_BOLTS_Y):
        z0 = Fr.Z_PLY0 + Fr.BEAM_CBORE
        L.append(F('f_beam%d' % i, 'cap', 5, 20, (Fr.YB_X, y, z0), (0, 0, 1), 'base', ('tnut', None, 3.0, None),
                   tnut=(Fr.Z_YB0 - z0, (0, 1, 0), 'y_beam_2020'), note='Y beam through plywood and riser, from below'))
    for i, t in enumerate(Fr.rail_holes(Fr.YB_Y1 - Fr.YB_Y0)):
        L.append(F('f_yrail%02d' % i, 'cap', 3, 8, (Fr.YB_X, Fr.YB_Y0 + t, Fr.Z_YR1 - Fr.RAIL_CB_H), (0, 0, -1), 'base',
                   ('tnut', None, 2.5, None), extra=('y_rail',), tnut=(Fr.RAIL_H - Fr.RAIL_CB_H, (0, 1, 0), 'y_beam_2020'),
                   note='Y rail to the beam (top slot)'))
    for i, (x, y) in enumerate(Fr.FEET):
        L.append(F('f_foot%d' % i, 'csk', 3, 10, (x, y, Fr.Z_PLY1), (0, 0, -1), 'base', ('insert', None, 4.0, None),
                   insert=('foot_%d' % (i + 1), Fr.Z_PLY1 - Fr.FOOT_H), note='printed foot: countersunk from the plywood top into its insert'))
    EB = Fr.EB
    for i, (x, y) in enumerate(() if not Fr.ELECTRONICS_ON_BASE else ((EB[0] + 4, EB[1] + 4), (EB[2] - 4, EB[1] + 4), (EB[0] + 4, EB[3] - 4), (EB[2] - 4, EB[3] - 4))):
        L.append(F('f_eb_bot%d' % i, 'csk', 3, 10, (x, y, Fr.Z_PLY0), (0, 0, 1), 'base', ('blind', 'standoff_m3x10_%d' % (i + 1), 3.5, 5.0),
                   extra=('plywood_base',), note='standoff from below (countersunk, flush)'))
        L.append(F('f_eb_top%d' % i, 'button', 3, 6, (x, y, Fr.Z_PLY1 + 10.0 + 1.6), (0, 0, -1), 'base',
                   ('blind', 'standoff_m3x10_%d' % (i + 1), 3.5, 5.0), extra=('perfboard',), note='board on the standoff'))
    x0, y0, x1, y1, zt = Fr.PANEL
    for i, (x, y) in enumerate(Fr.panel_bolts() if Fr.ELECTRONICS_ON_BASE else ()):
        L.append(through('f_panel%d' % i, 'button', 3, 50, x, y, zt, 'control panel through its bosses and the plywood'))
    for i, y in enumerate((47.0, 96.0) if Fr.ELECTRONICS_ON_BASE else ()):
        L.append(F('f_pcb%d' % i, 'pan', 2, 6, (x0 + 9.6, y, 24.5), (-1, 0, 0), 'base', ('self', 'control_panel', 3.0, None),
                   extra=('connector_pcb',), note='connector board, M2 self-tapping'))
    bx, by, t = Fr.BB[0], Fr.BB[1], 3.0
    for i, (x, y) in enumerate(Fr.BB_EARS if Fr.ELECTRONICS_ON_BASE else ()):
        L.append(through('f_bbtray%d' % i, 'button', 3, 12, x, y, Fr.Z_PLY1 + 3.0, 'breadboard tray'))
    for i, (x, y) in enumerate(Fr.bt_ears() if Fr.ELECTRONICS_ON_BASE else ()):
        L.append(through('f_battray%d' % i, 'button', 3, 12, x, y, Fr.Z_PLY1 + 3.0, 'battery tray'))
    import chains as C
    for i, y in enumerate(C.GUIDE_BOLTS_Y):
        L.append(through('f_guide%d' % i, 'button', 3, 25, C.YC_LANE_X, y, Fr.Z_PLY1 + C.GUIDE_FLOOR - 2.5, 'Y chain guide (heads sunk under the chain)'))
    return L

_CACHE = {}

def all_fasteners():
    if 'L' not in _CACHE:
        _CACHE['L'] = wrist_fasteners() + frame_fasteners()
        _CACHE['pieces'] = {f.name: f.pieces() for f in _CACHE['L']}
    return _CACHE['L'], _CACHE['pieces']

def placed(PYC, PXB, h, wd):
    """{piece name: (shape, group label, 'fastener', colour)} and {piece name: allowed prefixes} for one pose."""
    import wrist_module as W
    import frame as Fr
    L, P = all_fasteners()
    out, allow = {}, {}
    for f in L:
        for suf, (s, al) in P[f.name].items():
            s2 = s.copy()
            if f.name.startswith('wm_'):
                s2 = W.pose(s2, f.group, h, wd)
                s2.translate(V(PXB, PYC, 0))
                g = 'wm_' + f.group
            elif f.group == 'ycar':
                s2.translate(V(0, PYC - Fr.PYC0, 0))
                g = 'ycar'
            else:
                g = 'base'
            col = 'insert' if suf == 'insert' else ('fastener2' if suf in ('nut', 'tnut', 'washer', 'nutwasher') else 'fastener')
            nm = f.name + '_' + suf
            out[nm] = (s2, g, 'fastener', col)
            allow[nm] = al
    return out, allow

def bom():
    """Rows (item, qty, used for) for the fastener BOM."""
    from collections import OrderedDict
    L, _ = all_fasteners()
    rows = OrderedDict()
    def add(item, use):
        q, u = rows.get(item, (0, []))
        if use not in u:
            u = u + [use]
        rows[item] = (q + 1, u)
    for f in L:
        add(f.label(), f.note)
        if f.head_washer or f.nut_washer:
            add('M%g washer ISO 7089 (%g x %g)' % ((f.dia,) + WASHER[f.dia]), f.note)
        if f.nut:
            k = f.nut[0]
            add('M%g %s nut' % (f.dia, {'hex': 'hex ISO 4032', 'nyloc': 'nyloc ISO 10511'}[k]), f.note)
        if f.insert:
            add('Ruthex M3 x 5.7 heat-set insert', f.note)
        if f.tnut:
            add('M%g drop-in T-nut for 2020 V-slot (6 mm slot)' % f.dia, f.note)
    return [(k, q, '; '.join(u)) for k, (q, u) in rows.items()]
