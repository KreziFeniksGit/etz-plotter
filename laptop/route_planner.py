"""
Route planner: in which order to move the checkers so the whole task takes the least time.

The task: checkers stand in stacks (up to 5) on the 6 x 9 cells and the 5 buffer places. Each checker has a goal
(cell + level in the stack, and a wrist angle). The gripper can only take the TOP checker of a stack and only put it
on TOP of a stack. So the order matters twice:
  - legality: a checker can go to its goal only when the stack there already holds exactly the checkers that belong
    under it; a checker that blocks one below it has to move first (to its goal, or aside to a free place);
  - time: the tool travels between the moves; a good order saves a lot of travel.
Method (our own): many randomised greedy plans (each step: pick among the cheapest legal moves, with a bit of
randomness), keep the fastest. Travel time = straight XY line with trapezoid speed (the firmware's 'line' move),
plus pick / place time; the wrist turns during the travel.

Run:  python route_planner.py           window with a random task (New task, Plan, Animate, Run on the plotter)
      python route_planner.py --test    check on 200 random tasks (legal, reaches the goal, gain vs naive order)
"""
import math, random, sys, time, threading
import field as F

# ---------------------------------------------------------------- machine parameters (planning model)
V_MAX = 150.0        # mm/s straight-line speed (rule: at least 100 mm/s)
A_MAX = 1500.0       # mm/s^2
T_PICK = 0.6         # s: lower, magnet on, lift
T_PLACE = 0.6        # s: lower, magnet off (+ release pulse), lift
W_SPEED = 360.0      # deg/s wrist
PARK = (40.0, -40.0)  # field mm where the tool starts and ends (VERIFY: set from the real parked position)
STEPS_PER_MM = 80.0  # GT2 belt, 20-tooth pulley, 200 steps x 16 microsteps: 3200 / 40 mm
MAX_STACK = 5

def places():
    """every place a checker can stand: ('c', col, row) cells and ('b', col) buffer places"""
    ps = [('c', c, r) for c in range(F.COLS) for r in range(F.ROWS)]
    ps += [('b', c) for c in range(F.BUFFER_COLS)]
    return ps

def xy(p):
    if p == 'park':
        return PARK
    return F.cell_centre(p[1], p[2] if p[0] == 'c' else F.BUFFER_ROW)

def pname(p):
    if p == 'park':
        return 'park'
    return ('buf ' if p[0] == 'b' else '') + F.cell_name((p[1], p[2] if p[0] == 'c' else F.BUFFER_ROW), latin=True)

def travel(a, b):
    """seconds for a straight move between two field points (trapezoid speed profile)"""
    L = math.dist(a, b)
    if L < 1e-6:
        return 0.0
    if L < V_MAX * V_MAX / A_MAX:
        return 2 * math.sqrt(L / A_MAX)
    return L / V_MAX + V_MAX / A_MAX

class Task:
    """start: {place: [checker ids bottom..top]}; goal: {checker: (place, level)}; angle: {checker: deg};
    colour: {checker: name}"""
    def __init__(self, start, goal, colour, angle=None):
        self.start, self.goal, self.colour = start, goal, colour
        self.angle = angle or {}

    def goal_stacks(self):
        g = {}
        for c, (p, lvl) in self.goal.items():
            g.setdefault(p, {})[lvl] = c
        return {p: [d[i] for i in sorted(d)] for p, d in g.items()}

def random_task(n=12, seed=None, max_start_stack=3):
    """a legal random task: n checkers in random stacks, goals = random stacks up to 5 high"""
    rnd = random.Random(seed)
    ps = [p for p in places() if p[0] == 'c']
    start, goal, colour, angle = {}, {}, {}, {}
    ids = list(range(n))
    for c in ids:
        colour[c] = rnd.choice(F.COLOURS)
        angle[c] = rnd.choice((0, 0, 90, 180, 270, rnd.randrange(360)))
    i = 0
    while i < n:
        p = rnd.choice(ps)
        if p in start:
            continue
        k = min(n - i, rnd.randint(1, max_start_stack))
        start[p] = ids[i:i + k]; i += k
    order = ids[:]; rnd.shuffle(order); i = 0
    used = set()
    while i < n:
        p = rnd.choice(ps)
        if p in used:
            continue
        used.add(p)
        k = min(n - i, rnd.randint(1, MAX_STACK))
        for lvl, c in enumerate(order[i:i + k]):
            goal[c] = (p, lvl)
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

def plan(task, tries=300, greed=0.25, seed=0, order=None, polish=True):
    """best of `tries` randomised greedy plans, then polished (steps moved in the order while it saves time).
    order = a fixed checker order (naive plan, for comparison)"""
    rnd = random.Random(seed)
    gst = task.goal_stacks()
    best = None
    for t in range(1 if order else tries):
        r = _one_plan(task, gst, rnd, 0.0 if (t == 0 or order) else greed, order)
        if r and (best is None or r.total < best.total):
            best = r
    if best and polish and not order:
        best = _polish(task, best)
    return best

def _replay(task, steps):
    """total time of a step list, or None if a move is illegal / the goal is not reached"""
    stacks = {p: list(s) for p, s in task.start.items()}
    tool, total, out = PARK, 0.0, []
    for c, p, q, dt, kind in steps:
        s = stacks.get(p)
        if not s or s[-1] != c or len(stacks.get(q, [])) >= MAX_STACK:
            return None, None
        s.pop(); stacks.setdefault(q, []).append(c)
        rot = abs(task.angle.get(c, 0)) / W_SPEED if kind == 'goal' else 0.0
        dt = travel(tool, xy(p)) + T_PICK + max(travel(xy(p), xy(q)), rot) + T_PLACE
        out.append((c, p, q, dt, kind)); total += dt
        tool = xy(q)
    for c, (gp, lvl) in task.goal.items():
        g = stacks.get(gp, [])
        if len(g) <= lvl or g[lvl] != c:
            return None, None
    return total + travel(tool, PARK), out

def _polish(task, pl):
    """local search: take one step out and put it back elsewhere; keep it when legal and faster"""
    best_t, steps = _replay(task, pl.steps)
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
                t, out = _replay(task, s)
                if t is not None and t < best_t - 1e-6:
                    best_t, steps, improved = t, out, True
                    break
            if improved:
                break
    return Plan(steps, best_t)

def _one_plan(task, gst, rnd, greed, order):
    stacks = {p: list(s) for p, s in task.start.items()}
    where = {c: p for p, s in stacks.items() for c in s}
    tool = PARK
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
            if len(gs) == lvl and final_ok(gp) == lvl and (p != gp):
                cands.append((c, p, gp, 'goal'))
        if order:                   # naive: only the next checker of the fixed order, else unblock
            nxt = next((c for c in order if not (where[c] == task.goal[c][0] and
                        final_ok(where[c]) > stacks[where[c]].index(c))), None)
            cands = [x for x in cands if x[0] == nxt]
        if not cands:
            # 2) unblock: move a top checker that is in the way to a free place (not a goal place still needed)
            blocked = []
            for p, s in stacks.items():
                if not s:
                    continue
                fh = final_ok(p)
                # the top blocks something if it sits on a goal place that is not right yet,
                # or if another non-final checker is under it
                if (p in goal_places and len(s) > fh) or len(s) - fh >= 2:
                    blocked.append(p)
            if not blocked:
                return None
            free = [q for q in places() if not stacks.get(q) and q not in goal_places]
            if not free:
                return None
            for p in blocked:
                c = stacks[p][-1]
                q = min(free, key=lambda q: math.dist(xy(p), xy(q)) + math.dist(xy(q), xy(task.goal[c][0])))
                cands.append((c, p, q, 'aside'))
        def cost(x):
            c, p, q, kind = x
            tr = travel(tool, xy(p)) + T_PICK
            rot = abs(task.angle.get(c, 0)) / W_SPEED if kind == 'goal' else 0.0
            return tr + max(travel(xy(p), xy(q)), rot) + T_PLACE + (0.5 if kind == 'aside' else 0.0)
        cands.sort(key=cost)
        k = 0
        if greed and len(cands) > 1 and rnd.random() < greed:
            k = rnd.randrange(min(3, len(cands)))
        c, p, q, kind = cands[k]
        dt = cost(cands[k]) - (0.5 if kind == 'aside' else 0.0)
        stacks[p].pop()
        stacks.setdefault(q, []).append(c)
        where[c] = q
        steps.append((c, p, q, dt, kind))
        total += dt
        tool = xy(q)
    else:
        return None
    total += travel(tool, PARK)
    return Plan(steps, total)

def check(task, pl):
    """replay a plan: every move legal (top only, stack <= 5) and the end state = the goal"""
    stacks = {p: list(s) for p, s in task.start.items()}
    for c, p, q, dt, kind in pl.steps:
        assert stacks.get(p) and stacks[p][-1] == c, 'took a checker that is not on top'
        stacks[p].pop()
        stacks.setdefault(q, []).append(c)
        assert len(stacks[q]) <= MAX_STACK, 'stack above 5'
    for c, (gp, lvl) in task.goal.items():
        assert stacks[gp][lvl] == c, 'goal not reached'
    return True

# ---------------------------------------------------------------- window
def _plotter_steps(pt):
    """field mm -> plotter steps (X along the field's -x, Y along +y; VERIFY with the real mounting)"""
    return int(round(-pt[0] * STEPS_PER_MM)), int(round(pt[1] * STEPS_PER_MM))

def window(link=None, master=None):
    import tkinter as tk
    from tkinter import ttk
    S = 2.6                                          # px per mm
    X0, Y1 = -215.0, 280.0                           # field mm shown at the top-left
    w = tk.Toplevel(master) if master else tk.Tk()
    w.title('ETZ route planner')
    top = ttk.Frame(w, padding=4); top.pack(fill='x')
    cv = tk.Canvas(w, width=int(290 * S), height=int(345 * S), bg='white'); cv.pack(side='left', padx=4, pady=4)
    side = ttk.Frame(w, padding=4); side.pack(side='left', fill='both', expand=True)
    info = tk.Text(side, width=44, height=34, font=('Consolas', 9)); info.pack(fill='both', expand=True)
    st = {'task': None, 'plan': None, 'naive': None, 'running': False}
    nvar = tk.IntVar(value=12)

    def P(x, y):
        return (x - X0) * S, (Y1 - y) * S

    def draw(highlight=None, tool=None):
        cv.delete('all')
        for (c, r) in F.all_cells():
            x, y = F.cell_centre(c, r)
            cv.create_rectangle(*P(x - 14, y + 14), *P(x + 14, y - 14), outline='#bbb')
            cv.create_text(*P(x, y - 11), text=F.cell_name((c, r), latin=True), fill='#aaa', font=('Segoe UI', 7))
        for b in range(F.BUFFER_COLS):
            x, y = F.cell_centre(b, F.BUFFER_ROW)
            cv.create_rectangle(*P(x - 14, y + 14), *P(x + 14, y - 14), outline='#88a', dash=(3, 2))
        for mid, (mx, my) in F.MARKS.items():
            cv.create_rectangle(*P(mx - 9, my + 9), *P(mx + 9, my - 9), fill='black')
        cv.create_oval(*P(PARK[0] - 4, PARK[1] + 4), *P(PARK[0] + 4, PARK[1] - 4), outline='black')
        cv.create_text(*P(PARK[0], PARK[1] - 9), text='park', font=('Segoe UI', 7))
        t = st['task']
        if not t:
            return
        for p, gl in t.goal_stacks().items():       # goal: small coloured ring per level
            x, y = xy(p)
            for i, c in enumerate(gl):
                cv.create_oval(*P(x - 12 + 4 * i, y + 12), *P(x - 8 + 4 * i, y + 8), outline=t.colour[c], width=2)
        stacks = st.get('now') or t.start
        for p, s in stacks.items():
            if not s:
                continue
            x, y = xy(p)
            c = s[-1]
            cv.create_oval(*P(x - 11, y + 11), *P(x + 11, y - 11), fill=t.colour[c], outline='black')
            cv.create_text(*P(x, y), text=str(len(s)) if len(s) > 1 else '', font=('Segoe UI', 9, 'bold'))
        pl = st['plan']
        if pl and highlight is None:
            prev = PARK
            for i, (c, p, q, dt, kind) in enumerate(pl.steps):
                a, b = xy(p), xy(q)
                cv.create_line(*P(*prev), *P(*a), fill='#ccc', dash=(2, 3))
                cv.create_line(*P(*a), *P(*b), arrow='last', fill='#d33' if kind == 'aside' else '#235', width=1.5)
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                cv.create_text(*P(mx, my), text=str(i + 1), fill='#235', font=('Segoe UI', 8, 'bold'))
                prev = b
        if tool:
            cv.create_line(*P(tool[0] - 6, tool[1]), *P(tool[0] + 6, tool[1]), width=2)
            cv.create_line(*P(tool[0], tool[1] - 6), *P(tool[0], tool[1] + 6), width=2)

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
            info.insert('end', '%2d. %-7s %-7s -> %-7s %4.1f s%s\n' % (i + 1, t.colour[c], pname(p), pname(q), dt,
                                                                     '  (aside)' if kind == 'aside' else ''))

    def new_task():
        st['task'] = random_task(nvar.get(), seed=random.randrange(10 ** 6))
        st['plan'] = st['naive'] = None; st['now'] = None
        draw(); info.delete('1.0', 'end'); info.insert('end', 'press Plan')

    def do_plan():
        t = st['task']
        t0 = time.time()
        st['plan'] = plan(t)
        st['naive'] = plan(t, order=sorted(t.goal, key=lambda c: (t.goal[c][1], c)))
        st['now'] = None
        check(t, st['plan'])
        draw(); show_plan()
        info.insert('end', '\nplanned in %.2f s' % (time.time() - t0))

    def animate():
        pl, t = st['plan'], st['task']
        if not pl:
            return
        stacks = {p: list(s) for p, s in t.start.items()}
        frames = []
        prev = PARK
        for c, p, q, dt, kind in pl.steps:
            frames.append((dict((k, list(v)) for k, v in stacks.items()), prev, xy(p)))
            stacks[p].pop(); stacks.setdefault(q, []).append(c)
            frames.append((dict((k, list(v)) for k, v in stacks.items()), xy(p), xy(q)))
            prev = xy(q)
        def run(i=0, f=0):
            if i >= len(frames):
                st['now'] = None; draw(); return
            snap, a, b = frames[i]
            st['now'] = snap
            u = f / 10
            draw(highlight=True, tool=(a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
            w.after(25, run, i + (f == 10), 0 if f == 10 else f + 1)
        run()

    def run_on_plotter():
        if not link or not link.connected:
            info.insert('end', '\n\nnot connected: open the planner from the dashboard and Connect first'); return
        if st['running'] or not st['plan']:
            return
        st['running'] = True
        def job():
            def wait_xy():
                time.sleep(0.3)
                t0 = time.time()
                while st['running'] and time.time() - t0 < 30:
                    s = link.state
                    if s and not any(a['run'] for a in s['ax'] if a['n'] in 'xy'):
                        return True
                    time.sleep(0.05)
                return False
            for i, (c, p, q, dt, kind) in enumerate(st['plan'].steps):
                for pt, pause in ((xy(p), T_PICK), (xy(q), T_PLACE)):
                    if not st['running']:
                        break
                    x, y = _plotter_steps(pt)
                    link.send('line %d %d' % (x, y))
                    if not wait_xy():
                        st['running'] = False; break
                    time.sleep(pause)            # lift / magnet not built yet: just the time they will take
            x, y = _plotter_steps(PARK)
            link.send('line %d %d' % (x, y))
            st['running'] = False
        threading.Thread(target=job, daemon=True).start()

    def stop_run():
        st['running'] = False
        if link and link.connected:
            link.send('stop')

    ttk.Label(top, text='checkers').pack(side='left')
    ttk.Spinbox(top, from_=1, to=40, width=4, textvariable=nvar).pack(side='left', padx=3)
    for txt, fn in (('New task', new_task), ('Plan', do_plan), ('Animate', animate),
                    ('Run on the plotter', run_on_plotter), ('Stop', stop_run)):
        ttk.Button(top, text=txt, command=fn).pack(side='left', padx=2)
    ttk.Label(side, text='Run on the plotter: X/Y follow the plan with "line" moves, starting from X/Y = 0 at the\n'
                        'park point (zero them there first). Lift and magnet: only their time is waited.',
              foreground='#555').pack(fill='x')
    new_task()
    return w

def self_test(n_tasks=200):
    gains, bad = [], 0
    t0 = time.time()
    for k in range(n_tasks):
        t = random_task(random.Random(k).randint(3, 25), seed=k)
        pl = plan(t, tries=60, seed=k)
        nv = plan(t, order=sorted(t.goal, key=lambda c: (t.goal[c][1], c)))
        if not pl or not nv:
            bad += 1; continue
        check(t, pl); check(t, nv)
        gains.append(1 - pl.total / nv.total)
    print('%d tasks: %d without a plan, all plans legal and reach the goal' % (n_tasks, bad))
    print('best plan vs naive order: %.0f%% faster on average (min %.0f%%, max %.0f%%), %.2f s per task' % (
        100 * sum(gains) / len(gains), 100 * min(gains), 100 * max(gains), (time.time() - t0) / n_tasks))
    return bad == 0

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--test' in sys.argv:
        sys.exit(0 if self_test() else 1)
    window().mainloop()
