"""
Route planner: in which order to move the checkers so the whole task takes the least time.

The task: checkers stand in stacks (up to 5) - at any detected spot on the field or in cells. Each checker that has a
goal must end in a cell (or a buffer place) at a given level of the stack there, turned to a given wrist angle. The
magnet can only take the TOP checker of a stack and only put it on TOP of a stack. So the order matters twice:
  - legality: a checker can go to its goal only when the stack there already holds exactly the checkers that belong
    under it; a checker that blocks one below it has to move first (to its goal, or aside to a free place);
  - time: travel between moves, lifting to the stack heights, the wrist turning while carrying.
Method (our own): many randomised greedy plans (each step: pick among the cheapest legal moves, with a bit of
randomness), keep the fastest, then a local search moves single steps elsewhere in the order while it saves time.
Times come from machine.py (the same speed profile as the firmware, lift angle, magnet delays).
Coordinates: official field frame (field.py). Places: cells (n, k), buffer places (9, k), start spots ('p', X, Y).

Run:  python route_planner.py           window with a random task (New task, Plan, Animate)
      python route_planner.py --test    200 random tasks: plans legal, goal reached, gain vs the naive order
"""
import math, random, sys, time
import field as F
import machine as M

MAX_STACK = 5
ASIDE_PENALTY = 0.5        # s: prefer moves that finish a checker over moves that only clear the way
CAL = M.load_cal()
_NOMINAL = M.FieldTransform()

def set_cal(cal):
    global CAL
    CAL = cal

def park_field():
    """the parked magnet position in field mm (nominal sheet)"""
    return _NOMINAL.to_field(*M.carriage_to_magnet(*M.PARK))

def xy(p):
    if p == 'park':
        return park_field()
    if p[0] == 'p':
        return p[1], p[2]
    return F.cell_centre(*p)

def pname(p, latin=True):
    if p == 'park':
        return 'park'
    if p[0] == 'p':
        return '(%.0f,%.0f)' % (p[1], p[2])
    return F.cell_name(p, latin=latin)

def travel(a, b):
    """seconds for the straight `linemm` move between two field points (field X = machine y, field Y = machine x)"""
    return M.line_time(b[1] - a[1], b[0] - a[0], CAL)

def move_time(tool, src, dst, src_levels, dst_levels, turn_deg=0.0):
    """one pick-and-place: travel to src at carry height, down to the stack top, grab, up, travel to dst while the
    wrist turns, down to the stack top there, release, up. Returns seconds."""
    hc = CAL['h_carry']
    t = travel(tool, src)
    hs = M.stack_top(src_levels)
    t += 2 * M.lift_time(hc, hs, CAL) + CAL['mag_grab']
    rot = M.wrist_time(0.0, turn_deg, CAL) if turn_deg else 0.0
    t += max(travel(src, dst), rot)
    hd = M.stack_top(dst_levels) + CAL['h_clear']
    t += 2 * M.lift_time(hc, hd, CAL) + CAL['mag_release']
    return t

class Task:
    """start: {place: [checker ids bottom..top]}; goal: {checker: (cell, level)}; angle: {checker: deg};
    colour: {checker: name}; tag: {checker: text}; buffer_ok: may the buffer be used for moves aside"""
    def __init__(self, start, goal, colour, angle=None, tag=None, buffer_ok=True):
        self.start, self.goal, self.colour = start, goal, colour
        self.angle, self.tag, self.buffer_ok = angle or {}, tag or {}, buffer_ok

    def goal_stacks(self):
        g = {}
        for c, (p, lvl) in self.goal.items():
            g.setdefault(p, {})[lvl] = c
        return {p: [d[i] for i in sorted(d)] for p, d in g.items()}

def random_task(n=12, seed=None, max_start_stack=3, off_cell=0.4):
    """a legal random task: n checkers in random stacks (a share of them at off-centre spots), goals = random cell
    stacks up to 5 high (levels 0..), random wrist angles"""
    rnd = random.Random(seed)
    cells = F.field_cells()
    start, goal, colour, angle = {}, {}, {}, {}
    ids = list(range(n))
    for c in ids:
        colour[c] = rnd.choice(F.COLOURS)
        angle[c] = rnd.choice((0, 0, 90, 180, 270, rnd.randrange(360)))
    used, i = set(), 0
    while i < n:
        cell = rnd.choice(cells)
        if cell in used:
            continue
        used.add(cell)
        x, y = F.cell_centre(*cell)
        place = cell
        if rnd.random() < off_cell:                    # detected somewhere in the cell, not at its centre
            place = ('p', round(x + rnd.uniform(-7, 7), 1), round(y + rnd.uniform(-7, 7), 1))
        k = min(n - i, rnd.randint(1, max_start_stack))
        start[place] = ids[i:i + k]; i += k
    order = ids[:]; rnd.shuffle(order); i = 0
    used = set()
    while i < n:
        cell = rnd.choice(cells)
        if cell in used:
            continue
        used.add(cell)
        k = min(n - i, rnd.randint(1, MAX_STACK))
        for lvl, c in enumerate(order[i:i + k]):
            goal[c] = (cell, lvl)
        i += k
    return Task(start, goal, colour, angle)

# ---------------------------------------------------------------- planner
class Plan:
    def __init__(self, steps, total):
        self.steps, self.total = steps, total     # steps: [(checker, from, to, seconds, kind)] kind 'goal' / 'aside'

def _done_height(stack, goal_stack):
    """how many checkers at the bottom of this stack are already final"""
    k = 0
    while k < len(stack) and k < len(goal_stack) and stack[k] == goal_stack[k]:
        k += 1
    return k

def _free_places(task, stacks, goal_places):
    """where a checker may be put aside: buffer first (if allowed), then empty cells nobody needs"""
    out = [q for q in F.buffer_cells() if task.buffer_ok and not stacks.get(q)]
    occupied = [xy(p) for p, s in stacks.items() if s]
    for q in F.field_cells():
        if q in goal_places or stacks.get(q):
            continue
        if any(math.dist(F.cell_centre(*q), o) < 26.0 for o in occupied):   # an off-centre checker overlaps it
            continue
        out.append(q)
    return out

def plan(task, tries=300, greed=0.25, seed=0, order=None, polish=True, tool=None):
    """best of `tries` randomised greedy plans, then polished. order = a fixed checker order (naive plan).
    tool = where the magnet is now (field mm); default the park position."""
    rnd = random.Random(seed)
    gst = task.goal_stacks()
    tool = tool or park_field()
    best = None
    for t in range(1 if order else tries):
        r = _one_plan(task, gst, rnd, 0.0 if (t == 0 or order) else greed, order, tool)
        if r and (best is None or r.total < best.total):
            best = r
    if not order:                                    # the simple checker-by-checker order is a candidate too
        nv = _one_plan(task, gst, rnd, 0.0, sorted(task.goal, key=lambda c: (task.goal[c][1], c)), tool)
        if nv and (best is None or nv.total < best.total):
            best = nv
    if best and polish and not order:
        best = _polish(task, best, tool)
    return best

def _replay(task, steps, tool):
    """total time of a step list, or (None, None) if a move is illegal / the goal is not reached"""
    stacks = {p: list(s) for p, s in task.start.items()}
    total, out = 0.0, []
    for c, p, q, dt, kind in steps:
        s = stacks.get(p)
        if not s or s[-1] != c or len(stacks.get(q, [])) >= MAX_STACK:
            return None, None
        turn = task.angle.get(c, 0) if kind == 'goal' else 0.0
        dt = move_time(tool, xy(p), xy(q), len(s), len(stacks.get(q, [])), turn)
        s.pop(); stacks.setdefault(q, []).append(c)
        out.append((c, p, q, dt, kind)); total += dt
        tool = xy(q)
    for c, (gp, lvl) in task.goal.items():
        g = stacks.get(gp, [])
        if len(g) <= lvl or g[lvl] != c:
            return None, None
    return total + travel(tool, park_field()), out

def _polish(task, pl, tool):
    """local search: take one step out and put it back elsewhere; keep it when legal and faster"""
    best_t, steps = _replay(task, pl.steps, tool)
    if best_t is None:
        return pl
    improved = True
    while improved:
        improved = False
        n = len(steps)
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                s = steps[:i] + steps[i + 1:]
                s.insert(j, steps[i])
                t, out = _replay(task, s, tool)
                if t is not None and t < best_t - 1e-6:
                    best_t, steps, improved = t, out, True
                    break
            if improved:
                break
    return Plan(steps, best_t)

def _one_plan(task, gst, rnd, greed, order, tool):
    stacks = {p: list(s) for p, s in task.start.items()}
    where = {c: p for p, s in stacks.items() for c in s}
    steps, total = [], 0.0
    goal_places = set(gst)
    for _ in range(10 * len(task.goal) + 20):
        def final_ok(p):            # stack at p: bottom part that is final
            return _done_height(stacks.get(p, []), gst.get(p, []))
        if all(final_ok(p) == len(gst[p]) and len(stacks.get(p, [])) == len(gst[p]) for p in gst):
            break
        cands = []
        # 1) moves straight to the goal: checker on top of its stack, goal stack ready for it
        for c, (gp, lvl) in task.goal.items():
            p = where[c]
            if stacks[p][-1] != c:
                continue
            if p == gp and final_ok(p) > stacks[p].index(c):
                continue            # already final
            gs = stacks.get(gp, [])
            if len(gs) == lvl and final_ok(gp) == lvl and p != gp:
                cands.append((c, p, gp, 'goal'))
        if order:                   # naive: only the next checker of the fixed order, else unblock
            nxt = next((c for c in order if not (where[c] == task.goal[c][0] and
                        final_ok(where[c]) > stacks[where[c]].index(c))), None)
            cands = [x for x in cands if x[0] == nxt]
        if not cands:
            # 2) unblock: move a top checker that is in the way to a free place
            blocked = []
            for p, s in stacks.items():
                if not s:
                    continue
                fh = final_ok(p)
                # the top blocks something if it sits on a goal place that is not right yet,
                # or if another non-final checker is under it, or if it covers a goal cell (off-centre spot)
                covers_goal = p[0] == 'p' and any(math.dist(xy(p), F.cell_centre(*g)) < 26.0 for g in goal_places
                                                  if len(stacks.get(g, [])) < len(gst[g]))
                if (p in goal_places and len(s) > fh) or len(s) - fh >= 2 or (covers_goal and s[-1] not in task.goal):
                    blocked.append(p)
            if not blocked:
                return None
            free = _free_places(task, stacks, goal_places)
            if not free:
                return None
            for p in blocked:
                c = stacks[p][-1]
                tgt = xy(task.goal[c][0]) if c in task.goal else xy(p)
                q = min(free, key=lambda q: math.dist(xy(p), xy(q)) + math.dist(xy(q), tgt))
                cands.append((c, p, q, 'aside'))
        def cost(x):
            c, p, q, kind = x
            turn = task.angle.get(c, 0) if kind == 'goal' else 0.0
            return move_time(tool, xy(p), xy(q), len(stacks[p]), len(stacks.get(q, [])), turn) + \
                (ASIDE_PENALTY if kind == 'aside' else 0.0)
        cands.sort(key=cost)
        k = 0
        if greed and len(cands) > 1 and rnd.random() < greed:
            k = rnd.randrange(min(3, len(cands)))
        c, p, q, kind = cands[k]
        dt = cost(cands[k]) - (ASIDE_PENALTY if kind == 'aside' else 0.0)
        stacks[p].pop()
        stacks.setdefault(q, []).append(c)
        where[c] = q
        steps.append((c, p, q, dt, kind))
        total += dt
        tool = xy(q)
    else:
        return None
    total += travel(tool, park_field())
    return Plan(steps, total)

def check(task, pl):
    """replay a plan: every move legal (top only, stack <= 5, not into the service area) and the end state = the goal"""
    stacks = {p: list(s) for p, s in task.start.items()}
    for c, p, q, dt, kind in pl.steps:
        assert stacks.get(p) and stacks[p][-1] == c, 'took a checker that is not on top'
        assert q[0] != 'p' and not F.in_service_area(*xy(q), r=0.0), 'put down outside a cell'
        stacks[p].pop()
        stacks.setdefault(q, []).append(c)
        assert len(stacks[q]) <= MAX_STACK, 'stack above 5'
    for c, (gp, lvl) in task.goal.items():
        assert stacks[gp][lvl] == c, 'goal not reached'
    return True

def naive(task):
    return plan(task, order=sorted(task.goal, key=lambda c: (task.goal[c][1], c)))

# ---------------------------------------------------------------- window
def draw_field(cv, P, task=None, stacks=None, plan_=None, tool=None):
    """draw the field (official orientation: X right, Y up), checkers and a plan on a tkinter canvas"""
    cv.delete('all')
    for cell in F.all_cells():
        x, y = F.cell_centre(*cell)
        dash = (3, 2) if F.is_buffer(cell) else None
        cv.create_rectangle(*P(x - 14, y + 14), *P(x + 14, y - 14), outline='#88a' if dash else '#bbb', dash=dash)
        cv.create_text(*P(x, y - 11), text=F.cell_name(cell, latin=True) if not F.is_buffer(cell) else 'buf',
                       fill='#aaa', font=('Segoe UI', 7))
    for mid, (mx, my) in F.MARKS.items():
        cv.create_rectangle(*P(mx - 9, my + 9), *P(mx + 9, my - 9), fill='black')
        cv.create_text(*P(mx, my - 13), text=str(mid), font=('Segoe UI', 7))
    px, py = park_field()
    cv.create_oval(*P(px - 4, py + 4), *P(px + 4, py - 4), outline='black')
    cv.create_text(*P(px, py - 9), text='park', font=('Segoe UI', 7))
    if task is None:
        return
    for p, gl in task.goal_stacks().items():       # goal: small coloured ring per level
        x, y = xy(p)
        for i, c in enumerate(gl):
            cv.create_oval(*P(x - 12 + 4 * i, y + 12), *P(x - 8 + 4 * i, y + 8), outline=task.colour[c], width=2)
    for p, s in (stacks or task.start).items():
        if not s:
            continue
        x, y = xy(p)
        c = s[-1]
        cv.create_oval(*P(x - 13, y + 13), *P(x + 13, y - 13), fill=task.colour.get(c, 'grey'), outline='black')
        cv.create_text(*P(x, y), text=str(len(s)) if len(s) > 1 else '', font=('Segoe UI', 9, 'bold'))
    if plan_:
        prev = park_field()
        for i, (c, p, q, dt, kind) in enumerate(plan_.steps):
            a, b = xy(p), xy(q)
            cv.create_line(*P(*prev), *P(*a), fill='#ccc', dash=(2, 3))
            cv.create_line(*P(*a), *P(*b), arrow='last', fill='#d33' if kind == 'aside' else '#235', width=1.5)
            cv.create_text(*P((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), text=str(i + 1), fill='#235', font=('Segoe UI', 8, 'bold'))
            prev = b
    if tool:
        cv.create_line(*P(tool[0] - 6, tool[1]), *P(tool[0] + 6, tool[1]), width=2)
        cv.create_line(*P(tool[0], tool[1] - 6), *P(tool[0], tool[1] + 6), width=2)

def canvas_mapping(scale=2.6):
    X0, Y1 = -40.0, 205.0                            # field mm at the top-left
    P = lambda x, y: ((x - X0) * scale, (Y1 - y) * scale)
    return P, int(320 * scale), int(290 * scale)

def window(link=None, master=None):
    import tkinter as tk
    from tkinter import ttk
    P, W, H = canvas_mapping()
    w = tk.Toplevel(master) if master else tk.Tk()
    w.title('ETZ route planner')
    top = ttk.Frame(w, padding=4); top.pack(fill='x')
    cv = tk.Canvas(w, width=W, height=H, bg='white'); cv.pack(side='left', padx=4, pady=4)
    side = ttk.Frame(w, padding=4); side.pack(side='left', fill='both', expand=True)
    info = tk.Text(side, width=46, height=34, font=('Consolas', 9)); info.pack(fill='both', expand=True)
    st = {'task': None, 'plan': None, 'naive': None}
    nvar = tk.IntVar(value=12)

    def show_plan():
        t, pl, nv = st['task'], st['plan'], st['naive']
        info.delete('1.0', 'end')
        if not pl:
            info.insert('end', 'no plan'); return
        info.insert('end', 'best plan: %.1f s, %d moves\n' % (pl.total, len(pl.steps)))
        if nv:
            info.insert('end', 'naive order (checker by checker): %.1f s\n -> %.0f%% faster\n\n' % (
                nv.total, 100 * (1 - pl.total / nv.total)))
        for i, (c, p, q, dt, kind) in enumerate(pl.steps):
            info.insert('end', '%2d. %-7s %-9s -> %-6s %4.1f s%s\n' % (i + 1, t.colour[c], pname(p), pname(q), dt,
                                                                    '  (aside)' if kind == 'aside' else ''))

    def new_task():
        st['task'] = random_task(nvar.get(), seed=random.randrange(10 ** 6))
        st['plan'] = st['naive'] = None
        draw_field(cv, P, st['task']); info.delete('1.0', 'end'); info.insert('end', 'press Plan')

    def do_plan():
        t = st['task']
        t0 = time.time()
        st['plan'] = plan(t)
        st['naive'] = naive(t)
        check(t, st['plan'])
        draw_field(cv, P, t, plan_=st['plan']); show_plan()
        info.insert('end', '\nplanned in %.2f s' % (time.time() - t0))

    def animate():
        pl, t = st['plan'], st['task']
        if not pl:
            return
        stacks = {p: list(s) for p, s in t.start.items()}
        frames, prev = [], park_field()
        for c, p, q, dt, kind in pl.steps:
            frames.append(({k: list(v) for k, v in stacks.items()}, prev, xy(p)))
            stacks[p].pop(); stacks.setdefault(q, []).append(c)
            frames.append(({k: list(v) for k, v in stacks.items()}, xy(p), xy(q)))
            prev = xy(q)
        def run(i=0, f=0):
            if i >= len(frames):
                draw_field(cv, P, t, plan_=pl); return
            snap, a, b = frames[i]
            u = f / 10
            draw_field(cv, P, t, stacks=snap, tool=(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
            w.after(25, run, i + (f == 10), 0 if f == 10 else f + 1)
        run()

    ttk.Label(top, text='checkers').pack(side='left')
    ttk.Spinbox(top, from_=1, to=40, width=4, textvariable=nvar).pack(side='left', padx=3)
    for txt, fn in (('New task', new_task), ('Plan', do_plan), ('Animate', animate)):
        ttk.Button(top, text=txt, command=fn).pack(side='left', padx=2)
    ttk.Label(side, text='Real runs (task entry, Start, scan, execute): run.py', foreground='#555').pack(fill='x')
    new_task()
    return w

def self_test(n_tasks=200):
    gains, bad = [], 0
    t0 = time.time()
    for k in range(n_tasks):
        t = random_task(random.Random(k).randint(3, 25), seed=k)
        pl = plan(t, tries=60, seed=k)
        nv = naive(t)
        if not pl or not nv:
            bad += 1; continue
        check(t, pl); check(t, nv)
        gains.append(1 - pl.total / nv.total)
    print('%d tasks (40%% of stacks at off-centre spots): %d without a plan; all plans legal and reach the goal' % (n_tasks, bad))
    print('best plan vs naive order: %.0f%% faster on average (min %.0f%%, max %.0f%%), %.2f s per task' % (
        100 * sum(gains) / len(gains), 100 * min(gains), 100 * max(gains), (time.time() - t0) / n_tasks))
    return bad == 0

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--test' in sys.argv:
        sys.exit(0 if self_test() else 1)
    window().mainloop()
