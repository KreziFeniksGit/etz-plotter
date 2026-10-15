"""ETZ plotter: stiffness (FEA) check of the printed parts that carry the motors, idlers and the post.
Run with FreeCAD's python:  ./fcpy tools/fea.py [case ...]   -> out/fea.json (meshes and solver files in out/fea/, git-ignored)

How it works: the part is built by frame.py, meshed with gmsh (10-node tetrahedra) and solved with CalculiX
(both ship with FreeCAD). What the part holds (a motor, an idler axle, the post) is a rigid body tied to the
faces it is bolted to; the loads act on that body where they really act (belt on the pulley, weights at
their centre of mass). The part is held where it is screwed down (all directions) and where it presses on its
support (normal direction only: it may slide sideways there, so this is on the safe side).

Loads:
  belt pretension 25 N per strand -> 50 N on a pulley or idler, along the belt (both strands pull that way);
  the motor torque only moves tension from one strand to the other, the sum stays ~2T while the belt is tight;
  weights x g, plus the 2 m/s2 design acceleration where a part rides on the Y carriage.
Material: printed PETG, E 1500 MPa (6 walls + 40 % gyroid, a bit below solid ~2000), nu 0.38.
PETG creeps under a constant load: plan on ~2x the static deflection after weeks under belt tension.
Targets: pulley/idler moves < 0.10 mm and tilts < 0.25 deg; magnet sag from the post socket < 0.2 mm;
peak von Mises < 8 MPa (layer bonds ~25 MPa; creep and fatigue -> safety 3).
"""
import json, math, os, subprocess, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [HERE, os.path.join(HERE, 'wrist'), os.path.join(HERE, 'frame')]
import FreeCAD as App
import frame as F
import wrist_module as W

OUT = os.path.join(HERE, 'out', 'fea')
if not OUT.isascii():                     # gmsh / CalculiX cannot open non-ASCII paths (e.g. 'Рабочий стол' on Windows)
    import tempfile
    OUT = os.path.join(tempfile.gettempdir(), 'etz_fea')
os.makedirs(OUT, exist_ok=True)
FCBIN = os.path.dirname(sys.executable)
EXE = '.exe' if os.name == 'nt' else ''
def _tool(name):
    p = os.path.join(FCBIN, name + EXE)
    return os.environ.get(name.upper()) or (p if os.path.exists(p) else name)
GMSH, CCX = _tool('gmsh'), _tool('ccx')

E_PETG, NU_PETG = 1500.0, 0.38
T_BELT = 25.0                      # N per strand
M_MOTOR, G, ACC = 0.28, 9.81, 2.0
MESH = 2.2                         # max element size, mm
TARGET = {'move_mm': 0.10, 'tilt_deg': 0.25, 'magnet_mm': 0.20, 'vm_MPa': 8.0}

# =============================================================================
# mesh + solve
# =============================================================================
def mesh(shape, name):
    step = os.path.join(OUT, name + '.step')
    inp = os.path.join(OUT, name + '_mesh.inp')
    shape.exportStep(step)
    subprocess.run([GMSH, step, '-3', '-order', '2', '-clmax', str(MESH), '-clmin', str(MESH / 3), '-format', 'inp',
                    '-setnumber', 'Mesh.SecondOrderLinear', '1', '-o', inp, '-v', '1'], check=True, stdout=subprocess.DEVNULL)
    nodes, elems, mode = {}, [], None
    for line in open(inp):
        if line.startswith('*'):
            u = line.upper()
            mode = 'n' if u.startswith('*NODE') else ('e' if u.startswith('*ELEMENT') and 'C3D10' in u else None)
            continue
        if mode == 'n':
            p = line.split(',')
            nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
        elif mode == 'e':
            elems.append([int(v) for v in line.strip().rstrip(',').split(',') if v.strip()])
    used = {n for e in elems for n in e[1:]}
    return {k: v for k, v in nodes.items() if k in used}, elems

def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

def solve(name, nodes, elems, fixed, normal_fixed, rigid, ref, loads):
    """fixed: node ids held in x, y, z; normal_fixed: [(ids, dof)]; rigid: node ids tied to the held body;
    ref: its reference point; loads: [(point, force)] acting on the held body."""
    force = [sum(f[i] for p, f in loads) for i in range(3)]
    moment = [0.0, 0.0, 0.0]
    for p, f in loads:
        m = cross([p[i] - ref[i] for i in range(3)], f)
        moment = [moment[i] + m[i] for i in range(3)]
    nref, nrot = max(nodes) + 1, max(nodes) + 2
    L = ['*HEADING', name, '*NODE']
    L += ['%d,%.6f,%.6f,%.6f' % (k, *v) for k, v in nodes.items()]
    L += ['%d,%.6f,%.6f,%.6f' % (nref, *ref), '%d,%.6f,%.6f,%.6f' % (nrot, *ref)]
    L.append('*ELEMENT,TYPE=C3D10,ELSET=PART')
    L += [','.join(str(v) for v in e) for e in elems]
    def nset(nm, ids):
        L.append('*NSET,NSET=%s' % nm)
        ids = sorted(ids)
        for i in range(0, len(ids), 12):
            L.append(','.join(str(v) for v in ids[i:i + 12]))
    nset('FIX', fixed)
    for i, (ids, dof) in enumerate(normal_fixed):
        nset('NF%d' % i, ids)
    nset('RIG', rigid)
    L += ['*MATERIAL,NAME=PETG', '*ELASTIC', '%g,%g' % (E_PETG, NU_PETG), '*SOLID SECTION,ELSET=PART,MATERIAL=PETG',
          '*RIGID BODY,NSET=RIG,REF NODE=%d,ROT NODE=%d' % (nref, nrot), '*STEP', '*STATIC', '*BOUNDARY', 'FIX,1,3']
    for i, (ids, dof) in enumerate(normal_fixed):
        if ids:
            L.append('NF%d,%d,%d' % (i, dof, dof))
    L.append('*CLOAD')
    for d in range(3):
        if abs(force[d]) > 1e-9:
            L.append('%d,%d,%.6f' % (nref, d + 1, force[d]))
        if abs(moment[d]) > 1e-9:
            L.append('%d,%d,%.6f' % (nrot, d + 1, moment[d]))
    L.append('*NSET,NSET=REF')
    L.append('%d,%d' % (nref, nrot))
    L += ['*NODE PRINT,NSET=REF', 'U', '*EL PRINT,ELSET=PART', 'S', '*END STEP']
    job = os.path.join(OUT, name)
    for ext in ('.dat', '.frd'):
        if os.path.exists(job + ext):
            os.remove(job + ext)
    open(job + '.inp', 'w').write('\n'.join(L) + '\n')
    r = subprocess.run([CCX, '-i', name], cwd=OUT, env=dict(os.environ, OMP_NUM_THREADS='4'),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if not os.path.exists(job + '.dat') or '*ERROR' in r.stdout:
        raise RuntimeError(r.stdout[-3000:])
    sec, u, rot, vm = None, None, None, 0.0
    for line in open(job + '.dat'):
        s = line.strip()
        if s.startswith('displacements'):
            sec = 'u'
            continue
        if s.startswith('stresses'):
            sec = 's'
            continue
        try:
            vals = [float(v) for v in s.split()]
        except ValueError:
            continue
        if sec == 'u' and len(vals) == 4:
            if int(vals[0]) == nref:
                u = vals[1:]
            elif int(vals[0]) == nrot:
                rot = vals[1:]
        elif sec == 's' and len(vals) == 8:
            sx, sy, sz, txy, txz, tyz = vals[2:]
            vm = max(vm, math.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3 * (txy ** 2 + txz ** 2 + tyz ** 2)))
    return u, rot, vm, force, moment

# =============================================================================
# load cases: build, held faces, rigid body, loads
# =============================================================================
def near(p, c, r):
    return sum((a - b) ** 2 for a, b in zip(p, c)) <= r * r

def on(v, a, tol=0.05):
    return abs(v - a) < tol

def dist_line(p, c, axis):
    """distance of p from the line through c along axis 'x' / 'y' / 'z'"""
    i = 'xyz'.index(axis)
    return math.sqrt(sum((p[k] - c[k]) ** 2 for k in range(3) if k != i))

def case_y_motor():
    py, pz = F.YM_C
    face = F.YM_FACE
    screws = F.YM_WOOD
    ref = ((F.Y_BELT_X0 + F.Y_BELT_X1) / 2, py, pz)                  # belt centre on the pulley
    return dict(
        build=F.y_motor_mount,
        fixed=lambda x, y, z: on(z, F.Z_PLY1) and any(near((x, y), s, 5.0) for s in screws),
        normal=[(lambda x, y, z: on(z, F.Z_PLY1), 3)],
        rigid=lambda x, y, z: on(x, face) and abs(y - py) <= 21.0 and abs(z - pz) <= 21.0,
        ref=ref,
        loads=[(ref, (0.0, -2 * T_BELT, 0.0)),                          # idler at -y
               ((face - 20.0, py, pz), (0.0, 0.0, -M_MOTOR * G))])

def case_x_motor():
    P0 = F.PYC0
    fy = P0 + F.XM_FACE_DY
    xc, zc = F.XM_C
    ref = (xc, P0 + (F.XB_DY0 + F.XB_DY1) / 2, zc)
    px0 = F.POST_C[0] - 10.0
    return dict(
        build=F.x_motor_mount,
        fixed=lambda x, y, z: (on(y, P0 + 10.0) and any(near((x, z), b, 5.0) for b in F.XM_POST_BOLTS)) or
                              (on(x, px0) and any(near((y, z), b, 5.0) for b in F.XM_SIDE_BOLTS)),
        normal=[(lambda x, y, z: on(y, P0 + 10.0) and px0 - 0.05 <= x <= px0 + 20.05, 2),
                (lambda x, y, z: on(x, px0) and P0 - 10.05 <= y <= P0 + 10.05, 1)],
        rigid=lambda x, y, z: on(y, fy) and abs(x - xc) <= 21.0 and abs(z - zc) <= 21.0,
        ref=ref,
        loads=[(ref, (2 * T_BELT, 0.0, 0.0)),                           # idler at +x
               ((xc, fy + 20.0, zc), (0.0, M_MOTOR * ACC, -M_MOTOR * G))])

def case_y_idler():
    py, pz = F.YI_C
    ax = (180.0, py, pz)
    ref = ((F.Y_BELT_X0 + F.Y_BELT_X1) / 2, py, pz)
    return dict(
        build=F.y_idler_bracket,
        fixed=lambda x, y, z: (on(z, F.Z_PLY1) and any(near((x, y), s, 5.0) for s in F.IDLER_WOOD)) or
                              (on(y, F.YB_Y0) and near((x, z), (F.YB_X, F.Z_YB1 - 10.0), 5.0)),
        normal=[(lambda x, y, z: on(z, F.Z_PLY1), 3), (lambda x, y, z: on(y, F.YB_Y0) and abs(x - F.YB_X) <= 10.05, 2)],
        rigid=F.y_idler_held,
        ref=ref,
        loads=[(ref, (0.0, 2 * T_BELT, 0.0))])                          # motor at +y

def case_x_idler():
    P0 = F.PYC0
    ref = (F.XI_C[0], P0 + (F.XB_DY0 + F.XB_DY1) / 2, F.X_BELT_Z)
    return dict(
        build=F.x_idler_bracket,
        fixed=lambda x, y, z: on(x, F.BOOM_X1) and near((y, z), (P0, F.X_BELT_Z), 5.0),
        normal=[(lambda x, y, z: on(x, F.BOOM_X1) and abs(y - P0) <= 10.05 and abs(z - F.X_BELT_Z) <= 10.05, 1)],
        rigid=F.x_idler_held,
        ref=ref,
        loads=[(ref, (-2 * T_BELT, 0.0, 0.0))])                         # motor at -x

_CARRIED = None
def carried():
    """mass and centre of mass of everything the post carries (worst reach: X at its far end, magnet low)"""
    global _CARRIED
    if _CARRIED is None:
        import stability as S
        ms = S.masses(F.PYC0, F.PXB_RANGE[1], W.H_MIN, 0.0)
        skip = ('y_carriage', 'y_block', 'y_belt', 'zip_tie_ycar', 'f_yblock', 'f_yclamp', 'f_ychain', 'f_socket', 'cable_chain_y')
        sel = [m for m in ms if (m[1] == 'ycar' or m[1].startswith('wm_') or m[1] == 'chainX') and not m[0].startswith(skip)]
        mt = sum(m[2] for m in sel)
        _CARRIED = (mt, [sum(m[2] * m[3][i] for m in sel) / mt for i in range(3)])
    return _CARRIED

def case_y_carriage():
    pc = F.POST_C
    inner = 10.0 + W.SOCKET_GAP
    m, c = carried()
    blk = (F.YB_X - 13.5, F.YB_X + 13.5, F.PYC0 - 22.7, F.PYC0 + 22.7)
    holes = [(F.YB_X + a * 10.0, F.PYC0 + b * 10.0) for a in (-1, 1) for b in (-1, 1)]
    def in_socket(x, y, z):
        return z >= F.Z_YC1 - 0.05 and abs(x - pc[0]) <= inner + 0.05 and abs(y - pc[1]) <= inner + 0.05
    mag = (F.PXB_RANGE[1] + W.MAG_X, F.PYC0 + W.MAG_Y, W.H_MIN)
    return dict(
        build=F.y_carriage,
        fixed=lambda x, y, z: on(z, F.Z_YC0) and any(near((x, y), h, 4.5) for h in holes),
        normal=[(lambda x, y, z: on(z, F.Z_YC0) and blk[0] <= x <= blk[1] and blk[2] <= y <= blk[3], 3)],
        rigid=in_socket,
        ref=(pc[0], pc[1], F.Z_YC1),
        loads=[(tuple(c), (0.0, m * ACC, -m * G)), (tuple(c), (m * ACC, 0.0, 0.0))],
        report={'magnet': mag}, mass=m)

CASES = {'y_motor_mount': case_y_motor, 'x_motor_mount': case_x_motor, 'y_idler_bracket': case_y_idler,
         'x_idler_bracket': case_x_idler, 'y_carriage': case_y_carriage}

def run(name):
    c = CASES[name]()
    shape = c['build']()
    nodes, elems = mesh(shape, name)
    fixed = [k for k, p in nodes.items() if c['fixed'](*p)]
    fs = set(fixed)
    nfix = [([k for k, p in nodes.items() if k not in fs and pred(*p)], dof) for pred, dof in c['normal']]
    rigid = [k for k, p in nodes.items() if k not in fs and c['rigid'](*p)]
    if len(fixed) < 3 or len(rigid) < 3:
        raise RuntimeError('%s: too few held (%d) or rigid-body (%d) nodes' % (name, len(fixed), len(rigid)))
    u, rot, vm, force, moment = solve(name, nodes, elems, fixed, nfix, rigid, c['ref'], c['loads'])
    du = math.sqrt(sum(v * v for v in u))
    tilt = math.degrees(math.sqrt(sum(v * v for v in rot)))
    res = {'nodes': len(nodes), 'elements': len(elems), 'held_nodes': len(fixed), 'body_nodes': len(rigid),
           'force_N': [round(v, 2) for v in force], 'moment_Nmm': [round(v, 1) for v in moment],
           'move_mm': round(du, 4), 'disp_mm': [round(v, 4) for v in u], 'tilt_deg': round(tilt, 3),
           'max_von_mises_MPa': round(vm, 2), 'move_after_creep_x2_mm': round(2 * du, 3)}
    ok = vm < TARGET['vm_MPa']
    for k, p in c.get('report', {}).items():
        r = [p[i] - c['ref'][i] for i in range(3)]
        w = cross(rot, r)
        d = [u[i] + w[i] for i in range(3)]
        res[k + '_disp_mm'] = [round(v, 4) for v in d]
        res[k + '_move_mm'] = round(math.sqrt(sum(v * v for v in d)), 4)
        ok = ok and res[k + '_move_mm'] < TARGET['magnet_mm']
    if 'report' not in c:
        ok = ok and du < TARGET['move_mm'] and tilt < TARGET['tilt_deg']
    if 'mass' in c:
        res['carried_kg'] = round(c['mass'], 3)
    res['ok'] = ok
    print(name, json.dumps(res))
    return res

if __name__ == '__main__':
    names = sys.argv[1:] or list(CASES)
    path = os.path.join(HERE, 'out', 'fea.json')
    R = json.load(open(path)) if os.path.exists(path) else {}
    R['_settings'] = {'E_MPa': E_PETG, 'nu': NU_PETG, 'belt_N_per_strand': T_BELT, 'mesh_mm': MESH, 'targets': TARGET}
    for n in names:
        R[n] = run(n)
    json.dump(R, open(path, 'w'), indent=1)
    print('all ok' if all(v.get('ok') for k, v in R.items() if not k.startswith('_')) else 'NOT all ok')
