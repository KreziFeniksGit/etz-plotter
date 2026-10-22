"""
Plywood base -> DXF (mm, 1:1) for laser / CNC / hand cutting  ->  out/plywood_base.dxf, out/plywood_base_holes.csv
Origin (0, 0) = the plywood's -x/-y corner (model x 90, y 0). Viewed from the TOP.
Layers:
  CUT          outline (corner radius 10) and every through hole (cut or drill right through)
  POCKET_BOTTOM  20.4 mm foot recesses, 1 mm deep, from the UNDERSIDE (Forstner bit)   - not a through cut
  CBORE_BOTTOM   9.3 mm beam bolt counterbores, 2 mm deep, from the UNDERSIDE            - not a through cut
  CSK_TOP        6.6 mm countersinks for the foot bolts, on the TOP                       - not a through cut
  CSK_BOTTOM     countersinks for the standoff bolts, on the UNDERSIDE                    - not a through cut
Run: fcpy tools/plywood_dxf.py
"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'frame'))
sys.path.insert(0, os.path.join(HERE, '..', 'wrist'))
import frame as Fr

X0, Y0 = Fr.PLY[0], Fr.PLY[1]
OUT = os.path.join(HERE, '..', 'out')

def ents_from_section(shape, z, layer):
    out = []
    for e in shape.slice(Fr.V(0, 0, 1), z):
        for ed in e.Edges:
            c = ed.Curve
            if type(c).__name__ == 'Line' or type(c).__name__ == 'LineSegment':
                a, b = ed.Vertexes[0].Point, ed.Vertexes[-1].Point
                out.append(('LINE', layer, (a.x - X0, a.y - Y0, b.x - X0, b.y - Y0)))
            elif type(c).__name__ == 'Circle':
                cx, cy, r = c.Center.x - X0, c.Center.y - Y0, c.Radius
                if ed.isClosed():
                    out.append(('CIRCLE', layer, (cx, cy, r)))
                else:
                    a, b = ed.Vertexes[0].Point, ed.Vertexes[-1].Point
                    m = ed.valueAt((ed.FirstParameter + ed.LastParameter) / 2)
                    ang = lambda p: math.degrees(math.atan2(p.y - c.Center.y, p.x - c.Center.x)) % 360
                    sa, ea, ma = ang(a), ang(b), ang(m)
                    if not ((ma - sa) % 360 < (ea - sa) % 360):     # make it counter-clockwise through the midpoint
                        sa, ea = ea, sa
                    out.append(('ARC', layer, (cx, cy, r, sa, ea)))
            else:
                raise RuntimeError('unexpected edge %s' % type(c).__name__)
    return out

def circles(pts, d, layer):
    return [('CIRCLE', layer, (x - X0, y - Y0, d / 2)) for x, y in pts]

def dxf(ents, path):
    L = ['0', 'SECTION', '2', 'HEADER', '9', '$INSUNITS', '70', '4', '0', 'ENDSEC',
         '0', 'SECTION', '2', 'TABLES', '0', 'TABLE', '2', 'LAYER', '70', '5']
    colours = {'CUT': 7, 'POCKET_BOTTOM': 1, 'CBORE_BOTTOM': 3, 'CSK_TOP': 5, 'CSK_BOTTOM': 6}
    for n, col in colours.items():
        L += ['0', 'LAYER', '2', n, '70', '0', '62', str(col), '6', 'CONTINUOUS']
    L += ['0', 'ENDTAB', '0', 'ENDSEC', '0', 'SECTION', '2', 'ENTITIES']
    f = lambda v: '%.4f' % v
    for kind, layer, v in ents:
        L += ['0', kind, '8', layer]
        if kind == 'LINE':
            L += ['10', f(v[0]), '20', f(v[1]), '30', '0', '11', f(v[2]), '21', f(v[3]), '31', '0']
        elif kind == 'CIRCLE':
            L += ['10', f(v[0]), '20', f(v[1]), '30', '0', '40', f(v[2])]
        else:
            L += ['10', f(v[0]), '20', f(v[1]), '30', '0', '40', f(v[2]), '50', f(v[3]), '51', f(v[4])]
    L += ['0', 'ENDSEC', '0', 'EOF']
    open(path, 'w', newline='\r\n').write('\n'.join(L) + '\n')

if __name__ == '__main__':
    ply = Fr.plywood()
    zc = Fr.Z_PLY0 + Fr.Z_PLY / 2                     # mid-thickness: outline + through holes only
    ents = ents_from_section(ply, zc, 'CUT')
    eb = Fr.EB
    sto = [(eb[0] + 4, eb[1] + 4), (eb[2] - 4, eb[1] + 4), (eb[0] + 4, eb[3] - 4), (eb[2] - 4, eb[3] - 4)]
    if Fr.FOOT_POCKET > 0:
        ents += circles(Fr.FEET, Fr.FOOT_D + 0.4, 'POCKET_BOTTOM')
    if Fr.BEAM_CBORE > 0:
        ents += circles([(Fr.YB_X, y) for y in Fr.BEAM_BOLTS_Y], 8.5 + 0.8, 'CBORE_BOTTOM')
    if Fr.PLY_CSK_D > 0:
        ents += circles(Fr.FEET, Fr.PLY_CSK_D, 'CSK_TOP')
    if Fr.ELECTRONICS_ON_BASE:
        ents += circles(sto, 6.6, 'CSK_BOTTOM')
    os.makedirs(OUT, exist_ok=True)
    dxf(ents, os.path.join(OUT, 'plywood_base.dxf'))
    # hole table (for marking out by hand), from the same section
    rows = []
    for kind, layer, v in ents:
        if kind == 'CIRCLE':
            rows.append((layer, round(v[0], 2), round(v[1], 2), round(2 * v[2], 2)))
    rows.sort(key=lambda r: (r[0] != 'CUT', r[1], r[2]))
    with open(os.path.join(OUT, 'plywood_base_holes.csv'), 'w', newline='') as fh:
        fh.write('layer,x_mm,y_mm,diameter_mm\n')
        for r in rows:
            fh.write('%s,%s,%s,%s\n' % r)
    w, h = Fr.PLY[2] - Fr.PLY[0], Fr.PLY[3] - Fr.PLY[1]
    print('plywood %g x %g x %g mm; %d entities; %d through holes' % (w, h, Fr.Z_PLY, len(ents), sum(1 for r in rows if r[0] == 'CUT')))
