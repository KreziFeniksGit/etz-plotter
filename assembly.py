"""
ETZ plotter v2: whole-device assembly, checks and export helpers.
  world(PYC, PXB, h, wrist_deg)  -> {name: (shape, group_label, kind, colour)} placed in polygon coordinates
  python assembly.py             -> collision sweep, footprint, DFM of the frame parts (out/assembly_review.json)
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'wrist'))
sys.path.insert(0, os.path.join(HERE, 'frame'))
import FreeCAD as App
import Part
import wrist_module as W
import frame as F
import chains as C
import cables as CB
import fasteners as FA

V = App.Vector
OUT = os.path.join(HERE, 'out')
os.makedirs(OUT, exist_ok=True)

# which tree branch each part goes into in the FreeCAD / STEP file
def branch(name, kind):
    if kind == 'fastener':
        return 'Fasteners'
    if name in ('polygon_600x500',) or name.startswith(('zone', 'field_area', 'sheet_a4', 'cell_centres', 'marker_')):
        return 'Field_reference'
    if name.startswith(('plywood', 'rubber_foot', 'y_beam', 'y_beam_riser', 'y_rail', 'y_motor', 'y_pulley', 'y_idler', 'y_belt_gt2', 'y_home', 'y_chain_guide')):
        return 'Base_and_Y_axis'
    if name.startswith(('y_block', 'y_carriage', 'y_belt_spacer', 'y_belt_clamp', 'post_', 'boom_', 'corner_bracket', 'x_rail',
                        'x_motor', 'x_pulley', 'x_idler', 'x_belt_gt2', 'x_home')):
        return 'Y_carriage_and_X_axis'
    if name.startswith('wm_'):
        return 'Wrist_module'
    if name.startswith(('cable_chain', 'cable_', 'zip_tie_')):
        return 'Cables_and_chains'
    return 'Electronics_and_controls'

WM_COLOUR = {'servo_case': 'servo', 'servo_tabs': 'servo', 'servo_spline': 'white', 'servo_horn': 'steel', 'nema17p': 'motor',
             'nema17p_pilot': 'motor', 'nema17p_shaft': 'steel', 'electromagnet': 'copper', 'camera_board': 'board', 'camera_lens': 'black',
             'mgn12h_block': 'steel'}
WM_COLOUR.update({k: 'black' for k in W.GROUP if k.startswith('zip_')})

_FRAME = None
_WM = None
_DET = None

def _cache():
    global _FRAME, _WM
    if _FRAME is None:
        _FRAME = dict(F.build_frame())
        parts, bought = W.build_all()
        _WM = (parts, bought)
    return _FRAME, _WM

def _detail():
    global _DET
    if _DET is None:
        _DET = (F.detailed(), W.detailed())
    return _DET

def world(PYC=F.PYC0, PXB=F.PXB0, h=W.H_MAX, wrist_deg=0.0, field=True, cables=True, fasteners=False, detail=False):
    """detail=True swaps in the real vendor STEP models (vendor/) where we have them."""
    frame, (wparts, wbought) = _cache()
    if detail:
        fd, wd = _detail()
        frame = dict(frame)
        for k, s in fd.items():
            frame[k] = (s,) + tuple(frame[k][1:])
        wbought = dict(wbought)
        for k, s in wd.items():
            if s is None:
                wbought.pop(k, None)
            else:
                wbought[k] = s
    out = {}
    dy = PYC - F.PYC0
    for k, (s, g, kind, col) in frame.items():
        s2 = s.copy()
        if g == 'ycar':
            s2.translate(V(0, dy, 0))
        out[k] = (s2, 'ycar' if g == 'ycar' else 'base', kind, col)
    for k, s in list(wparts.items()) + list(wbought.items()):
        if k == 'x_belt':
            continue                                    # the frame carries the whole X belt
        s2 = W.pose(s, W.GROUP[k], h, wrist_deg)
        s2.translate(V(PXB, PYC, 0))
        kind = 'printed' if k in wparts else 'bought'
        col = 'printed' if k in wparts else WM_COLOUR.get(k, 'steel')
        out['wm_' + k] = (s2, 'wm_' + W.GROUP[k], kind, col)
    xc, _ = C.x_chain(PYC, PXB)
    yc, _ = C.y_chain(PYC)
    out['cable_chain_x'] = (xc, 'chainX', 'bought', 'chain')
    out['cable_chain_y'] = (yc, 'chainY', 'bought', 'chain')
    if cables:
        out.update(CB.harness(PYC, PXB))
        out.update(CB.wrist_harness(PYC, PXB, h, wrist_deg))
    if fasteners:
        fp, _ = FA.placed(PYC, PXB, h, wrist_deg)
        out.update(fp)
    if field:
        for k, (s, col) in F.field_reference().items():
            out[k] = (s, 'field', 'reference', col)
    return out

# ------------------------------------------------------------------ checks
ALLOWED = [
    # designed contacts: belt in its clamps, shafts in pulleys, parts on the rails, switches pressed at home
    ('y_belt_gt2', 'y_belt_spacer'), ('y_belt_gt2', 'y_belt_clamp'), ('x_belt_gt2', 'wm_x_belt_riser'), ('x_belt_gt2', 'wm_x_belt_clamp'),
    ('y_motor_shaft', 'y_pulley_gt2_20t'), ('x_motor_shaft', 'x_pulley_gt2_20t'), ('y_belt_gt2', 'y_pulley_gt2_20t'),
    ('y_belt_gt2', 'y_idler_gt2_20t'), ('x_belt_gt2', 'x_pulley_gt2_20t'), ('x_belt_gt2', 'x_idler_gt2_20t'),
    ('wm_mgn12h_block', 'x_rail_mgn12_250'), ('y_block_mgn12h', 'y_rail_mgn12_400'),
    ('x_home_switch_d2f', 'wm_wrist_carriage'), ('y_home_switch_d2f', 'y_carriage'),
    ('battery_strap', 'battery_4s_2200'), ('battery_strap', 'battery_tray'), ('cable_chain_y', 'y_carriage'), ('cable_chain_y', 'y_chain_guide'), ('cable_chain_x', 'wm_chain_post'), ('cable_chain_x', 'boom_2020'), ('cable_chain', 'cable_'),
    ('wm_zip_', 'cable_'), ('zip_tie_', 'cable_'), ('cable_wrist_', 'cable_wrist_'), ('cable_wrist_stepper', 'wm_nema17p'), ('cable_wrist_servo', 'wm_servo_case'),
    ('led_', 'control_panel'), ('estop', 'control_panel'), ('start_button', 'control_panel'), ('header_', 'control_panel'),
    ('header_', 'connector_pcb'), ('standoff', 'perfboard'), ('standoff', 'plywood'),
] + [tuple('wm_' + x for x in p) for p in [
    ('servo_tabs', 'wrist_carriage'), ('servo_horn', 'arm_top'), ('servo_spline', 'servo_horn'), ('servo_case', 'servo_spline'),
    ('brg_AL', 'arm_bottom'), ('brg_BL', 'arm_bottom'), ('brg_BT', 'arm_top'), ('nema17p_shaft', 'wrist_hub'), ('nema17p_pilot', 'nema17p'),
    ('nema17p_shaft', 'nema17p_pilot'), ('electromagnet', 'wrist_hub'), ('camera_board', 'camera_lens'), ('servo_case', 'servo_tabs'),
    ('spacer_AL', 'brg_AL'), ('spacer_BT', 'brg_BT'), ('spacer_BL', 'brg_BL'), ('shim_BT', 'brg_BT'), ('shim_BL', 'brg_BL'),
    ('shim_AL', 'brg_AL'), ('nema17p', 'nema17p_shaft'), ('shim_BT', 'end_plate'), ('shim_BL', 'end_plate'), ('spacer_AL', 'wrist_carriage')]]

def allowed(a, b):
    for p, q in ALLOWED:
        if (a.startswith(p) and b.startswith(q)) or (a.startswith(q) and b.startswith(p)):
            return True
    return False

def collisions(parts, only_moving=False, tol=0.3):
    names = [k for k, v in parts.items() if v[1] != 'field']
    hits = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            A, B = parts[a], parts[b]
            if only_moving and A[1] == B[1]:
                continue
            if allowed(a, b):
                continue
            if A[2] == 'fastener' or B[2] == 'fastener':
                continue                                 # fasteners: see fastener_check()
            if (A[2] == 'cable' or B[2] == 'cable') and A[1] == B[1]:
                continue                                 # cables ride on their own group: see cable_contacts()
            if not A[0].BoundBox.intersect(B[0].BoundBox):
                continue
            try:
                v = A[0].common(B[0]).Volume
            except Exception:
                v = -1
            if v > tol or v < 0:
                hits['%s | %s' % (a, b)] = round(v, 2)
    return hits

def cable_contacts(parts, tol=0.5):
    """Cable tubes against parts of their own group (tied to them): any real overlap means the path
    goes through a part and must be moved. Chain mouths are allowed."""
    hits = {}
    cab = [k for k, v in parts.items() if v[2] == 'cable']
    for c in cab:
        for k, v in parts.items():
            if k == c or v[1] == 'field' or (v[1] != parts[c][1] and not k.startswith('cable_chain')):
                continue
            if k.startswith('cable_chain') or (v[2] == 'cable'):
                continue
            if not parts[c][0].BoundBox.intersect(v[0].BoundBox):
                continue
            vol = parts[c][0].common(v[0]).Volume
            if vol > tol:
                hits['%s | %s' % (c, k)] = round(vol, 2)
    return hits

def fastener_check(parts, only_moving=False, tol=0.2):
    """Every fastener piece against every other solid: only its allowed partners (its own nut/insert/T-nut,
    the part it threads into, parts without modelled holes such as switch bodies) may overlap."""
    _, allow = FA.placed(F.PYC0, F.PXB0, W.H_MAX, 0.0)
    names = [k for k, v in parts.items() if v[1] != 'field']
    hits = {}
    for n in [k for k in names if parts[k][2] == 'fastener']:
        own = n.rsplit('_', 1)[0] + '_'
        A_ = parts[n]
        for k in names:
            if k == n or k.startswith(own):
                continue
            B_ = parts[k]
            if only_moving and A_[1] == B_[1]:
                continue
            if B_[2] == 'fastener' and k < n:
                continue                                 # each fastener pair once
            if any(k.startswith(a) for a in allow[n]):
                continue
            if B_[2] == 'fastener':
                own2 = k.rsplit('_', 1)[0] + '_'
                _, al2 = FA.placed(F.PYC0, F.PXB0, W.H_MAX, 0.0) if False else (None, allow)
                if any(n.startswith(a) for a in allow[k]):
                    continue
            if not A_[0].BoundBox.intersect(B_[0].BoundBox):
                continue
            try:
                v = A_[0].common(B_[0]).Volume
            except Exception:
                v = -1
            if v > tol or v < 0:
                hits['%s | %s' % (n, k)] = round(v, 2)
    return hits

def fastener_engagement(parts):
    """Thread length of every screw in its target (sampled on the thread's outer radius), and whether a blind
    screw ends inside its target. Parked pose."""
    L, P = FA.all_fasteners()
    rep, bad = {}, {}
    for f in L:
        tn = f.target_name()
        tgt = None
        for k in parts:
            if k == tn or (tn and k.startswith(tn) and parts[k][2] != 'fastener'):
                tgt = parts[k][0]
                break
        if tgt is None:
            bad[f.name] = 'target %s not found' % tn
            continue
        u, w = FA._perp(f.d)
        r = 0.95 * f.dia / 2
        n = int(f.len_shank / 0.25)
        pts = []
        for i in range(n + 1):
            c = f.s0 + f.d * (f.len_shank * i / n)
            pts += [c + u * r, c - u * r, c + w * r, c - w * r]
        tipin = f.tip() - f.d * 0.3
        verts = Part.makeCompound([Part.Vertex(p) for p in pts] + [Part.Vertex(tipin + u * r), Part.Vertex(tipin - u * r)])
        if f.name.startswith('wm_'):
            verts = W.pose(verts, f.group, W.H_MAX, 0.0)
            verts.translate(V(F.PXB0, F.PYC0, 0))
        vp = [v.Point for v in verts.Vertexes]
        inside = 0
        for i in range(n + 1):
            k = sum(1 for p in vp[4 * i:4 * i + 4] if tgt.isInside(p, 0.01, True))
            inside += 1 if k >= 2 else 0
        eng = round(inside * f.len_shank / n, 2)
        if f.target[0] not in ('self', 'tapped'):        # solid targets: exact length from the overlap volume
            sh = None
            for kk, vv in parts.items():
                if kk == f.name + '_shank':
                    sh = vv[0]
            if sh is not None:
                eng = round(sh.common(tgt).Volume / (math.pi * (f.dia / 2) ** 2), 2)
        tip_ok = any(tgt.isInside(p, 0.01, True) for p in vp[-2:])
        kind, _, emin, emax = f.target
        rep[f.name] = {'screw': f.label(), 'into': kind, 'engagement_mm': eng}
        prob = []
        if eng < emin - 0.05:
            prob.append('engagement %.2f < %.1f' % (eng, emin))
        if emax is not None and eng > emax + 0.05:
            prob.append('engagement %.2f > %.1f (bottoms out)' % (eng, emax))
        if kind in ('blind', 'wood', 'self', 'tapped') and not tip_ok:
            prob.append('tip leaves the target')
        if kind == 'nut' and eng < f.nut_m - 0.3:
            prob.append('does not pass through the nut')
        if prob:
            bad[f.name] = '; '.join(prob) + ' (' + f.label() + ')'
    return rep, bad

def in_zones(x, y):
    if x < -0.01 or x > 600.01 or y < -0.01 or y > 500.01:
        return False
    return x <= 350.01 or y <= 80.01 or y >= 419.99

def footprint(parts):
    bad = {}
    for k, (s, g, kind, col) in parts.items():
        if g == 'field':
            continue
        vs, _ = s.tessellate(1.0)
        out = [(round(p.x, 1), round(p.y, 1)) for p in vs if not in_zones(p.x, p.y)]
        if out:
            bad[k] = out[:3]
    return bad

PRINT_ORIENT = {'y_motor_mount': (V(1, 0, 0), 0), 'y_idler_bracket': (V(1, 0, 0), 0), 'y_carriage': (V(1, 0, 0), 0),
                'y_belt_spacer': (V(1, 0, 0), 0), 'y_belt_clamp': (V(1, 0, 0), 0), 'post_cap': (V(1, 0, 0), 180),
                'x_motor_mount': (V(1, 0, 0), -90), 'x_idler_bracket': (V(0, 1, 0), 90), 'control_panel': (V(1, 0, 0), 180),
                'x_idler_slider': (V(1, 0, 0), 90), 'y_idler_slider': (V(0, 1, 0), 90),
                'breadboard_tray': (V(1, 0, 0), 0), 'battery_tray': (V(1, 0, 0), 0), 'y_chain_guide': (V(1, 0, 0), 0), 'y_beam_riser': (V(1, 0, 0), 0)}

def print_orient(name):
    if name in PRINT_ORIENT:
        return PRINT_ORIENT[name]
    return PRINT_ORIENT[name.rsplit('_', 1)[0]]

def polygon_excess(parts):
    """How far the pose's parts reach outside the 600 x 500 polygon (mm, 0 = inside)."""
    worst = 0.0
    who = None
    for k, (s, g, kind, col) in parts.items():
        if g == 'field':
            continue
        b = s.BoundBox
        e = max(-b.XMin, b.XMax - 600.0, -b.YMin, b.YMax - 500.0, 0.0)
        if e > worst:
            worst, who = e, k
    return round(worst, 1), who

def lowest_over_field(parts):
    """Lowest point of any non-gripper part above the operating field area (x > 350, 85 < y < 415)."""
    low = (1e9, None)
    for k, (s, g, kind, col) in parts.items():
        if g in ('field', 'wm_wrist') or kind == 'reference':
            continue
        b = s.BoundBox
        if b.XMax < 350 or b.YMax < 85 or b.YMin > 415:
            continue
        vs, _ = s.tessellate(1.0)
        z = [p.z for p in vs if p.x > 350 and 85 < p.y < 415]
        if z and min(z) < low[0]:
            low = (min(z), k)
    return (round(low[0], 1), low[1]) if low[1] else None

def poses_full():
    out = []
    for PYC in (40.0, 124.0, 208.0, 292.0, 376.0):
        for PXB in (287.0, 323.0, 359.0, 395.0, 430.0):
            for h in (5.0, 40.0):
                out.append((PYC, PXB, h, 90.0 if h == 5.0 else 0.0))
    out += [(376.0, 430.0, 22.5, 180.0), (40.0, 287.0, 22.5, -180.0), (40.0, 430.0, 5.0, 180.0), (376.0, 287.0, 40.0, -90.0)]
    return out

if __name__ == '__main__':
    import dfm
    R = {}
    park = world(field=False)
    R['static_park'] = collisions(park)
    R['cable_paths_through_parts'] = cable_contacts(park) or 'none'
    R['footprint_parked_outside_zones'] = footprint(park) or 'none'
    sweep, excess, low = {}, [], []
    poses = poses_full()
    for p in poses:
        w = world(*p, field=False)
        hits = collisions(w, only_moving=True)
        if hits:
            sweep[str(p)] = hits
        excess.append((polygon_excess(w), p))
        if p[2] == 5.0:
            lo = lowest_over_field(w)
            if lo:
                low.append((lo, p))
    # fasteners: every piece at rest, thread engagement, and against moving parts in the extreme poses
    wf = world(field=False, fasteners=True)
    R['fasteners_count'] = len(FA.all_fasteners()[0])
    R['fastener_clips_at_rest'] = fastener_check(wf) or 'none'
    eng, bad = fastener_engagement(wf)
    R['fastener_engagement_problems'] = bad or 'none'
    R['fastener_engagement'] = eng
    fsweep = {}
    fposes = [p for p in poses if p[0] in (40.0, 376.0) and p[1] in F.PXB_RANGE] + poses[-4:]
    for p in fposes:
        hits = fastener_check(world(*p, field=False, fasteners=True), only_moving=True)
        if hits:
            fsweep[str(p)] = hits
    R['fastener_sweep_poses'] = len(fposes)
    R['fastener_sweep'] = fsweep or 'none'
    # the real vendor models (vendor/*.step) in place of the simple shapes: at rest (with fasteners) and in the lift/wrist extremes
    wd = world(field=False, fasteners=True, detail=True)
    R['detailed_static_park'] = collisions(wd) or 'none'
    R['detailed_fastener_clips'] = fastener_check(wd) or 'none'
    dsweep = {}
    for p in [(40.0, 287.0, 5.0, 90.0), (40.0, 287.0, 40.0, 0.0), (376.0, 430.0, 5.0, 180.0), (376.0, 430.0, 40.0, -90.0)]:
        hits = collisions(world(*p, field=False, detail=True), only_moving=True)
        if hits:
            dsweep[str(p)] = hits
    R['detailed_sweep'] = dsweep or 'none'
    import csv
    with open(os.path.join(OUT, 'fastener_bom.csv'), 'w', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['Item', 'Qty', 'Used for'])
        for row in FA.bom():
            wr.writerow(row)
    R['sweep_poses'] = len(poses)
    R['sweep'] = sweep or 'none'
    R['worst_outside_polygon_mm'] = max(excess)
    R['lowest_over_field_h5'] = min(low)
    # chain travel: where each bend sits at the travel ends
    R['x_chain_bend_x'] = [round(C.x_chain(F.PYC0, x)[1], 1) for x in F.PXB_RANGE]
    R['y_chain_bend_y'] = [round(C.y_chain(y)[1], 1) for y in F.PYC_RANGE]
    # DFM of the frame's printed parts
    frame = F.build_frame()
    d = {}
    for k, (s, g, kind, col) in frame.items():
        if kind != 'printed':
            continue
        if k.startswith('y_beam_riser') and k != 'y_beam_riser_40':
            continue
        ax, deg = print_orient(k)
        d[k] = dfm.report(dfm.orient(s, ax, deg), s)
    R['dfm_frame'] = d
    json.dump(R, open(os.path.join(OUT, 'assembly_review.json'), 'w'), indent=1, default=str)
    print(json.dumps({k: R[k] for k in R if k not in ('dfm_frame', 'fastener_engagement')}, indent=1, default=str)[:6000])
    for k, v in d.items():
        print('%-18s size %s min_wall %s thin %d bridge %s overhang %s sharp %d' % (k, v['size'], v['min_wall'], v['thin_samples'], v['widest_bridge_mm'], v['steep_overhang_mm2'], v['n_sharp']))
