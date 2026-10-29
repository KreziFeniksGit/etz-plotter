"""
Tasks: what to do with the checkers, given what the camera found and the parameters typed in before the start.

A task turns a Scene (detected stacks, official field mm) + parameters into a route_planner.Task (start stacks and
goals: checker -> cell, level, wrist angle). The planner then finds the fastest legal order of moves.

The task NUMBERS below are ours: the final's 10 tasks are only in the full ETZ (not received yet). When it arrives,
each official task becomes one entry in TASKS (most will be one of the shapes here with other parameters).
Implemented:
  1  move       move the checker in cell `from` to cell `to`                            (ETZ 4.2 task 1)
  2  far        move the checker in `cell` as far as possible along one axis (X / Y / best) (ETZ 4.2 task 2)
  3  line3      three checkers: move one so all three lie on a line (row, column, diagonal) (ETZ 4.2 task 3)
  4  colours    each colour to a cell, e.g. red=А0 blue=Б2 (several of one colour: stacked)
  5  tags       each sticker (QR text / marker id) to a cell, e.g. T1=Б3 7=А0
  6  stack      build a stack in `cell` from colours bottom -> top, e.g. cell=В4 order=red,green,blue
  7  rotate     turn the checker in `cell` by `angle` degrees and put it back
Limits: the camera sees only the top checker of each stack; tasks about hidden checkers need a re-scan after the
stack is opened (not done yet). Run:  python tasks.py --test
"""
import math, sys
import field as F
import route_planner as R

SNAP = 4.0          # a detection this close to a cell centre is taken as "in that cell"

class TaskError(Exception):
    pass

class Scene:
    """detected stacks in field mm: [{'X', 'Y', 'levels', 'colour', 'tag', 'angle'}] (colour / tag / angle of the top)"""
    def __init__(self, stacks):
        self.stacks = stacks

    @classmethod
    def from_scan(cls, tops, transform):
        """twin / camera scan (machine mm) -> Scene in field mm"""
        out = []
        for mx, my, colour, tag, levels, angle in tops:
            X, Y = transform.to_field(mx, my)
            out.append(dict(X=X, Y=Y, levels=levels, colour=colour, tag=tag, angle=angle))
        return cls(out)

    def planner_start(self):
        """route_planner start stacks: {place: [ids]}, colours, tags; hidden (lower) checkers get colour '?'"""
        start, colour, tag, info = {}, {}, {}, {}
        nid = 0
        for s in self.stacks:
            cell = F.cell_of(s['X'], s['Y'])
            place = cell if cell and math.dist(F.cell_centre(*cell), (s['X'], s['Y'])) <= SNAP else ('p', round(s['X'], 1), round(s['Y'], 1))
            ids = []
            for lvl in range(s['levels']):
                top = lvl == s['levels'] - 1
                colour[nid] = s['colour'] if top else '?'
                tag[nid] = s['tag'] if top else ''
                info[nid] = dict(s, level=lvl, place=place)
                ids.append(nid); nid += 1
            start[place] = ids
        return start, colour, tag, info

def _top_at(info, start, cell):
    """id of the top checker of the stack in / nearest to a cell (within 14 mm), or TaskError"""
    cx, cy = F.cell_centre(*cell)
    best = None
    for place, ids in start.items():
        d = math.dist(R.xy(place), (cx, cy))
        if ids and d <= 14.0 and (best is None or d < best[0]):
            best = (d, ids[-1])
    if best is None:
        raise TaskError('no checker found in %s' % F.cell_name(cell))
    return best[1]

def _height(start, cell):
    return len(start.get(cell, []))

def _free(start, cell, ignore=None):
    cx, cy = F.cell_centre(*cell)
    for place, ids in start.items():
        if ids and place != ignore and math.dist(R.xy(place), (cx, cy)) < 20.0:
            return False
    return True

def _pairs(text):
    """'red=А0 blue=Б2' -> [('red', 'А0'), ('blue', 'Б2')]"""
    out = []
    for part in text.replace(',', ' ').split():
        if '=' not in part:
            raise TaskError('expected name=cell, got %r' % part)
        k, v = part.split('=', 1)
        out.append((k.strip().lower(), v.strip()))
    return out

# ---------------------------------------------------------------- the tasks
def t_move(scene, p):
    start, colour, tag, info = scene.planner_start()
    src, dst = F.parse_cell(p['from']), F.parse_cell(p['to'])
    c = _top_at(info, start, src)
    return R.Task(start, {c: (dst, _height(start, dst))}, colour, tag=tag)

def t_far(scene, p):
    start, colour, tag, info = scene.planner_start()
    src = F.parse_cell(p['cell'])
    c = _top_at(info, start, src)
    axis = p.get('axis', 'best').upper()
    n0, k0 = src
    options = []
    if axis in ('X', 'BEST'):
        options += [(n, k0) for n in range(F.COLS)]
    if axis in ('Y', 'BEST'):
        options += [(n0, k) for k in range(1, F.ROWS + 1)]
    here = info[c]['place']
    options = [q for q in options if q != src and _free(start, q, ignore=here)]
    if not options:
        raise TaskError('no free cell along that axis')
    far = max(math.dist(F.cell_centre(*q), F.cell_centre(*src)) for q in options)
    best = [q for q in options if abs(math.dist(F.cell_centre(*q), F.cell_centre(*src)) - far) < 1e-6]
    tool = R.park_field()
    q = min(best, key=lambda q: R.move_time(tool, R.xy(here), F.cell_centre(*q), 1, 0))
    return R.Task(start, {c: (q, 0)}, colour, tag=tag)

def _collinear_cells(a, b):
    """cells on the grid line (row, column or diagonal) through cells a and b, or [] if they are not on one"""
    (na, ka), (nb, kb) = a, b
    dn, dk = nb - na, kb - ka
    if dn == 0 and dk == 0:
        return []
    if not (dn == 0 or dk == 0 or abs(dn) == abs(dk)):
        return []
    sn, sk = (dn > 0) - (dn < 0), (dk > 0) - (dk < 0)
    out = []
    for t in range(-12, 13):
        n, k = na + sn * t, ka + sk * t
        if 0 <= n < F.COLS and 1 <= k <= F.ROWS:
            out.append((n, k))
    return out

def t_line3(scene, p):
    start, colour, tag, info = scene.planner_start()
    tops = [ids[-1] for ids in start.values() if ids]
    if len(tops) != 3:
        raise TaskError('line3 needs exactly 3 checkers on the field, found %d' % len(tops))
    cell = {c: F.cell_of(*R.xy(info[c]['place'])) for c in tops}
    tool = R.park_field()
    best = None
    for mover in tops:
        a, b = [cell[c] for c in tops if c != mover]
        for q in _collinear_cells(a, b):
            if q in (a, b) or not _free(start, q, ignore=info[mover]['place']):
                continue
            if q == cell[mover] and math.dist(F.cell_centre(*q), R.xy(info[mover]['place'])) < 1.0:
                return R.Task(start, {}, colour, tag=tag)                  # already on a line
            t = R.move_time(tool, R.xy(info[mover]['place']), F.cell_centre(*q), 1, 0)
            if best is None or t < best[0]:
                best = (t, mover, q)
    if best is None:
        raise TaskError('no single move puts the three checkers on one line')
    return R.Task(start, {best[1]: (best[2], 0)}, colour, tag=tag)

def t_colours(scene, p):
    start, colour, tag, info = scene.planner_start()
    goal, height = {}, {}
    for name, cellname in _pairs(p['map']):
        cell = F.parse_cell(cellname)
        mine = sorted((c for c in colour if colour[c] == name), key=lambda c: (info[c]['Y'], info[c]['X']))
        for c in mine:
            h = height.get(cell, _height(start, cell) if cell not in [g[0] for g in goal.values()] else 0)
            goal[c] = (cell, h); height[cell] = h + 1
    if not goal:
        raise TaskError('no checker of those colours found')
    return R.Task(start, goal, colour, tag=tag)

def t_tags(scene, p):
    start, colour, tag, info = scene.planner_start()
    goal = {}
    for name, cellname in _pairs(p['map']):
        cell = F.parse_cell(cellname)
        mine = [c for c in tag if tag[c].lower() == name]
        if not mine:
            raise TaskError('sticker %r not found' % name)
        goal[mine[0]] = (cell, _height(start, cell))
    return R.Task(start, goal, colour, tag=tag)

def t_stack(scene, p):
    start, colour, tag, info = scene.planner_start()
    cell = F.parse_cell(p['cell'])
    goal, used = {}, set()
    base = _height(start, cell)
    for lvl, name in enumerate(x.strip().lower() for x in p['order'].split(',')):
        mine = [c for c in colour if colour[c] == name and c not in used]
        if not mine:
            raise TaskError('no %s checker left for level %d' % (name, lvl))
        c = min(mine, key=lambda c: math.dist(R.xy(info[c]['place']), F.cell_centre(*cell)))
        used.add(c); goal[c] = (cell, base + lvl)
    return R.Task(start, goal, colour, tag=tag)

def t_rotate(scene, p):
    start, colour, tag, info = scene.planner_start()
    cell = F.parse_cell(p['cell'])
    c = _top_at(info, start, cell)
    angle = float(p.get('angle', 90))
    # put it down in the same cell: the planner needs a different place, so go via a turn in place
    return R.Task(start, {c: (cell, info[c]['level'])}, colour, angle={c: angle}, tag=tag)

class TaskDef:
    def __init__(self, key, title, params, build):
        self.key, self.title, self.params, self.build = key, title, params, build

TASKS = {
    1: TaskDef('move', 'Move one checker (ETZ 4.2 #1)', [('from', 'Д1'), ('to', 'Д5')], t_move),
    2: TaskDef('far', 'As far as possible along one axis (ETZ 4.2 #2)', [('cell', 'В4'), ('axis', 'best')], t_far),
    3: TaskDef('line3', 'Three checkers on one line (ETZ 4.2 #3)', [], t_line3),
    4: TaskDef('colours', 'Colours to cells', [('map', 'red=А0 blue=Б2')], t_colours),
    5: TaskDef('tags', 'Stickers to cells', [('map', 'T1=Б3')], t_tags),
    6: TaskDef('stack', 'Build a stack of colours', [('cell', 'В4'), ('order', 'red,green,blue')], t_stack),
    7: TaskDef('rotate', 'Rotate a checker in place', [('cell', 'Б3'), ('angle', '90')], t_rotate),
}

def build(number, scene, params):
    td = TASKS[number]
    p = {k: params.get(k, d) for k, d in td.params}
    return td.build(scene, p)

# ---------------------------------------------------------------- test
def _scene(cells):
    """cells: [(name, colour, tag, levels)] -> Scene with checkers exactly at the cell centres"""
    out = []
    for name, colour, tag, levels in cells:
        X, Y = F.cell_centre(*F.parse_cell(name))
        out.append(dict(X=X, Y=Y, levels=levels, colour=colour, tag=tag, angle=0.0))
    return Scene(out)

def self_test():
    ok = True
    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print('  %-60s %s' % (name, 'ok' if cond else 'FAILED'))
    t = build(1, _scene([('Д1', 'red', '', 1)]), {'from': 'Д1', 'to': 'Д5'})
    check('move Д1 -> Д5: one goal, Д5 level 0', list(t.goal.values()) == [((5, 5), 0)])
    t = build(2, _scene([('В4', 'red', '', 1)]), {'cell': 'В4', 'axis': 'X'})
    check('far along X from В4 -> В0 or В8 (4 cells away)', list(t.goal.values())[0][0] in ((0, 3), (8, 3)))
    t = build(2, _scene([('В4', 'red', '', 1), ('В0', 'blue', '', 1)]), {'cell': 'В4', 'axis': 'X'})
    check('far along X with В0 taken -> В8', list(t.goal.values())[0][0] == (8, 3))
    t = build(3, _scene([('А0', 'red', '', 1), ('А4', 'blue', '', 1), ('Г7', 'green', '', 1)]), {})
    (c, (q, lvl)), = t.goal.items()
    check('line3: one move, result on a common line', q is not None)
    sc = _scene([('А0', 'red', '', 1), ('Б2', 'red', '', 1), ('В5', 'blue', '', 1)])
    t = build(4, sc, {'map': 'red=Д0 blue=Д8'})
    check('colours: two reds stacked in Д0 (levels 0, 1), blue in Д8', sorted(t.goal.values()) == [((0, 5), 0), ((0, 5), 1), ((8, 5), 0)])
    t = build(5, _scene([('Г3', 'yellow', 'T1', 1)]), {'map': 'T1=Б3'})
    check('tags: T1 -> Б3', list(t.goal.values()) == [((3, 2), 0)])
    t = build(6, _scene([('А0', 'blue', '', 1), ('А1', 'red', '', 1), ('А2', 'green', '', 1)]), {'cell': 'В4', 'order': 'red,green,blue'})
    order = [t.colour[c] for c, _ in sorted(t.goal.items(), key=lambda kv: kv[1][1])]
    check('stack: red, green, blue bottom -> top in В4', order == ['red', 'green', 'blue'])
    try:
        build(1, _scene([('Д1', 'red', '', 1)]), {'from': 'Г1', 'to': 'Д5'}); err = False
    except TaskError:
        err = True
    check('move from an empty cell -> clear error', err)
    # every task plans
    for name, sc, num, prm in (('move', _scene([('Д1', 'red', '', 1)]), 1, {}),
                              ('rotate in place', _scene([('Б3', 'red', '', 1)]), 7, {'cell': 'Б3', 'angle': '90'}),
                              ('colours', sc, 4, {'map': 'red=Д0 blue=Д8'}),
                              ('stack', _scene([('А0', 'blue', '', 1), ('А1', 'red', '', 2), ('А2', 'green', '', 1)]), 6, {})):
        task = build(num, sc, prm)
        pl = R.plan(task, tries=40)
        check('%s: planner finds a legal plan (%.1f s, %d moves)' % (name, pl.total, len(pl.steps)) if pl else name,
              pl is not None and R.check(task, pl))
    print('tasks self-test:', 'PASS' if ok else 'FAIL')
    return ok

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--test' in sys.argv:
        sys.exit(0 if self_test() else 1)
    for n, td in TASKS.items():
        print('%2d  %-8s %s  params: %s' % (n, td.key, td.title, ', '.join('%s=%s' % kv for kv in td.params)))
