"""ETZ plotter v2: masses, tipping, rail moment loads and boom/post deflection.
Run with FreeCAD's python:  ./fcpy tools/stability.py   -> out/stability.json
Masses: bought parts from datasheets (grams below), printed parts from the CAD volume
x PETG 1.27 g/cm3 x 0.65 (4 walls, 40 % gyroid), plywood 0.68 g/cm3, chains 0.6 x nylon 1.14."""
import json, math, os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [HERE, os.path.join(HERE, 'wrist'), os.path.join(HERE, 'frame')]
import assembly as A, frame as F

G = 9.81
ACC = 2.0                      # m/s^2 design acceleration (100 mm/s reached in 50 ms)
MASS_G = {                     # bought parts, grams (datasheet or typical)
    'y_beam_2020': 200, 'post_2020_130': 65, 'boom_2020_270': 135,          # 2020: 0.5 kg/m
    'y_rail_mgn12_400': 260, 'x_rail_mgn12_250': 163,                         # 0.65 kg/m
    'y_block_mgn12h': 47, 'wm_mgn12h_block': 47,
    'y_motor_17HS16': 280, 'x_motor_17HS16': 280, 'wm_nema17p': 140, 'wm_nema17p_pilot': 0, 'wm_nema17p_shaft': 0,
    'wm_servo_case': 55, 'wm_servo_tabs': 0, 'wm_servo_spline': 0, 'wm_servo_horn': 8, 'wm_tof_board': 2,
    'wm_electromagnet': 35, 'wm_camera_board': 8, 'wm_camera_lens': 4,
    'battery_4s_2200': 230, 'estop_22mm_latching': 60, 'start_button_16mm': 10, 'breadboard_400': 45,
    'perfboard_100x80': 30, 'esp32_s3_devkitc1': 10, 'pololu_5v_d36v28f5': 3, 'pololu_6v_d36v28f6': 3,
    'corner_bracket_top': 20, 'corner_bracket_bottom': 20, 'x_pulley_gt2_20t': 10, 'y_pulley_gt2_20t': 10,
    'x_idler_gt2_20t': 10, 'y_idler_gt2_20t': 10, 'x_belt_gt2': 4, 'y_belt_gt2': 5,
}
PREFIX_G = {'tmc2209': 5, 'standoff': 1, 'led_': 1, 'header_': 1, 'battery_strap': 3,
            'wm_brg': 3, 'wm_spacer': 0.2, 'wm_shim': 0.1, 'connector_pcb': 3, 'x_home': 2, 'y_home': 2}
EXTRA = [  # (group, grams, x, y, z) screws, nuts, wires not in the CAD; y relative to PYC for moving groups
    # the wrist-internal wires are modelled now (cable_wrist_*); screws are modelled
]

def grams(name, shape, kind, col):
    if name in MASS_G:
        return MASS_G[name]
    for p, g in PREFIX_G.items():
        if name.startswith(p):
            return g
    v = shape.Volume / 1000.0
    if name == 'plywood_base':
        return v * 0.68
    if name.startswith('cable_chain'):
        return v * 1.14 * 0.6
    if kind == 'printed':
        return v * 1.27 * 0.65
    if kind == 'fastener':
        return v * (8.4 if col == 'insert' else 7.85)   # brass inserts, steel screws
    if kind == 'cable':
        return v * 1.5                  # copper + insulation, loosely bundled
    return v * 1.2                      # small plastic bits

def com(shape):
    sol = shape.Solids
    tv = sum(s.Volume for s in sol)
    return [sum(getattr(s.CenterOfMass, a) * s.Volume for s in sol) / tv for a in 'xyz']

def masses(PYC, PXB, h, wd):
    w = A.world(PYC, PXB, h, wd, field=False, fasteners=True)
    out = []
    for k, (s, g, kind, col) in w.items():
        out.append((k, g, grams(k, s, kind, col) / 1000.0, com(s)))
    for g, gr, x, y, z in EXTRA:
        if g == 'base':
            out.append(('extra', g, gr / 1000.0, [x, y, z]))
        elif g == 'ycar':
            out.append(('extra', g, gr / 1000.0, [x, PYC + y, z]))
        else:
            out.append(('extra', g, gr / 1000.0, [PXB + x, PYC + y, z]))
    return out

def total(ms, pred=lambda g: True):
    m = sum(x[2] for x in ms if pred(x[1]))
    c = [sum(x[2] * x[3][i] for x in ms if pred(x[1])) / m for i in range(3)]
    return m, c

FEET_X = (min(x for x, y in F.FEET), max(x for x, y in F.FEET))
FEET_Y = (min(y for x, y in F.FEET), max(y for x, y in F.FEET))

def tipping(ms):
    """Static margin and the acceleration that would tip the device, per direction.
    Moving groups accelerate; inertial moment about a foot edge = sum m a z."""
    M, c = total(ms)
    mov = [x for x in ms if x[1] != 'base']
    res = {'mass_kg': round(M, 3), 'com': [round(v, 1) for v in c]}
    # X motion moves only the X carriage side (wrist + X chain); Y motion moves ycar + wrist + chains
    xm = [x for x in mov if x[1].startswith('wm_') or x[1] == 'chainX']
    ym = mov
    for axis, grp, lo, hi, i in (('x', xm, FEET_X[0], FEET_X[1], 0), ('y', ym, FEET_Y[0], FEET_Y[1], 1)):
        mz = sum(x[2] * x[3][2] for x in grp) / 1000.0           # kg m
        for sgn, edge in ((-1, lo), (1, hi)):
            arm = abs(c[i] - edge) / 1000.0                      # m, static restoring arm
            # tipping toward 'edge' needs inertial force pointing to it: a_tip = M g arm / (sum m z)
            a_tip = M * G * arm / mz if mz > 0 else float('inf')
            res['%s%s' % ('+' if sgn > 0 else '-', axis)] = {'static_margin_mm': round(arm * 1000, 1), 'tips_at_m_s2': round(a_tip, 1),
                                                           'safety_at_design_acc': round(a_tip / ACC, 1)}
    return res

def rail_loads(ms, PYC, PXB):
    """Moments on the two MGN12H blocks (rated MR 38.4, MP 37.5, MY 37.5 N m, C0 5.9 kN)."""
    zY = F.Z_YBLK0 + 5.0                                          # Y block centre
    carried = [x for x in ms if x[1] != 'base' and x[1] != 'chainY']
    m, c = total(carried, lambda g: True)
    dx, dy, dz = (c[0] - F.YB_X) / 1000, (c[1] - PYC) / 1000, (c[2] - zY) / 1000
    y_blk = {'mass_kg': round(m, 3), 'MR_roll_Nm': round(m * G * abs(dx), 2),
             'MP_pitch_Nm': round(m * (G * abs(dy) + ACC * abs(dz)), 2), 'MY_yaw_Nm': round(m * ACC * abs(dx), 2)}
    wm = [x for x in ms if x[1].startswith('wm_')]
    m2, c2 = total(wm)
    zX = 152.0 - 8.0 - 5.0
    dx2, dy2, dz2 = (c2[0] - PXB) / 1000, (c2[1] - PYC) / 1000, (c2[2] - zX) / 1000
    x_blk = {'mass_kg': round(m2, 3), 'MR_roll_Nm': round(m2 * G * abs(dy2), 2),
             'MP_pitch_Nm': round(m2 * (G * abs(dx2) + ACC * abs(dz2)), 2), 'MY_yaw_Nm': round(m2 * ACC * abs(dy2), 2)}
    worst = max(max(v for k, v in d.items() if k.endswith('Nm')) for d in (y_blk, x_blk))
    return {'y_block': y_blk, 'x_block': x_blk, 'worst_Nm': worst, 'margin_vs_37_5': round(37.5 / worst, 1)}

def deflection(ms, PYC, PXB):
    """Sag of the magnet from the boom (cantilever from the post face) and the post (2020, fixed in the
    socket). 2020 profile: I = 0.69 cm4 (6900 mm4), E = 69 GPa. Joints (corner brackets, printed socket)
    are taken as rigid, so the real sag is larger: treat this as the profile part only."""
    E, I = 69000.0, 6900.0
    wm = [x for x in ms if x[1].startswith('wm_') or x[1] == 'chainX']
    m, c = total(wm)
    F_N = m * G
    a = c[0] - F.BOOM_X0                                         # mm, load position from the post face
    boom_tip = F_N * a ** 2 * (3 * (A.W.MAG_X + PXB - F.BOOM_X0) - a) / (6 * E * I)   # at the magnet x
    boom_own = 0.135 * G * (F.BOOM_X1 - F.BOOM_X0) ** 3 / (8 * E * I)
    Lp = (F.Z_BOOM0 + F.Z_BOOM1) / 2 - (F.Z_YC1 + F.SOCKET_H)  # free post length
    Mp = F_N * a + 0.135 * G * (F.BOOM_X1 - F.BOOM_X0) / 2        # N mm at the post top
    theta = Mp * Lp / (E * I)
    post_tip = theta * (A.W.MAG_X + PXB - F.POST_C[0])
    # X acceleration: the wrist mass swings the boom sideways (bending about the boom's other axis, same I)
    side = m * ACC * a ** 3 / (3 * E * I)
    return {'load_kg': round(m, 3), 'boom_sag_mm': round(boom_tip + boom_own, 3), 'post_tilt_sag_mm': round(post_tip, 3),
            'total_profile_sag_mm': round(boom_tip + boom_own + post_tip, 3), 'boom_side_flex_at_design_acc_mm': round(side, 4)}

BELT_EA = 25000.0             # N, GT2 6 mm glass-cord belt, axial stiffness EA (typical published figure; steel cord is stiffer)
STEP_TORQUE = 0.45           # N m holding torque, 17HS16-2004S1
MG996R_PLAY_DEG = 1.0        # gear play at the servo output (typical for metal-gear hobby servos)   VERIFY: measure yours

def backlash(ms):
    """Lost motion at the magnet when an axis reverses at the design acceleration (mm): belt stretch on both
    strands from the clamp to the motor pulley, stepper load angle, belt-to-pulley tooth clearance, and the
    printed mounts (out/fea.json). Worst carriage position for the belt (clamp farthest from the motor)."""
    fea = {}
    p = os.path.join(HERE, 'out', 'fea.json')
    if os.path.exists(p):
        fea = json.load(open(p))
    import wrist_module as W
    loop = lambda a, b: 2 * abs(b - a) + math.pi * F.GT2_PD          # belt path length around both pulleys
    m_y = total([x for x in ms if x[1] != 'base' and x[1] != 'chainY'])[0]
    m_x = total([x for x in ms if x[1].startswith('wm_') or x[1] == 'chainX'])[0]
    out = {}
    # Y: clamp middle at PYC0 + 15 (park, farthest from the motor at y 443)
    yc = F.Y_BELT_GAP
    L1 = F.YM_C[0] - yc                                               # upper strand, clamp -> motor
    L2 = loop(F.YI_C[0], F.YM_C[0]) - L1                              # the other way round, via the idler
    # X: clamp middle at PXB + X_BELT_GAP, farthest from the motor (x 165) at PXB 452
    xc = F.PXB_RANGE[1] + W.X_BELT_GAP
    X1 = xc - F.XM_C[0]
    X2 = loop(F.XM_C[0], F.XI_C[0]) - X1
    for ax, m, a, b, mount in (('y', m_y, L1, L2, 'y_motor_mount'), ('x', m_x, X1, X2, 'x_motor_mount')):
        Fd = m * ACC                                                  # N
        k = BELT_EA / a + BELT_EA / b                                 # both strands act (pretensioned)
        belt = Fd / k
        lag = math.asin(min(1.0, Fd * F.GT2_PD / 2000.0 / STEP_TORQUE)) * 2 / math.pi * 1.8   # deg of shaft (load angle, sine torque curve)
        motor = lag / 360.0 * math.pi * F.GT2_PD
        mt = fea.get(mount, {}).get('move_mm', 0.0) * Fd / 50.0         # mount moves in proportion to the force change
        teeth = 0.05                                                  # GT2 tooth clearance on reversal (profile is made for it)
        out[ax] = {'moving_kg': round(m, 3), 'force_N': round(Fd, 2), 'belt_mm': round(belt, 4), 'stepper_mm': round(motor, 4),
                   'mount_mm': round(mt, 4), 'tooth_clearance_mm': teeth, 'total_reversal_mm': round(2 * (belt + motor + mt) + teeth, 3)}
    # wrist: servo gear play tilts the parallelogram: vertical only (the magnet stays level)
    out['magnet_height_play_mm'] = round(W.R_ARM * math.radians(MG996R_PLAY_DEG), 2)
    out['note'] = ('XY lost motion is ~0.1 mm per axis against the 10 mm placement tolerance. Keep it that way: GT2 pulleys '
                   'with two grub screws (one on the shaft flat, Loctite 243), belts tensioned to ~25 N, a full homing each run. '
                   'The servo play only changes the magnet height (it lands on the checker anyway).')
    return out

MG996R_STALL_NM = 1.08       # N m stall torque at 6 V (11 kg cm, datasheet; 0.92 at 4.8 V)
SERVO_LIFT_ACC = 2.0         # m/s^2 vertical acceleration of the end when the servo lifts

def servo_torque(ms, PXB):
    """Torque the MG996R needs to hold / lift the parallelogram, arms level (worst case, cos = 1).
    Virtual work: everything on the end plate (shelf, stepper, hub, magnet, camera, their screws) rises R_ARM dtheta;
    each arm rises by its centre of mass distance from its pivot A. The wrist harness counts at half the arm length."""
    import wrist_module as W
    R = W.R_ARM / 1000.0
    m_end = sum(x[2] for x in ms if x[1] in ('wm_end', 'wm_wrist'))
    t = m_end * (G + SERVO_LIFT_ACC) * R
    for g in ('wm_armT', 'wm_armB'):
        for x in ms:
            if x[1] == g:
                t += x[2] * (G + SERVO_LIFT_ACC) * (x[3][0] - PXB) / 1000.0
    m_cab = sum(x[2] for x in ms if x[1] == 'wm_cable')
    t += m_cab * G * R / 2
    motor = MASS_G['wm_nema17p'] / 1000.0
    return {'end_mass_kg': round(m_end, 3), 'wrist_stepper_kg': motor, 'needed_Nm': round(t, 3),
            'stall_6V_Nm': MG996R_STALL_NM, 'stall_margin': round(MG996R_STALL_NM / t, 1),
            'load_vs_stall_pct': round(100 * t / MG996R_STALL_NM, 1),
            'note': 'keep the steady load under ~30-40 % of stall for a long servo life (hobby servo rule of thumb)'}

if __name__ == '__main__':
    R = {'design_acc_m_s2': ACC}
    worst_tip, worst_rail, worst_def = None, None, None
    table = []
    for p in [(40.0, 287.0, 40.0, 0.0), (376.0, 452.0, 5.0, 0.0), (40.0, 452.0, 5.0, 0.0), (376.0, 287.0, 40.0, 0.0), (208.0, 340.0, 22.5, 0.0)]:
        ms = masses(*p)
        t = tipping(ms)
        r = rail_loads(ms, p[0], p[1])
        d = deflection(ms, p[0], p[1])
        table.append({'pose': p, 'tipping': t, 'rails': r, 'deflection': d})
    R['poses'] = table
    ms = masses(F.PYC0, F.PXB0, 40.0, 0.0)
    groups = {}
    for k, g, m, c in ms:
        gg = 'base' if g == 'base' else ('Y carriage + boom' if g == 'ycar' else ('wrist module' if g.startswith('wm_') else 'cable chains'))
        groups[gg] = round(groups.get(gg, 0) + m, 3)
    R['mass_by_group_kg'] = groups
    R['backlash'] = backlash(masses(F.PYC0, F.PXB_RANGE[1], A.W.H_MIN, 0.0))
    R['servo_lift'] = servo_torque(masses(F.PYC0, F.PXB0, A.W.H_MID, 0.0), F.PXB0)
    R['min_tip_acc_m_s2'] = min(v['tips_at_m_s2'] for e in table for k, v in e['tipping'].items() if isinstance(v, dict))
    R['min_static_margin_mm'] = min(v['static_margin_mm'] for e in table for k, v in e['tipping'].items() if isinstance(v, dict))
    R['worst_rail_moment_Nm'] = max(e['rails']['worst_Nm'] for e in table)
    R['worst_sag_mm'] = max(e['deflection']['total_profile_sag_mm'] for e in table)
    json.dump(R, open(os.path.join(HERE, 'out', 'stability.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in R.items() if k != 'poses'}, indent=1))
    for e in table:
        print(e['pose'], 'mass', e['tipping']['mass_kg'], 'com', e['tipping']['com'],
              {k: (v['static_margin_mm'], v['tips_at_m_s2']) for k, v in e['tipping'].items() if isinstance(v, dict)})
        print('   rails', e['rails'], '\n   defl', e['deflection'])
