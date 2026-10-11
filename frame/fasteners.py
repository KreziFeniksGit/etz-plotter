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
        'pan': {2: (3.8, 1.6), 3.5: (7.0, 2.4), 4: (8.0, 2.8)}}
NUT = {'hex': {2: (4.0, 1.6), 2.5: (5.0, 2.0), 3: (5.5, 2.4), 4: (7.0, 3.2), 5: (8.0, 4.0)},
       'nyloc': {2: (4.0, 3.0), 3: (5.5, 4.0), 4: (7.0, 5.0), 5: (8.0, 5.0)}}
WASHER = {2: (6.0, 0.8), 3: (7.0, 0.5), 4: (9.0, 0.8), 5: (10.0, 1.0)}   # M2: DIN 9021 large washer (covers the 4.5 servo tab hole)
INSERT_L, INSERT_D = 5.7, 4.0                  # Ruthex RX-M3x5.7 (drawn solid: its thread is what the screw engages)
TNUT_W, TNUT_L, TNUT_T, TNUT_DEPTH = 5.8, 9.5, 3.5, 1.8   # 2020 drop-in T-nut, under the 1.8 mm slot lips

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
        n = {'cap': 'ISO 4762', 'button': 'ISO 7380', 'csk': 'ISO 10642', 'pan': 'pan head'}[self.std]
        if self.std == 'pan' and self.dia in (3.5, 4):
            return 'wood screw %gx%g (pan head)' % (self.dia, self.L)
        return 'M%g x %g %s' % (self.dia, self.L, n)

    def pieces(self):
        """{suffix: (shape, allowed prefixes)}"""
        p, d, r = self.p, self.d, self.dia / 2
        own = self.name + '_'
        out = {}
        D, H = HEAD[self.std][self.dia]
        if self.std == 'csk':
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
        L.append(F('wm_f_servo%d' % i, 'cap', 2, 12, (x, y0, z), (0, 1, 0), 'xcar', ('nut', None, 3.0, None), extra=('wm_servo_tabs', 'wm_servo_case'),
                   nut=('nyloc', W.SP_Y1 - y0), head_washer=True, note='servo tabs: M2x12, large washer under the head (4.5 tab hole), nyloc on the +y side (no washer: a longer screw would reach the horn)'))
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
    for i in range(4):
        a, b = (-1, 1)[i % 2], (-1, 1)[i // 2]
        L.append(F('wm_f_n11_%d' % i, 'button', 2.5, 6, (W.MAG_X + a * W.N11_HOLE_PITCH / 2, W.MAG_Y + b * W.N11_HOLE_PITCH / 2, W.Z_SH0), (0, 0, 1),
                   'end', ('blind', 'wm_nema11', 1.8, 2.5), note='NEMA11 from below (motor thread depth VERIFY, about 2.5)'))
    zb = W.Z_SH0 - 4.0 - 1.6
    for i, (x, y) in enumerate(W.CAM_POSTS):
        L.append(F('wm_f_cam%d' % i, 'pan', 2, 12, (x, y, W.Z_SH1), (0, 0, -1), 'end', ('nut', None, 1.6, None), extra=('wm_camera_board',),
                   nut=('hex', W.Z_SH1 - zb), note='camera board, nut under the board'))
    L.append(F('wm_f_magnet', 'button', 3, 6, (W.MAG_X, W.MAG_Y, W.H_MID + W.MAG_H + 2.5), (0, 0, -1), 'wrist', ('blind', 'wm_electromagnet', 3.0, 4.0),
               note='magnet on the hub (magnet thread depth VERIFY)'))
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
    o = 10.2 + 5.0
    for nm, p, d in (('px', (pc[0] + o, pc[1], zs), (-1, 0, 0)), ('mx', (pc[0] - o, pc[1], zs), (1, 0, 0)),
                     ('py', (pc[0], pc[1] + o, zs), (0, -1, 0)), ('my', (pc[0], pc[1] - o, zs), (0, 1, 0))):
        L.append(F('f_socket_' + nm, 'cap', 5, 10, p, d, 'ycar', ('tnut', None, 3.0, None), tnut=(o - 10.0, (0, 0, 1), 'post_2020'),
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
        L.append(F('f_xmotor%d' % i, 'cap', 3, 8, (Fr.XM_C[0] + 15.5 * a, fy - 4.0, Fr.XM_C[1] + 15.5 * b), (0, 1, 0), 'ycar',
                   ('blind', 'x_motor_17HS16', 3.0, 4.5), note='X motor (thread depth 4.5)'))
    for i, zc in enumerate((186.0, 136.5)):
        L.append(F('f_xmount%d' % i, 'cap', 5, 16, (199.0, P0 + 21.0, zc), (0, -1, 0), 'ycar', ('tnut', None, 3.0, None),
                   tnut=(11.0, (0, 0, 1), 'post_2020'), note='X motor mount to the post (+y slot), heads in the counterbore'))
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
    L.append(F('f_xidler_axle', 'button', 5, 18, (Fr.XI_C[0], P0 + Fr.XB_DY0 - 0.5, Fr.X_BELT_Z), (0, 1, 0), 'ycar', ('nut', None, 4.0, None),
               extra=('x_idler_gt2', 'x_idler_bracket'), nut=('hex', Fr.XB_DY1 + 5.0 - Fr.XB_DY0 + 0.5),
               note='X idler axle: head between boom and idler, nut outside the slotted plate'))
    for i, x in enumerate((235.0, 245.0)):
        L.append(F('f_xchain_fix%d' % i, 'button', 3, 10, (x, P0, Fr.Z_BOOM1 + 4.5), (0, 0, -1), 'ycar', ('tnut', None, 2.5, None),
                   extra=('cable_chain_x',), tnut=(4.5, (1, 0, 0), 'boom_2020'), note='X chain fixed end link on the boom top'))
    # ---------------- base
    py, pz = Fr.YI_C
    L.append(F('f_yidler_axle', 'cap', 5, 18, (176.0, py, pz), (1, 0, 0), 'base', ('nut', None, 4.0, None), extra=('y_idler_gt2',),
               nut=('hex', Fr.Y_BELT_X0 + 6.5 - 176.0), note='Y idler axle (cantilever)'))
    L.append(F('f_ybeam_end', 'button', 5, 12, (Fr.YB_X, 4.0, Fr.Z_YB1 - 10.0), (0, 1, 0), 'base', ('tapped', 'y_beam_2020', 5.0, None),
               note='Y idler bracket into the tapped beam end (tap M5)'))
    for i, (x, y) in enumerate(Fr.IDLER_WOOD):
        L.append(F('f_yidler_wood%d' % i, 'pan', 4, 12, (x, y, Fr.Z_PLY1 + 4.0), (0, 0, -1), 'base', ('wood', 'plywood_base', 6.0, None),
                   note='Y idler bracket to the plywood'))
    for i, s in enumerate((-1, 1)):
        zz = 40.0 + Fr.Y_RISER + s * Fr.D2F['hole_pitch'] / 2 + 0.5
        L.append(F('f_yswitch%d' % i, 'pan', 2, 10, (236.0 + Fr.D2F['W'], 4.5, zz), (-1, 0, 0), 'base', ('self', 'y_idler_bracket', 3.5, None),
                   extra=('y_home_switch',), note='Y home switch, M2 self-tapping'))
    for i, (a, b) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        L.append(F('f_ymotor%d' % i, 'cap', 3, 8, (Fr.YM_FACE + 4.0, Fr.YM_C[0] + 15.5 * a, Fr.YM_C[1] + 15.5 * b), (-1, 0, 0), 'base',
                   ('blind', 'y_motor_17HS16', 3.0, 4.5), note='Y motor'))
    for i, yy in enumerate((Fr.YM_C[0] - 16.0, Fr.YM_C[0] + 16.0)):
        L.append(F('f_ymotor_wood%d' % i, 'pan', 4, 12, (187.0, yy, Fr.Z_PLY1 + 4.0), (0, 0, -1), 'base', ('wood', 'plywood_base', 6.0, None),
                   note='Y motor mount to the plywood (tension slots)'))
    for i, y in enumerate(Fr.BEAM_BOLTS_Y):
        z0 = Fr.Z_PLY0 + Fr.BEAM_CBORE
        L.append(F('f_beam%d' % i, 'cap', 5, 20, (Fr.YB_X, y, z0), (0, 0, 1), 'base', ('tnut', None, 3.0, None),
                   tnut=(Fr.Z_YB0 - z0, (0, 1, 0), 'y_beam_2020'), note='Y beam through plywood and riser, from below'))
    for i, t in enumerate(Fr.rail_holes(Fr.YB_Y1 - Fr.YB_Y0)):
        L.append(F('f_yrail%02d' % i, 'cap', 3, 8, (Fr.YB_X, Fr.YB_Y0 + t, Fr.Z_YR1 - Fr.RAIL_CB_H), (0, 0, -1), 'base',
                   ('tnut', None, 2.5, None), extra=('y_rail',), tnut=(Fr.RAIL_H - Fr.RAIL_CB_H, (0, 1, 0), 'y_beam_2020'),
                   note='Y rail to the beam (top slot)'))
    for i, (x, y) in enumerate(Fr.FEET):
        L.append(F('f_foot%d' % i, 'pan', 3.5, 12, (x, y, Fr.FOOT_SCREW_SINK), (0, 0, 1), 'base', ('wood', 'plywood_base', 6.0, None),
                   extra=('rubber_foot',), note='rubber foot, from below'))
    EB = Fr.EB
    for i, (x, y) in enumerate(((EB[0] + 4, EB[1] + 4), (EB[2] - 4, EB[1] + 4), (EB[0] + 4, EB[3] - 4), (EB[2] - 4, EB[3] - 4))):
        L.append(F('f_eb_bot%d' % i, 'csk', 3, 16, (x, y, Fr.Z_PLY0), (0, 0, 1), 'base', ('blind', 'standoff_m3x10_%d' % (i + 1), 3.5, 5.0),
                   extra=('plywood_base',), note='standoff from below (countersunk, flush)'))
        L.append(F('f_eb_top%d' % i, 'button', 3, 6, (x, y, Fr.Z_PLY1 + 10.0 + 1.6), (0, 0, -1), 'base',
                   ('blind', 'standoff_m3x10_%d' % (i + 1), 3.5, 5.0), extra=('perfboard',), note='board on the standoff'))
    x0, y0, x1, y1, zt = Fr.PANEL
    for i, (x, y) in enumerate(((x0 + 6, y0 + 6), (x1 - 6, y0 + 6), (x0 + 6, y1 - 6), (x1 - 6, y1 - 6))):
        L.append(F('f_panel%d' % i, 'pan', 3.5, 50, (x, y, zt), (0, 0, -1), 'base', ('wood', 'plywood_base', 8.0, None),
                   note='control panel through its bosses into the plywood'))
    for i, y in enumerate((47.0, 96.0)):
        L.append(F('f_pcb%d' % i, 'pan', 2, 6, (x0 + 9.6, y, 24.5), (-1, 0, 0), 'base', ('self', 'control_panel', 3.0, None),
                   extra=('connector_pcb',), note='connector board, M2 self-tapping'))
    bx, by, t = Fr.BB[0], Fr.BB[1], 3.0
    for i, (x, y) in enumerate(Fr.BB_EARS):
        L.append(F('f_bbtray%d' % i, 'pan', 3.5, 12, (x, y, Fr.Z_PLY1 + 3.0), (0, 0, -1), 'base', ('wood', 'plywood_base', 6.0, None),
                   note='breadboard tray'))
    for i, (x, y) in enumerate(Fr.bt_ears()):
        L.append(F('f_battray%d' % i, 'pan', 3.5, 12, (x, y, Fr.Z_PLY1 + 3.0), (0, 0, -1), 'base', ('wood', 'plywood_base', 6.0, None),
                   note='battery tray'))
    import chains as C
    for i, y in enumerate((250.0, 300.0, 350.0, 405.0)):
        L.append(F('f_guide%d' % i, 'pan', 3.5, 25, (C.YC_LANE_X, y, Fr.Z_PLY1 + C.GUIDE_FLOOR - 3.0), (0, 0, -1), 'base',
                   ('wood', 'plywood_base', 8.0, None), note='Y chain guide (heads sunk under the chain)'))
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
            add('M%g drop-in T-nut for 2020 (6 mm slot)' % f.dia, f.note)
    return [(k, q, '; '.join(u)) for k, (q, u) in rows.items()]
