"""Assembly simulation: can a person actually put the plotter together, in this order, with normal tools?

For every step of SEQUENCE (machine or bench sub-assembly) it checks:
  1. part insertion   - the part (or sub-assembly) slides into place along one of the six axis directions
                        without hitting anything already fitted (flexible items - belts, cables, chains, zip ties -
                        are pushed aside by hand, so they are not obstacles);
  2. screw entry      - the screw head can travel in along its axis from outside, clear of fitted parts;
  3. tool access      - a hex key / screwdriver reaches the head: a straight driver (80 mm shaft) or an L-key
                        (short arm in the socket, long arm swinging >= 60 deg); Phillips: stubby or long driver;
  4. nuts             - the nut can be put on the tip and held: a socket (30 mm) or an open spanner swinging 60 deg;
  5. drop-in T-nuts   - the slot mouth is open (not yet covered) when the T-nut must go in;
  6. heat-set inserts - the soldering iron reaches the insert hole on the bare printed part.
Every screw is checked at the earliest moment it can go in (right after the last part it joins is fitted); if it
fails in the parked pose the moving axes are tried in other positions (you can push the carriages by hand).
Result -> out/assembly_sim.json and a short text summary.
Run: ./fcpy tools/assembly_sim.py   (about 10-20 min)
"""
import os, sys, json, math, time
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (HERE, os.path.join(HERE, 'wrist'), os.path.join(HERE, 'frame')):
    sys.path.insert(0, p)
import FreeCAD as App
import Part
import assembly as A
import fasteners as FA
import frame as Fr
import wrist_module as W

V = App.Vector
T0 = time.time()

# ------------------------------------------------------------------ tool sizes (mm)
KEY = {('cap', 2): 1.5, ('cap', 2.5): 2.0, ('cap', 3): 2.5, ('cap', 4): 3.0, ('cap', 5): 4.0,
       ('button', 3): 2.0, ('button', 4): 2.5, ('button', 5): 3.0, ('csk', 3): 2.0, ('csk', 4): 2.5, ('csk', 5): 3.0}
LKEY_SHORT = {1.5: 14, 2.0: 16, 2.5: 18, 3.0: 20, 4.0: 25}        # short arm of an L hex key
LKEY_LONG = 45                                                     # length of the long arm that must swing
DRIVER_L = 80                                                      # straight hex / Phillips driver shaft
STUBBY = (25, 3.0, 40, 13.0)                                       # Phillips stubby: shaft L, r, handle L, r
SOCKET_L, SPANNER_L = 30, 70
MIN_VOL = 0.5                                                      # mm3 of overlap that counts as a hit
FLEX = ('cable_', 'zip_tie', 'wm_zip_', 'y_belt_gt2', 'x_belt_gt2', 'battery_strap')

# poses to try when something is blocked in the parked pose (carriages can be pushed by hand, the lift turned)
PARK = (Fr.PYC0, Fr.PXB0, W.H_MAX, 0.0)
POSES = [PARK, (208.0, 287.0, W.H_MAX, 0.0), (376.0, 287.0, W.H_MAX, 0.0), (40.0, 430.0, W.H_MAX, 0.0), (208.0, 360.0, W.H_MAX, 0.0),
         (376.0, 430.0, W.H_MAX, 0.0), (208.0, 360.0, W.H_MIN, 0.0), (208.0, 360.0, W.H_MIN, 90.0), (208.0, 430.0, W.H_MIN, 45.0)]

# ------------------------------------------------------------------ the assembly order
# (step label, context, [part name prefixes]); context 'machine' or 'bench:<name>'; ('mount', '<name>') fits a
# finished bench sub-assembly onto the machine as one piece. Every rigid part must appear once.
SEQUENCE = [
    ('1 base: plywood and rubber feet', 'machine', ['plywood_base', 'rubber_foot']),
    ('1 base: Y beam risers', 'machine', ['y_beam_riser']),
    ('1 base: Y beam', 'machine', ['y_beam_2020']),
    ('1 base: Y rail with its block', 'machine', ['y_rail_mgn12_400', 'y_block_mgn12h']),
    ('1 base: Y motor mount', 'machine', ['y_motor_mount']),
    ('1 base: Y motor with pulley', 'machine', ['y_motor_17HS16', 'y_pulley_gt2_20t']),
    ('1 bench: Y idler unit', 'bench:yidler', ['y_idler_bracket', 'y_idler_slider', 'y_idler_gt2_20t']),
    ('1 base: fit the Y idler unit', ('mount', 'yidler'), []),
    ('1 base: Y home switch', 'machine', ['y_home_switch_d2f']),
    ('1 base: Y carriage on the block', 'machine', ['y_carriage']),
    ('1 base: Y belt spacer and clamp', 'machine', ['y_belt_spacer', 'y_belt_clamp']),
    ('2 X: post in the socket', 'machine', ['post_2020_130']),
    ('2 X: boom', 'machine', ['boom_2020_270']),
    ('2 X: corner brackets', 'machine', ['corner_bracket']),
    ('2 X: post cap', 'machine', ['post_cap']),
    ('2 X: X rail with its block', 'machine', ['x_rail_mgn12_250', 'wm_mgn12h_block']),
    ('2 X: X motor mount', 'machine', ['x_motor_mount']),
    ('2 X: X motor with pulley', 'machine', ['x_motor_17HS16', 'x_pulley_gt2_20t']),
    ('2 X: X home switch', 'machine', ['x_home_switch_d2f']),
    ('2 bench: X idler unit', 'bench:xidler', ['x_idler_bracket', 'x_idler_slider', 'x_idler_gt2_20t']),
    ('2 X: fit the X idler unit', ('mount', 'xidler'), []),
    ('3 X: wrist carriage plate on the X block', 'machine', ['wm_wrist_carriage']),
    ('3 X: belt riser, clamp, chain post', 'machine', ['wm_x_belt_riser', 'wm_x_belt_clamp', 'wm_chain_post']),
    ('3 X: servo', 'machine', ['wm_servo_case', 'wm_servo_tabs', 'wm_servo_spline']),
    ('3 X: lower arm with bearings', 'machine', ['wm_arm_bottom', 'wm_brg_AL', 'wm_brg_BL']),
    ('3 X: lower pivot spacer and shim', 'machine', ['wm_spacer_AL', 'wm_shim_AL']),
    ('3 X: horn', 'machine', ['wm_servo_horn']),
    ('3 X: top arm with bearing', 'machine', ['wm_arm_top', 'wm_brg_BT']),
    ('3 X: end pivots spacers and shims', 'machine', ['wm_spacer_BT', 'wm_spacer_BL', 'wm_shim_BT', 'wm_shim_BL']),
    ('3 X: end plate', 'machine', ['wm_end_plate']),
    ('3 X: shelf', 'machine', ['wm_shelf']),
    ('3 X: wrist motor', 'machine', ['wm_nema17p']),
    ('3 X: magnet screwed to the hub', 'bench:hub', ['wm_wrist_hub', 'wm_electromagnet']),
    ('3 X: hub pushed onto the wrist motor shaft', ('mount', 'hub'), []),
    ('3 X: camera', 'machine', ['wm_camera']),
    ('4 bench: controller board', 'bench:board', ['perfboard', 'header_esp32', 'header_tmc', 'tmc2209', 'pololu']),
    ('4 base: standoffs', 'machine', ['standoff']),
    ('4 base: fit the controller board', ('mount', 'board'), []),
    ('4 base: plug the ESP32 board in', 'machine', ['esp32']),
    ('4 bench: control panel', 'bench:panel', ['control_panel', 'estop', 'start_button', 'led_', 'connector_pcb', 'header_A', 'header_B', 'header_C']),
    ('4 base: fit the control panel', ('mount', 'panel'), []),
    ('4 base: battery tray and battery', 'machine', ['battery_tray', 'battery_4s']),
    ('4 base: breadboard tray and breadboard', 'machine', ['breadboard_tray', 'breadboard_400']),
    ('5 cables: Y chain guide', 'machine', ['y_chain_guide']),
    ('5 cables: chains', 'machine', ['cable_chain']),
]

# ------------------------------------------------------------------ helpers
_WORLD = {}
def world(pose):
    if pose not in _WORLD:
        _WORLD[pose] = A.world(*pose, field=False, cables=False, fasteners=True)
    return _WORLD[pose]

def flexible(n):
    return n.startswith(FLEX)

def hit_volume(s, names, parts, skip=()):
    """Overlap of shape s with the named parts (bbox filter first). Returns (worst name, volume)."""
    bb = s.BoundBox
    worst = (None, 0.0)
    for n in names:
        if n in skip:
            continue
        o = parts[n][0]
        if not bb.intersect(o.BoundBox):
            continue
        try:
            v = s.common(o).Volume
        except Exception:
            v = 0.0
        if v > MIN_VOL and v > worst[1]:
            worst = (n, v)
    return worst

def cyl(p, d, r, L):
    return Part.makeCylinder(r, L, p, d)

def perp(d):
    return FA._perp(d)

# ------------------------------------------------------------------ fastener bookkeeping
FL, PIECES = FA.all_fasteners()
FBY = {f.name: f for f in FL}

def fpieces(f, parts):
    return {s: f.name + '_' + s for s in PIECES[f.name] if f.name + '_' + s in parts}

def solid_pieces(f, parts):
    return [n for s, n in fpieces(f, parts).items() if s not in ('insert', 'tnut')]

def joined_parts(f, parts, rigid):
    """Rigid parts the fastener's head / shank / nut / washer touch in the finished machine."""
    out = set()
    for pn in solid_pieces(f, parts):
        s = parts[pn][0]
        bb = s.BoundBox
        bb.enlarge(0.5)
        for n in rigid:
            o = parts[n][0]
            if not bb.intersect(o.BoundBox):
                continue
            if s.distToShape(o)[0] < 0.45:
                out.add(n)
    if f.tnut:
        out.update(n for n in rigid if n.startswith(f.tnut[2]) and parts[n][0].BoundBox.intersect(parts[f.name + '_tnut'][0].BoundBox))
    if f.insert:
        out.update(n for n in rigid if n == f.insert[0])
    return out

# ------------------------------------------------------------------ the checks
def check_insert(moving, obstacles, parts):
    """Try to bring the moving parts in from outside along each axis direction. Returns (direction, None) or (None, worst hit)."""
    ms = [parts[n][0] for n in moving]
    mbb = ms[0].BoundBox
    for s in ms[1:]:
        mbb.add(s.BoundBox)
    obs = [n for n in obstacles if not any(A.allowed(n, m) for m in moving)]
    worst = None
    for d in (V(0, 0, 1), V(0, 0, -1), V(1, 0, 0), V(-1, 0, 0), V(0, 1, 0), V(0, -1, 0)):
        ok, t = True, 1.0
        while ok:
            b = App.BoundBox(mbb.XMin + d.x * t, mbb.YMin + d.y * t, mbb.ZMin + d.z * t, mbb.XMax + d.x * t, mbb.YMax + d.y * t, mbb.ZMax + d.z * t)
            near = [n for n in obs if b.intersect(parts[n][0].BoundBox)]
            if not near:
                return (tuple(d), round(t, 1)), None
            for n, s in zip(moving, ms):
                s2 = s.copy()
                s2.translate(d * t)
                h = hit_volume(s2, near, parts)
                if h[0]:
                    ok = False
                    if worst is None or t > worst[2]:
                        worst = (h[0], round(h[1], 1), round(t, 1), tuple(d), n)
                    break
            t += 1.5
            if t > 600:
                return (tuple(d), 600), None
    return None, worst

def place(s, f, pose):
    """Move a shape built in the fastener's own coordinates the way fasteners.placed() moves its pieces."""
    PYC, PXB, h, wd = pose
    if f.name.startswith('wm_'):
        s = W.pose(s, f.group, h, wd)
        s.translate(V(PXB, PYC, 0))
    elif f.group == 'ycar':
        s = s.copy()
        s.translate(V(0, PYC - Fr.PYC0, 0))
    return s

def tool_access(f, parts, obstacles, pose=PARK):
    """Screw entry + tool for one fastener. Returns (ok, detail)."""
    _cyl = cyl
    cyl_ = lambda p, d, r, L: place(_cyl(p, d, r, L), f, pose)
    own = set(n for n in parts if n.startswith(f.name + '_'))
    obs = [n for n in obstacles if n not in own]
    D, H = FA.HEAD[f.std][f.dia]
    d = f.d
    wt = FA.WASHER[f.dia][1] if f.head_washer else 0.0
    q = f.p - d * wt                                  # seat of the head
    top = q - d * H if f.std != 'csk' else f.p        # head top (where the tool goes)
    res = {}
    # 1. entry: the head travels in from outside along the axis
    if f.std == 'set':
        res['entry'] = None
    else:
        entry = cyl_(q - d * (H + f.L + 5), d, D / 2 - 0.3, f.L + 5)
        res['entry'] = hit_volume(entry, obs, parts)[0]
    # 2. tool
    tool_ok, tools = False, []
    if f.std == 'set':
        res['tool'] = ['hex key 1.5 from below, before the magnet goes on (stud)']
        return True, res
    if f.std == 'pan' and f.dia <= 2.5:
        a = cyl_(top - d * 60.0, d, 1.5, 60.0).fuse(cyl_(top - d * 120.0, d, 7.0, 60.0))     # precision PH0 x 60 driver
        ha = hit_volume(a, obs, parts)
        if not ha[0]:
            tool_ok = True; tools.append('precision Phillips')
        b = cyl_(top - d * 30.0, d, 1.5, 30.0).fuse(cyl_(top - d * 55.0, d, 9.0, 25.0))      # short bit in a stubby holder
        hb = hit_volume(b, obs, parts)
        if not hb[0]:
            tool_ok = True; tools.append('stubby Phillips bit')
        if not tool_ok:
            res['tool_hit'] = [ha[0], hb[0]]
    elif f.std == 'pan':
        a = cyl_(top - d * STUBBY[0], d, STUBBY[1], STUBBY[0]).fuse(cyl_(top - d * (STUBBY[0] + STUBBY[2]), d, STUBBY[3], STUBBY[2]))
        ha = hit_volume(a, obs, parts)
        if not ha[0]:
            tool_ok = True; tools.append('stubby Phillips')
        b = cyl_(top - d * DRIVER_L, d, 3.0, DRIVER_L)
        hb = hit_volume(b, obs, parts)
        if not hb[0]:
            tool_ok = True; tools.append('long Phillips')
        if not tool_ok:
            res['tool_hit'] = [ha[0], hb[0]]
    else:
        k = KEY[(f.std, f.dia)]
        r = k * 0.6 + 0.2
        b = cyl_(top - d * DRIVER_L, d, r, DRIVER_L)
        hb = hit_volume(b, obs, parts)
        if not hb[0]:
            tool_ok = True; tools.append('straight %g hex driver' % k)
        S = LKEY_SHORT[k]
        sh = cyl_(top - d * S, d, r, S)
        if not hit_volume(sh, obs, parts)[0]:
            u, w = perp(d)
            free = []
            elbow = top - d * (S - r)
            for i in range(12):
                a = math.radians(30 * i)
                rd = u * math.cos(a) + w * math.sin(a)
                arm = cyl_(elbow, rd, r, LKEY_LONG)
                free.append(not hit_volume(arm, obs, parts)[0])
            if any(free[i] and free[(i + 1) % 12] and free[(i + 2) % 12] for i in range(12)):
                tool_ok = True; tools.append('L hex key %g' % k)
        if not tool_ok:
            res['tool_hit'] = hb[0]
    res['tool'] = tools
    # 3. nut on the far side
    nut_ok = True
    if f.nut:
        kind, at = f.nut
        af, m = FA.NUT[kind][f.dia]
        a0 = f.p + d * at + (d * FA.WASHER[f.dia][1] if f.nut_washer else V(0, 0, 0))
        R = af / math.sqrt(3)
        # the nut is brought to the tip along the axis (fingers / tweezers): its own path must be free
        path = cyl_(a0 + d * m, d, R + 0.3, m + 6)
        free_path = not hit_volume(path, obs, parts)[0]
        sock = cyl_(a0, d, R + (1.0 if f.dia <= 2.5 else 2.5), SOCKET_L)
        hs = hit_volume(sock, obs, parts)
        s_ok = not hs[0]
        u, w = perp(d)
        free = []
        for i in range(12):
            an = math.radians(30 * i)
            rd = u * math.cos(an) + w * math.sin(an)
            c = a0 + rd * (SPANNER_L / 2)
            slab = place(FA._obox(c + d * (m / 2), d, tuple(rd), m, SPANNER_L, af + 6), f, pose)
            hsl = hit_volume(slab, obs, parts)
            free.append(not hsl[0])
            if hsl[0]: res.setdefault('spanner_hits', set()).add(hsl[0])
        sp_ok = any(free[i] and free[(i + 1) % 12] and free[(i + 2) % 12] for i in range(12))
        jam = bool(f.insert)
        nut_ok = (s_ok or sp_ok) if jam else (free_path and (s_ok or sp_ok))
        res['nut'] = {'path_free': free_path, 'socket': s_ok or hs[0], 'spanner': sp_ok}
    ok = res['entry'] is None and tool_ok and nut_ok
    return ok, res

def tnut_open(f, parts, obstacles, profile):
    """Before the clamped part goes on, the slot mouth over the T-nut must be open (drop-in from the face)."""
    surf, axis, prof = f.tnut
    d = f.d
    mouth = f.p + d * surf                             # profile face
    ax = V(*axis); ax.normalize()
    box = place(FA._obox(mouth - d * 8.0, d, axis, 16.0, 12.0, 7.0), f, PARK)
    obs = [n for n in obstacles if n != profile and not n.startswith(f.name)]
    h = hit_volume(box, obs, parts)
    return h[0]

def iron_access(f, parts, host):
    if host not in parts:
        return 'host %s missing' % host
    hn, at = f.insert
    d = f.d
    worst = None
    for mouth, dd in ((f.p + d * at, d), (f.p + d * (at + FA.INSERT_L), -d)):
        iron = place(cyl(mouth - dd * 12.0, dd, 2.6, 11.5).fuse(cyl(mouth - dd * 70.0, dd, 6.0, 58.0)), f, PARK)
        h = hit_volume(iron, [host], parts)
        if not h[0]:
            return None
        worst = h[0]
    return worst

# ------------------------------------------------------------------ run
def main():
    parts = world(PARK)
    rigid = [n for n, v in parts.items() if v[2] != 'fastener' and not flexible(n)]
    # step and context of every rigid part
    where, seq_parts = {}, []
    for i, (lab, ctx, prefs) in enumerate(SEQUENCE):
        mine = [n for n in rigid if n not in where and any(n.startswith(p) for p in prefs)]
        for n in mine:
            where[n] = (i, ctx)
        seq_parts.append(mine)
    unassigned = [n for n in rigid if n not in where]
    mount_step = {ctx[1]: i for i, (lab, ctx, prefs) in enumerate(SEQUENCE) if isinstance(ctx, tuple)}

    def on_machine_at(n):
        i, ctx = where[n]
        if ctx == 'machine':
            return i
        return mount_step[ctx.split(':')[1]]

    # fasteners: when and where they go in
    fplan = {}
    for f in FL:
        J = joined_parts(f, parts, rigid)
        if not J:
            fplan[f.name] = ('?', None, J); continue
        ctxs = set(where[n][1] for n in J if n in where)
        if len(ctxs) == 1 and list(ctxs)[0] != 'machine':
            ctx = list(ctxs)[0]
            fplan[f.name] = (ctx, max(where[n][0] for n in J), J)
        else:
            fplan[f.name] = ('machine', max(on_machine_at(n) for n in J if n in where), J)

    report = {'steps': [], 'problems': [], 'unassigned_parts': unassigned}
    present = {'machine': []}
    present_f = {'machine': []}
    benches = {}

    def obstacles_for(ctx):
        return present[ctx] + present_f[ctx]

    nprob = 0
    for i, (lab, ctx, prefs) in enumerate(SEQUENCE):
        step = {'step': lab, 'parts': seq_parts[i], 'fasteners': {}}
        if isinstance(ctx, tuple):
            b = ctx[1]
            moving = present['bench:' + b] + present_f['bench:' + b]
            mv = [n for n in moving if parts[n][2] != 'fastener' or not n.endswith(('_insert', '_tnut'))]
            dirn, hit = check_insert(mv, obstacles_for('machine'), parts)
            step['insert'] = dirn if dirn else {'blocked': hit}
            if not dirn:
                report['problems'].append({'step': lab, 'what': 'sub-assembly cannot be fitted', 'hit': hit})
            present['machine'] += present['bench:' + b]
            present_f['machine'] += present_f['bench:' + b]
            c = 'machine'
        else:
            c = ctx
            present.setdefault(c, []); present_f.setdefault(c, [])
            if seq_parts[i]:
                dirn, hit = check_insert(seq_parts[i], obstacles_for(c), parts)
                step['insert'] = dirn if dirn else {'blocked': hit}
                if not dirn:
                    report['problems'].append({'step': lab, 'what': 'part cannot be put in place', 'hit': hit})
            # T-nuts for screws in this step's parts must be dropped in before them
            for f in FL:
                if f.tnut and fplan[f.name][1] == i and fplan[f.name][0] == c:
                    prof = [n for n in fplan[f.name][2] if n.startswith(f.tnut[2])]
                    prof = prof[0] if prof else f.tnut[2]
                    if prof in seq_parts[i]:
                        continue                           # T-nut goes into the loose profile
                    blk = tnut_open(f, parts, [n for n in obstacles_for(c)], prof)
                    if blk:
                        report['problems'].append({'step': lab, 'what': 'T-nut slot already covered for %s' % f.name, 'hit': blk})
            present[c] += seq_parts[i]
        # screws that can go in now
        for f in FL:
            fc, fi, J = fplan[f.name]
            if fi != i or fc != c:
                continue
            if f.insert:
                host = f.insert[0]
                blk = iron_access(f, parts, host)
                if blk:
                    report['problems'].append({'step': lab, 'what': 'soldering iron cannot reach the insert of %s' % f.name, 'hit': blk})
            ok, det = tool_access(f, parts, obstacles_for(c))
            tried = ['parked']
            if not ok and c == 'machine':
                for pose in POSES[1:]:
                    pp = world(pose)
                    ok2, det2 = tool_access_pose(f, pp, obstacles_for(c), pose)
                    tried.append(str(pose))
                    if ok2:
                        ok, det = True, dict(det2, pose=pose)
                        break
            step['fasteners'][f.name] = det if ok else dict(det, failed=True)
            if not ok:
                report['problems'].append({'step': lab, 'what': 'cannot fit %s (%s)' % (f.name, f.note), 'detail': det, 'poses_tried': len(tried)})
            present_f[c] += solid_pieces(f, parts)
        report['steps'].append(step)
        for pr in report['problems'][nprob:]:
            print('   PROBLEM', pr['what'], '|', str(pr.get('hit') or pr.get('detail'))[:300], flush=True)
        nprob = len(report['problems'])
        print('%5.0fs  %s  (%d problems so far)' % (time.time() - T0, lab, len(report['problems'])), flush=True)
    report['fasteners_without_parts'] = [k for k, v in fplan.items() if v[0] == '?']
    report['fastener_plan'] = {k: [str(v[0]), v[1], sorted(v[2])] for k, v in fplan.items()}
    json.dump(report, open(os.path.join(HERE, 'out', 'assembly_sim.json'), 'w'), indent=1, default=str)
    print('problems:', len(report['problems']))
    for p in report['problems']:
        print(' -', p['step'], '|', p['what'], '|', p.get('hit') or p.get('detail'))
    print('unassigned parts:', unassigned)
    print('fasteners touching no part:', report['fasteners_without_parts'])

def tool_access_pose(f, pp, obstacles, pose):
    # same names, shapes from the other pose
    return tool_access(f, pp, [n for n in obstacles if n in pp], pose)

main()
sys.stdout.flush(); os._exit(0)
