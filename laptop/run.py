"""
The competition run program (ETZ 3.5 cycle), for the real plotter or the digital twin:
  1. choose the task number and type the parameters -> red LED on (`led red 1`)
  2. the checkers are set out; the program waits for the Start button on the device (`event start`)
  3. home X / Y, scan the field (marks + checkers), find where the sheet really lies (5 mm / 3 deg allowed)
  4. build the task (tasks.py) and plan it (route_planner.py)
  5. each move = one queue on the ESP32 (no USB gaps): carry height -> line to the checker -> down -> magnet on ->
     up -> wrist turn -> line to the cell -> down -> magnet off -> up
  6. park, red LED off, report the time
Safety: CRASH / HOT / watchdog / battery stop / queue stopped -> abort: stop, magnet off, lift, park if possible, LED off.
Camera: on the twin the scan comes from the simulation; on the real plotter the camera scan is not built yet (the
camera is not chosen) - RealCamera says so.

Run:  python run.py               window (choose the twin or the ESP32 port)
      python run.py --test        the ETZ debug tasks + random tasks end to end on the twin, plus fault injection
"""
import math, queue, random, sys, threading, time
import field as F
import machine as M
import route_planner as R
import tasks as T
from esp_link import EspLink, list_ports

ABORT_EVENTS = ('CRASH', 'HOT', 'watchdog', 'battery stop', 'q stopped')

class RunAborted(Exception):
    pass

class TwinCamera:
    def __init__(self, twin):
        self.twin = twin
    def scan(self):
        return self.twin.scan()

class RealCamera:
    def scan(self):
        raise RunAborted('camera scan on the real plotter is not built yet (camera not chosen) - see docs/bringup.md')

class Runner:
    """Drives one run over an EspLink (real port or twin). log(kind, text) receives messages for the window."""
    def __init__(self, link, camera, cal=None, log=print, speed=1.0):
        self.link, self.camera, self.cal = link, camera, cal or M.load_cal()
        self.log, self.speed = log, speed
        self.events = queue.Queue()
        self.abort_reason = None
        self.wrist = 0.0
        self.phase = 'idle'
        self.step_i, self.steps_n = 0, 0
        self.plan = self.task = self.scene = self.transform = None
        self.t_start = None
        self.took = None
        self.in_abort = False                              # our own stop during an abort is not a new abort
        self.warnings = []

    # ------------------------------------------------------------ link helpers
    def pump(self):
        """move lines from the link log to the window log; remember events; abort events set abort_reason"""
        while not self.link.log.empty():
            kind, text = self.link.log.get()
            self.log(kind, text)
            if kind == 'rx' and text.startswith('event'):
                self.events.put(text)
                if any(k in text for k in ABORT_EVENTS) and not self.abort_reason and                         not (self.in_abort and ('q stopped' in text or 'watchdog' in text)):
                    self.abort_reason = text
            if kind == 'err' or (kind == 'rx' and text.startswith('err')):
                if not self.abort_reason and self.phase not in ('idle', 'parking', 'done'):
                    self.abort_reason = text

    def send(self, line):
        self.link.send(line)

    def wait_event(self, word, timeout):
        t_end = time.time() + timeout / self.speed
        while time.time() < t_end:
            self.pump()
            if self.abort_reason:
                raise RunAborted(self.abort_reason)
            try:
                e = self.events.get(timeout=0.02)
            except queue.Empty:
                continue
            if word in e:
                return e
        raise RunAborted('timeout waiting for "%s"' % word)

    def wait_state(self, cond, timeout, what):
        t_end = time.time() + timeout / self.speed
        while time.time() < t_end:
            self.pump()
            if self.abort_reason:
                raise RunAborted(self.abort_reason)
            s = self.link.state
            if s and cond(s):
                return s
            time.sleep(0.02)
        raise RunAborted('timeout: %s' % what)

    def run_queue(self, lines, timeout=60.0):
        self.send('qclear')
        for l in lines:
            self.send('q ' + l)
        while not self.events.empty():
            self.events.get()
        self.send('qrun')
        self.wait_event('q done', timeout)

    def magnet_field(self):
        s = self.link.state
        ax = {a['n']: a for a in s['ax']}
        mx, my = M.axis_to_magnet(ax['x']['pos'] / self.cal['steps_per_mm_x'], ax['y']['pos'] / self.cal['steps_per_mm_y'], self.cal)
        return (self.transform or M.FieldTransform()).to_field(mx, my)

    # ------------------------------------------------------------ the run
    def arm(self, number, params):
        """step 1: task chosen and parameters entered -> red LED on"""
        self.number, self.params = number, params
        T.TASKS[number]                                    # unknown number -> KeyError
        self.send('led red 1')
        self.phase = 'armed'
        self.log('info', 'task %d (%s) armed: red LED on - press Start on the device' % (number, T.TASKS[number].title))

    def run(self, start_timeout=600.0):
        try:
            self.phase = 'waiting for Start'
            self.wait_event('start', start_timeout)
            self.t_start = time.time()
            self.phase = 'homing'
            cal = self.cal                                 # the plan assumes these: never trust what the board has saved
            for line in ('speed x %d' % cal['speed_x'], 'speed y %d' % cal['speed_y'], 'speed w %d' % cal['speed_w'],
                         'accel x %d' % cal['accel_x'], 'accel y %d' % cal['accel_y'], 'accel w %d' % cal['accel_w'],
                         'jerk x %d' % cal['jerk_ms'], 'jerk y %d' % cal['jerk_ms']):
                self.send(line)
            self.send('servo %d' % M.servo_us(self.cal['h_carry'], self.cal))
            self.send('home all')
            self.wait_state(lambda s: all(a.get('homed') for a in s['ax'] if a['n'] in 'xy') and not any(a['run'] for a in s['ax']),
                            30, 'homing')
            self.phase = 'scanning'
            marks, tops = self.camera.scan()
            pairs = [(F.MARKS[mid], marks[mid]) for mid in F.MARK_IDS if mid in marks]
            if len(pairs) < 2:
                raise RunAborted('field not found: only %d marks seen' % len(pairs))
            self.transform = M.FieldTransform.fit(pairs)
            self.log('info', 'field: %s (fit error %.1f mm)' % (self.transform.describe(), self.transform.residual(pairs)))
            self.scene = T.Scene.from_scan(tops, self.transform)
            self.phase = 'planning'
            self.task = T.build(self.number, self.scene, self.params)
            self.plan = R.plan(self.task, tries=150, tool=self.magnet_field())
            if self.plan is None:
                raise RunAborted('no plan found for this task')
            self.steps_n = len(self.plan.steps)
            self.log('info', 'plan: %d moves, about %.1f s' % (self.steps_n, self.plan.total))
            self.phase = 'moving'
            levels = {p: len(s) for p, s in self.task.start.items()}
            pos = dict(getattr(self.task, 'pos', {}))      # where each stack really is
            for i, (c, p, q, dt, kind) in enumerate(self.plan.steps):
                self.step_i = i + 1
                turn = self.task.angle.get(c, 0.0) if kind == 'goal' else 0.0
                src = pos.get(p, R.xy(p))
                dst = pos[q] if levels.get(q, 0) > 0 and q in pos else R.xy(q)
                self.do_move(src, dst, levels.get(p, 0), levels.get(q, 0), turn)
                levels[p] = levels.get(p, 0) - 1
                levels[q] = levels.get(q, 0) + 1
                if levels[p] == 0:
                    pos.pop(p, None)
                pos.setdefault(q, dst)
                self.log('info', 'move %d/%d done: %s %s -> %s' % (i + 1, self.steps_n, self.task.colour.get(c, '?'),
                                                                  R.pname(p, latin=False), R.pname(q, latin=False)))
            self.park()
            self.phase = 'done'
            self.took = (time.time() - self.t_start) * self.speed
            self.log('info', 'finished in %.1f s (planned %.1f s + homing / scan)' % (self.took, self.plan.total))
            return True
        except RunAborted as e:
            self.abort(str(e))
            return False

    def axis_cmd(self, field_pt, shift=(0.0, 0.0)):
        """field mm -> 'linemm ax ay' (machine shift added, clamped into reach; warns when that moves it a lot).
        Returns the command and how far the clamp moved the magnet (machine dx, dy)."""
        mx, my = self.transform.to_machine(*field_pt)
        mx, my = mx + shift[0], my + shift[1]
        cx, cy, moved = M.clamp_to_reach(mx, my)
        if moved > 0.3:
            msg = 'target %.1f mm outside the reach (X travel): clamped' % moved
            self.warnings.append(msg); self.log('err' if moved > 7 else 'info', msg)
        ax, ay = M.magnet_to_axis(cx, cy, self.cal)
        return 'linemm %.2f %.2f' % (ax, ay), (mx - cx, my - cy)

    def do_move(self, src, dst, src_levels, dst_levels, turn):
        cal = self.cal
        carry = M.servo_us(cal['h_carry'], cal)
        pick = M.servo_us(M.stack_top(src_levels), cal)
        place = M.servo_us(M.stack_top(dst_levels) + M.CHECKER_H + 1.0, cal)
        go_src, off = self.axis_cmd(src)
        # a checker the magnet could not reach exactly hangs off-centre by `off` (machine mm); the wrist turn swings
        # it round with the magnet; the drop is shifted the other way so it lands centred
        a = math.radians(turn)
        off = (off[0] * math.cos(a) - off[1] * math.sin(a), off[0] * math.sin(a) + off[1] * math.cos(a))
        go_dst, _ = self.axis_cmd(dst, shift=(-off[0], -off[1]))
        lines = ['servo %d' % carry, go_src, 'servo %d' % pick, 'mag on', 'wait %d' % (cal['mag_grab'] * 1000),
                 'servo %d' % carry]
        if turn:
            self.wrist = (self.wrist + turn) % 360.0
            lines.append('wrist %.1f' % self.wrist)
        lines += [go_dst, 'servo %d' % place, 'mag off', 'wait %d' % (cal['mag_release'] * 1000), 'servo %d' % carry]
        self.run_queue(lines)

    def park(self):
        self.phase = 'parking'
        ax, ay = M.carriage_to_axis(*M.PARK, self.cal)
        self.run_queue(['servo %d' % M.servo_us(self.cal['h_carry'], self.cal), 'linemm %.2f %.2f' % (ax, ay)])
        self.send('led red 0')

    def abort(self, why):
        self.log('err', 'RUN ABORTED: %s' % why)
        self.phase = 'aborting'
        self.in_abort = True
        self.send('stop'); self.send('qclear'); self.send('mag off')
        time.sleep(0.2 / self.speed + 0.1); self.pump()        # let our own stop's events go by
        self.send('servo %d' % M.servo_us(self.cal['h_carry'], self.cal))
        crashed = 'CRASH' in why
        self.abort_reason = None
        try:
            if 'battery' in why:
                pass                                        # moves are refused: stay where it is
            else:
                if crashed:
                    self.send('home all')
                    self.wait_state(lambda s: all(a.get('homed') and not a.get('lost') for a in s['ax'] if a['n'] in 'xy')
                                    and not any(a['run'] for a in s['ax']), 30, 'homing after the crash')
                self.park()
        except RunAborted as e:
            self.log('err', 'could not park: %s' % e)
        self.send('led red 0')
        self.in_abort = False
        self.phase = 'aborted'

# ---------------------------------------------------------------- window
def window(master=None):
    import tkinter as tk
    from tkinter import ttk
    root = tk.Toplevel(master) if master else tk.Tk(); root.title('ETZ plotter - run')
    st = {'link': None, 'runner': None, 'twin': None}
    top = ttk.Frame(root, padding=6); top.pack(fill='x')
    ttk.Label(top, text='Board').pack(side='left')
    ports = ['TWIN (simulation)'] + ['%s  %s' % p for p in list_ports()]
    board = ttk.Combobox(top, values=ports, width=34, state='readonly'); board.current(0); board.pack(side='left', padx=4)
    ttk.Label(top, text='Task').pack(side='left', padx=(10, 2))
    names = ['%d  %s' % (n, td.title) for n, td in T.TASKS.items()]
    task = ttk.Combobox(top, values=names, width=40, state='readonly'); task.current(0); task.pack(side='left')
    pframe = ttk.Frame(root, padding=(6, 0)); pframe.pack(fill='x')
    entries = {}
    def show_params(*_):
        for w in pframe.winfo_children():
            w.destroy()
        entries.clear()
        for k, d in T.TASKS[int(task.get().split()[0])].params:
            ttk.Label(pframe, text=k).pack(side='left')
            e = ttk.Entry(pframe, width=22); e.insert(0, d); e.pack(side='left', padx=(2, 10)); entries[k] = e
    task.bind('<<ComboboxSelected>>', show_params); show_params()
    mid = ttk.Frame(root, padding=6); mid.pack(fill='both', expand=True)
    P, W, H = R.canvas_mapping(2.3)
    cv = tk.Canvas(mid, width=W, height=H, bg='white'); cv.pack(side='left')
    right = ttk.Frame(mid, padding=(8, 0)); right.pack(side='left', fill='both', expand=True)
    phase = tk.Label(right, text='not connected', font=('Segoe UI', 13, 'bold'), anchor='w'); phase.pack(fill='x')
    timer = ttk.Label(right, text='', font=('Segoe UI', 11)); timer.pack(fill='x')
    b = ttk.Frame(right); b.pack(fill='x', pady=4)
    logbox = tk.Text(right, height=24, width=60, font=('Consolas', 9)); logbox.pack(fill='both', expand=True)
    for tag, col in (('tx', '#1a5fb4'), ('rx', '#222'), ('info', '#2e7d32'), ('err', '#d23b3b')):
        logbox.tag_config(tag, foreground=col)
    msgs = queue.Queue()
    def log(kind, text):
        if kind == 'rx' and (text.startswith('{') or text == 'pong' or text.startswith('ok q')):
            return
        msgs.put((kind, text))

    def connect():
        if st['link'] and st['link'].connected:
            return
        link = EspLink()
        if board.current() == 0:
            link.connect(None, fake=True)
            st['twin'] = link.ser
            tw = link.ser
            for name, colour in (('Д1', 'red'), ('Б3', 'blue'), ('В6', 'green'), ('А8', 'yellow')):
                tw.world.put_cell(name, colour)
            cam = TwinCamera(tw)
        else:
            link.connect(board.get().split()[0])
            cam = RealCamera()
        st['link'] = link
        st['runner'] = Runner(link, cam, log=log)

    def arm():
        connect()
        r = st['runner']
        n = int(task.get().split()[0])
        r.arm(n, {k: e.get() for k, e in entries.items()})
        threading.Thread(target=r.run, daemon=True).start()

    def press_start():
        if st['twin']:
            st['twin'].press_start()
        else:
            msgs.put(('info', 'press the real Start button on the device'))

    def abort():
        r = st['runner']
        if r:
            r.abort_reason = 'stopped from the laptop'
    ttk.Button(b, text='Connect', command=connect).pack(side='left', padx=2)
    ttk.Button(b, text='Enter task (red LED on)', command=arm).pack(side='left', padx=2)
    ttk.Button(b, text='Start (twin: simulated button)', command=press_start).pack(side='left', padx=2)
    tk.Button(b, text='ABORT', bg='#d23b3b', fg='white', command=abort).pack(side='left', padx=8)

    def tick():
        while not msgs.empty():
            kind, text = msgs.get()
            logbox.insert('end', ('> ' if kind == 'tx' else '') + text + '\n', kind); logbox.see('end')
        r = st['runner']
        if r:
            r.pump() if r.phase in ('idle', 'armed', 'done', 'aborted') else None
            ph = r.phase + ('  %d/%d' % (r.step_i, r.steps_n) if r.phase == 'moving' else '')
            phase.config(text=ph, fg='#d23b3b' if 'abort' in r.phase else '#222')
            if r.t_start and r.phase not in ('done', 'aborted'):
                timer.config(text='run time %.1f s' % ((time.time() - r.t_start) * r.speed))
            tw = st['twin']
            if tw:
                stacks = {('p', *tw.world.sheet.to_field(s.mx, s.my)): [c.id for c in s.checkers] for s in tw.world.stacks if s.checkers}
                colour = {c.id: c.colour for s in tw.world.stacks for c in s.checkers}
                if tw.held is not None:
                    colour[tw.held.id] = tw.held.colour
                fake = R.Task(stacks, {}, colour)
                mx, my = tw.magnet_xy()
                R.draw_field(cv, P, fake, tool=tw.world.sheet.to_field(mx, my))
            else:
                R.draw_field(cv, P, r.task, plan_=r.plan)
        else:
            R.draw_field(cv, P)
        root.after(100, tick)
    tick()
    if master is None:
        root.mainloop()
    return root

# ---------------------------------------------------------------- end-to-end test on the twin
def _twin_run(setup, number, params, sheet=(0.0, 0.0, 0.0), speed=25.0, fault=None, seed=1):
    """setup(world) puts checkers; returns (ok, runner, twin, seconds_virtual)"""
    link = EspLink()
    link.connect(None, fake=True, speed=speed)
    tw = link.ser
    tw.rng = random.Random(seed)
    nominal = M.FieldTransform()
    tw.world.sheet = M.FieldTransform(nominal.a + math.radians(sheet[2]), nominal.ox + sheet[0], nominal.oy + sheet[1])
    setup(tw.world)
    lines = []
    r = Runner(link, TwinCamera(tw), log=lambda k, t: lines.append((k, t)), speed=speed)
    time.sleep(0.4)
    r.arm(number, params)
    th = threading.Thread(target=r.run, daemon=True); th.start()
    time.sleep(0.3); tw.press_start()
    if fault:
        t_end = time.time() + 30
        while r.phase != 'moving' and time.time() < t_end:      # inject the fault in the middle of the moves
            time.sleep(0.01)
        time.sleep(0.05)
        if fault == 'battery':
            tw.set_battery(13.9)
        if fault == 'crash':
            with tw.lock:
                tw._event('CRASH x: test fault')
    th.join(timeout=120)
    vt = r.took if r.took is not None else -1.0
    link.disconnect()
    return r, tw, lines, vt

def _placed(tw, cell, level, colour):
    """is there a checker of that colour at that level in that cell (ETZ 2.4)?"""
    for s in tw.world.stacks:
        X, Y = tw.world.sheet.to_field(s.mx, s.my)
        if F.placed_in(X, Y, cell) and len(s.checkers) > level and not s.fallen:
            c = s.checkers[level]
            if c.colour == colour and c.lid_up:
                return True
    return False

def self_test(n_random=30):
    ok_all = True
    def check(name, cond):
        nonlocal ok_all
        ok_all &= bool(cond)
        print('  %-72s %s' % (name, 'ok' if cond else 'FAILED'))
    rnd = random.Random(7)
    def parked(tw):
        return math.dist(M.magnet_to_carriage(*tw.magnet_xy()), M.PARK) < 1.0 and tw.led_red == 0
    # 1. move Д1 -> Д5 with the sheet 3 mm off and 1.5 deg turned
    r, tw, lines, vt = _twin_run(lambda w: w.put_cell('Д1', 'red'), 1, {'from': 'Д1', 'to': 'Д5'}, sheet=(3.0, -2.0, 1.5))
    check('task 1: red Д1 -> Д5 (sheet 3 mm off, 1.5 deg), parked, LED off (%.1f s)' % vt,
          r.phase == 'done' and _placed(tw, F.parse_cell('Д5'), 0, 'red') and parked(tw))
    # 2. far along X
    r, tw, lines, vt = _twin_run(lambda w: w.put_cell('В4', 'blue'), 2, {'cell': 'В4', 'axis': 'X'})
    check('task 2: blue В4 -> В0 or В8 (%.1f s)' % vt, r.phase == 'done' and (
        _placed(tw, (0, 3), 0, 'blue') or _placed(tw, (8, 3), 0, 'blue')))
    # 3. line of three
    def three(w):
        w.put_cell('А0', 'red'); w.put_cell('А4', 'blue'); w.put_cell('Г7', 'green')
    r, tw, lines, vt = _twin_run(three, 3, {})
    cells = [F.cell_of(*tw.world.sheet.to_field(s.mx, s.my)) for s in tw.world.stacks]
    on_line = len(cells) == 3 and all(cells) and bool(T._collinear_cells(cells[0], cells[1])) and cells[2] in T._collinear_cells(cells[0], cells[1])
    check('task 3: three checkers end on one grid line (%.1f s)' % vt, r.phase == 'done' and on_line)
    # 4. build a stack red, green, blue in В4 from three spots
    def spread(w):
        w.put_cell('А0', 'blue'); w.put_cell('Д7', 'red'); w.put_cell('Б5', 'green')
    r, tw, lines, vt = _twin_run(spread, 6, {'cell': 'В4', 'order': 'red,green,blue'})
    check('task 6: stack red/green/blue in В4 (%.1f s)' % vt, r.phase == 'done' and all(
        _placed(tw, (4, 3), i, c) for i, c in enumerate(('red', 'green', 'blue'))))
    # 5. random colour tasks, sheet within half the ETZ tolerance (full tolerance: see machine.worst_reach_shortfall)
    good = 0
    times = []
    for k in range(n_random):
        cols = rnd.sample(F.COLOURS, 3)
        spots = rnd.sample([c for c in F.field_cells() if 1 <= c[1] <= 5], 6)
        targets = rnd.sample([c for c in F.field_cells() if c not in spots and 1 <= c[1] <= 5], 3)
        pts = [(cell, cols[i % 3]) for i, cell in enumerate(spots)]
        def setup(w, pts=pts):
            for cell, colour in pts:
                X, Y = F.cell_centre(*cell)
                w.put(X + rnd.uniform(-5, 5), Y + rnd.uniform(-5, 5), colour)
        mapping = ' '.join('%s=%s' % (cols[i], F.cell_name(targets[i])) for i in range(3))
        sheet = (rnd.uniform(-2.5, 2.5), rnd.uniform(-2.5, 2.5), rnd.uniform(-1.5, 1.5))
        r, tw, lines, vt = _twin_run(setup, 4, {'map': mapping}, sheet=sheet, seed=k)
        ok = r.phase == 'done' and all(_placed(tw, targets[i], j, cols[i]) for i in range(3) for j in range(2))
        good += ok; times.append(vt)
        if not ok:
            print('     random %d failed: %s; %s; wanted %s' % (k, r.phase, [t for kd, t in lines if kd == 'err'][:3], mapping))
            for s in tw.world.stacks:
                X, Y = tw.world.sheet.to_field(s.mx, s.my)
                cell = F.cell_of(X, Y)
                print('       (%6.1f, %6.1f) %-6s off %4.1f mm: %s%s' % (X, Y, F.cell_name(cell, latin=True),
                      math.dist((X, Y), F.cell_centre(*cell)) if cell else -1,
                      [x.colour + ('' if x.lid_up else '(lid down)') for x in s.checkers], ' FALLEN' if s.fallen else ''))
    check('random colour tasks (6 checkers, 2 per colour stacked): %d / %d placed, mean %.0f s' % (
        good, n_random, sum(times) / len(times)), good == n_random)
    # 6. faults
    r, tw, lines, vt = _twin_run(spread, 6, {'cell': 'В4', 'order': 'red,green,blue'}, fault='battery')
    check('fault: battery stop -> run aborted, magnet off, LED off', r.phase == 'aborted' and tw.mag == 0 and tw.led_red == 0)
    r, tw, lines, vt = _twin_run(spread, 6, {'cell': 'В4', 'order': 'red,green,blue'}, fault='crash')
    check('fault: crash event -> aborted, re-homed and parked, LED off', r.phase == 'aborted' and parked(tw))
    print('run self-test:', 'PASS' if ok_all else 'FAIL')
    return ok_all

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--test' in sys.argv:
        sys.exit(0 if self_test(int(sys.argv[sys.argv.index('--test') + 1]) if len(sys.argv) > sys.argv.index('--test') + 1 else 30) else 1)
    window()
