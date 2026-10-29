"""
Digital twin of the plotter: behaves like the ESP32 firmware on the serial port (same commands, replies, events and
json status lines), and simulates the machine and the field, so the laptop programs (dashboard, run program, planner)
can be tested end to end before the plotter exists.

What is simulated:
- X / Y / wrist steppers with the firmware's speed profile (machine.move_time), absolute moves, coordinated lines,
  homing switches, soft limits after homing, crash when the magnet hits a stack while moving low.
- servo lift (pulse width -> magnet face height, slew limited), magnet (grab delay, hold), red LED, Start button,
  battery voltage with low / stop events, idle switch-off, laptop watchdog, motor heat estimate, move queue.
- the field: stacks of checkers (colour, sticker text, angle); picking = magnet on, touching the top checker of a stack
  within the capture radius; placing = magnet off: the checker drops, lands on a stack below it or on the sheet
  (small random error; a drop half on a stack makes it fall over = not placed).
- a camera scan: what the vision would report (marks and top checkers in machine mm, with noise).
Firmware command syntax for the new parts (homing, mm, servo, magnet, wrist, LED, queue): docs in firmware/README.md.
Python API for tests: Twin.world (World), Twin.press_start(), Twin.scan(), Twin.score(goals).
Time: `speed` > 1 runs the machine faster than real time (tests); the laptop watchdog always uses real time.

Run:  python twin.py --test
"""
import json, math, random, sys, threading, time
import field as F
import machine as M

STEPS_PER_REV = 3200

# ---------------------------------------------------------------- the field world
class Checker:
    _next = 0
    def __init__(self, colour, tag='', angle=0.0):
        Checker._next += 1
        self.id = Checker._next
        self.colour, self.tag, self.angle = colour, tag, angle
        self.lid_up = True

class Stack:
    def __init__(self, mx, my, checkers=None):
        self.mx, self.my = mx, my                  # machine mm of the bottom checker's centre
        self.checkers = checkers or []             # bottom .. top
        self.fallen = False                        # a checker dropped half on it: the whole stack counts as messed up

class World:
    def __init__(self, sheet=None, rng=None):
        self.sheet = sheet or M.FieldTransform()   # the true sheet position (the run program must find it)
        self.stacks = []
        self.rng = rng or random.Random(1)

    def put(self, X, Y, colour, tag='', angle=0.0, field=True):
        """add a checker at field (X, Y) (or machine mm with field=False); on top of a stack if one is there"""
        mx, my = self.sheet.to_machine(X, Y) if field else (X, Y)
        c = Checker(colour, tag, angle)
        s = self.stack_at(mx, my, 3.0)
        if s:
            s.checkers.append(c)
        else:
            self.stacks.append(Stack(mx, my, [c]))
        return c

    def put_cell(self, name, colour, tag='', angle=0.0):
        return self.put(*F.cell_centre(*F.parse_cell(name)), colour, tag, angle)

    def stack_at(self, mx, my, r):
        best = None
        for s in self.stacks:
            d = math.hypot(s.mx - mx, s.my - my)
            if s.checkers and d <= r and (best is None or d < best[0]):
                best = (d, s)
        return best[1] if best else None

    def height_at(self, mx, my, r=13.0):
        """top height of whatever is under a 26 mm disc at (mx, my) (crash check while carrying / lowering)"""
        h = 0.0
        for s in self.stacks:
            if s.checkers and math.hypot(s.mx - mx, s.my - my) < r + 13.0:
                h = max(h, M.CHECKER_H * len(s.checkers))
        return h

    def where(self, checker):
        for s in self.stacks:
            if checker in s.checkers:
                return s, s.checkers.index(checker)
        return None, None

class Twin:
    """Looks like a serial port to esp_link.EspLink (write / read / close)."""
    AXES = ('x', 'y', 'w')

    def __init__(self, world=None, speed=1.0, seed=1):
        self.speed = speed
        self.rng = random.Random(seed)
        self.world = world or World(rng=self.rng)
        self.cal = M.load_cal()
        self.real0 = time.time(); self.vt = 0.0       # virtual time (s)
        self.out = b''
        self.lock = threading.Lock()
        mA = {'x': 900, 'y': 900, 'w': 600}; rated = {'x': 2000, 'y': 2000, 'w': 700}
        self.ax = {n: dict(n=n, pos=0.0, p0=0.0, p1=0.0, t0=0.0, T=0.0, on=1, sleep=0, mA=mA[n], rated=rated[n], inv=0,
                           spd=3200, acc=6400, jerk=0, hold=50, cpct=30, mt=25.0, warm=0, hot=0, lost=1, homed=0,
                           t_act=0.0)
                   for n in self.AXES}
        self.stream, self.wd, self.idle = 0, 0, 60
        self.t_stream = 0.0; self.t_cmd_real = time.time(); self.wdtrip = 0
        self.servo, self.servo0, self.servo1, self.servo_t0, self.servo_T = 1500.0, 1500.0, 1500.0, 0.0, 0.0
        self.servo_done_sent = True
        self.mag, self.mag_t_on, self.held, self.held_off = 0, 0.0, None, (0.0, 0.0)
        self.led_red = 0
        self.vbat = 15.6; self.vbat_state = 0
        self.queue, self.q_running, self.q_wait_until, self.q_done = [], False, 0.0, 0
        self.prof, self.saved, self.crashes = 'defaults', {}, 0
        self.limits = {'x': (0.0, 143.0), 'y': (0.0, 336.0)}
        self.home_switch = {'x': 0.0, 'y': 0.0}       # switch position in axis mm
        self.mag_hold_pct = 40
        self.log_lines = []

    # ------------------------------------------------------------ helpers
    def now(self):
        return self.vt

    def _say(self, s):
        self.out += (s + '\r\n').encode()
        self.log_lines.append((round(self.vt, 3), s))

    def _event(self, s):
        self._say('event ' + s)

    def spm(self, n):
        return {'x': self.cal['steps_per_mm_x'], 'y': self.cal['steps_per_mm_y'], 'w': self.cal['steps_per_deg_w']}[n]

    def pos(self, n, t=None):
        """axis position in steps at time t (trapezoid shape over the move duration)"""
        a = self.ax[n]
        t = self.vt if t is None else t
        if a['T'] <= 0 or t >= a['t0'] + a['T']:
            return a['p1']
        u = max(0.0, (t - a['t0']) / a['T'])
        f = u * u * 2 if u < 0.5 else 1 - (1 - u) ** 2 * 2          # smooth start and stop
        return a['p0'] + (a['p1'] - a['p0']) * f

    def running(self, n):
        a = self.ax[n]
        return a['T'] > 0 and self.vt < a['t0'] + a['T']

    def moving(self):
        return any(self.running(n) for n in self.AXES) or self.vt < self.servo_t0 + self.servo_T

    def _start(self, n, target, v=None, acc=None, T=None):
        a = self.ax[n]
        p = self.pos(n)
        a['p0'], a['p1'], a['t0'] = p, float(target), self.vt
        if T is None:
            T = M.move_time(target - p, v or a['spd'], acc or a['acc'], a['jerk'])
        a['T'] = T
        a['t_act'] = self.vt
        self._wake(a)

    def _wake(self, a):
        a['t_act'] = self.vt
        if a['sleep']:
            a['on'], a['sleep'] = 1, 0
            self._event('idle %s: driver back on' % a['n'])

    def _halt_all(self):
        for n in self.AXES:
            p = self.pos(n)
            self.ax[n].update(p0=p, p1=p, T=0.0, pos=p)

    def magnet_xy(self):
        ax = self.pos('x') / self.spm('x'); ay = self.pos('y') / self.spm('y')
        return M.axis_to_magnet(ax, ay, self.cal)

    def face_h(self, us=None):
        """magnet face height from the servo pulse (inverse of machine.servo_us)"""
        us = self.servo_now() if us is None else us
        deg = (us - self.cal['servo_us_level']) / (self.cal['servo_sign'] * self.cal['servo_us_per_deg'])
        deg = max(-89.0, min(89.0, deg))
        return M.H_MID + M.R_ARM * math.sin(math.radians(deg))

    def servo_now(self):
        if self.servo_T <= 0 or self.vt >= self.servo_t0 + self.servo_T:
            return self.servo1
        u = (self.vt - self.servo_t0) / self.servo_T
        return self.servo0 + (self.servo1 - self.servo0) * u

    def wrist_deg(self):
        return self.pos('w') / self.spm('w')

    # ------------------------------------------------------------ physics, timers, queue
    def _advance(self, dt):
        end = self.vt + dt
        while self.vt < end - 1e-12:
            h = min(0.005, end - self.vt)
            self._tick(h)
            self.vt += h

    def _tick(self, h):
        mx, my = self.magnet_xy()
        face = self.face_h()
        # held checker follows the magnet; the wrist turns it
        if self.held is not None:
            c = self.held
            c.hx, c.hy = mx + self.held_off[0], my + self.held_off[1]
        # crash: the magnet (or the held checker) runs into a stack while X/Y move low
        if any(self.running(n) for n in ('x', 'y')):
            bottom = face - (M.CHECKER_H if self.held is not None else 0.0)
            under = self.world.height_at(mx, my, 13.0 if self.held is not None else 8.0)
            if bottom < under - 1.0:
                self._halt_all(); self.crashes += 1
                self.ax['x']['lost'] = self.ax['y']['lost'] = 1
                self._event('CRASH x: magnet hit a stack (face %.1f mm, stack top %.1f mm) - all motors stopped' % (face, under))
                self._queue_stop()
        # magnet catches the top checker it touches
        if self.mag and self.held is None and self.vt - self.mag_t_on >= self.cal['mag_grab'] * 0.5:
            s = self.world.stack_at(mx, my, self.cal['capture_r'])
            if s is not None and abs(face - M.CHECKER_H * len(s.checkers)) <= 1.5:
                c = s.checkers.pop()
                self.held, self.held_off = c, (s.mx - mx, s.my - my)
                c.hx, c.hy = s.mx, s.my
                c.w0 = self.wrist_deg(); c.a0 = c.angle
                if not s.checkers:
                    self.world.stacks.remove(s)
        if self.held is not None:
            self.held.angle = (self.held.a0 + self.wrist_deg() - self.held.w0) % 360.0
        # servo done
        if not self.servo_done_sent and self.vt >= self.servo_t0 + self.servo_T:
            self.servo_done_sent = True
            self._event('servo done')
        # idle switch-off, heat (1 min demo time constant), battery
        for a in self.ax.values():
            run = self.running(a['n'])
            if run:
                a['t_act'] = self.vt
            elif self.idle and a['on'] and self.vt - a['t_act'] > self.idle:
                a['on'], a['sleep'] = 0, 1
                self._event('idle %s: not used for %d s, driver off' % (a['n'], self.idle))
            i = 0 if not a['on'] else a['mA'] if run else a['mA'] * a['hold'] / 100
            a['mt'] += (25 + 80 * (i / a['rated']) ** 2 - a['mt']) * h / 600.0
        self.vbat -= h * (0.0004 if self.moving() else 0.00005)
        if self.vbat < 14.8 and self.vbat_state == 0:
            self.vbat_state = 1; self._event('battery low (%.2f V)' % self.vbat)
        if self.vbat < 14.0 and self.vbat_state == 1:
            self.vbat_state = 2; self._halt_all(); self._queue_stop(); self._event('battery stop (%.2f V)' % self.vbat)
        # queue
        if self.q_running and self.vt >= self.q_wait_until and not self.moving() and not self._mag_settling():
            if self.queue:
                line = self.queue.pop(0)
                self.q_done += 1
                if line.startswith('wait '):
                    self.q_wait_until = self.vt + float(line.split()[1]) / 1000.0
                else:
                    self._cmd(line, from_queue=True)
            else:
                self.q_running = False
                self._event('q done %d' % self.q_done)
        # stream
        if self.stream and (self.vt - self.t_stream) * 1000 >= self.stream * self.speed:
            self.t_stream = self.vt
            self._say(self._json())

    def _mag_settling(self):
        return (self.mag and self.vt - self.mag_t_on < self.cal['mag_grab']) or \
               (not self.mag and self.vt - getattr(self, 'mag_t_off', -9) < self.cal['mag_release'])

    def _queue_stop(self):
        if self.q_running or self.queue:
            self.q_running = False; self.queue = []
            self._event('q stopped')

    def _drop(self):
        """magnet off: the held checker falls from the face height onto whatever is below"""
        c, self.held = self.held, None
        if c is None:
            return
        fall = max(0.0, self.face_h() - M.CHECKER_H - self.world.height_at(c.hx, c.hy, 0.0))
        err = 0.6 + 0.15 * fall                                  # mm, grows with the drop height
        x = c.hx + self.rng.gauss(0, err); y = c.hy + self.rng.gauss(0, err)
        s = self.world.stack_at(x, y, 26.0)
        if s is not None:
            d = math.hypot(s.mx - x, s.my - y)
            if d <= 8.0:
                s.checkers.append(c); return                    # lands on the stack
            if d < 22.0:
                s.fallen = True; c.lid_up = False                # half on it: tips over
                self.world.stacks.append(Stack(x, y, [c])); return
        self.world.stacks.append(Stack(x, y, [c]))

    # ------------------------------------------------------------ status
    def _json(self):
        axs = []
        for n in self.AXES:
            a = self.ax[n]
            run = int(self.running(n))
            axs.append(dict(n=n, pos=int(round(self.pos(n))), tgt=int(round(a['p1'])), run=run, ok=1, on=a['on'],
                            mA=a['mA'], inv=a['inv'], sleep=a['sleep'], spd=a['spd'], acc=a['acc'], jerk=a['jerk'],
                            v=a['spd'] if run else 0, hold=a['hold'], mt=round(a['mt'], 1), warm=a['warm'], hot=a['hot'],
                            lost=a['lost'], cpct=a['cpct'], sgavg=200, sg=self.rng.randint(150, 260) if run else 0,
                            cs=20 if a['on'] else 0, otpw=0, ot=0, s2g=0, ol=0, temp=0, homed=a['homed']))
        return json.dumps(dict(t=int(self.vt * 1000), wd=self.wd, wdtrip=self.wdtrip, idle=self.idle * 1000,
                               heap=231000, heapmin=226500, heapsize=327680, loop=68000, ctemp=38.5,
                               vbat=round(self.vbat, 2), vbatavg=round(self.vbat, 2), drive=1, busy='', prof=self.prof,
                               crashes=self.crashes, warn=70, limit=90, servo=int(round(self.servo_now())), mag=self.mag,
                               led=self.led_red, qlen=len(self.queue), ax=axs), separators=(',', ':'))

    # ------------------------------------------------------------ serial-port interface
    def write(self, data):
        with self.lock:
            for line in data.decode().splitlines():
                self.t_cmd_real = time.time()
                self._cmd(line.strip().lower())

    def read(self, n):
        time.sleep(0.02)
        with self.lock:
            real = time.time()
            self._advance((real - self.real0) * self.speed - self.vt)
            if self.wd and not self.wdtrip and (real - self.t_cmd_real) * 1000 > self.wd:   # real time
                for a in self.AXES:
                    p = self.pos(a); self.ax[a].update(p0=p, p1=p, T=0.0)
                self.wdtrip = 1; self._queue_stop(); self._event('watchdog: no ping, motors stopped')
            d, self.out = self.out[:n], self.out[n:]
        return d

    def close(self):
        pass

    # ------------------------------------------------------------ Python API (tests, run program in twin mode)
    def press_start(self):
        with self.lock:
            self._event('start')

    def set_battery(self, v):
        with self.lock:
            self.vbat = v

    def scan(self, noise=0.6):
        """what a camera scan would report: marks {id: (mx, my)} and top checkers [(mx, my, colour, tag, levels, angle)]"""
        with self.lock:
            g = lambda: self.rng.gauss(0, noise)
            marks = {mid: (lambda p: (p[0] + g(), p[1] + g()))(self.world.sheet.to_machine(*xy)) for mid, xy in F.MARKS.items()}
            tops = [(s.mx + g(), s.my + g(), s.checkers[-1].colour, s.checkers[-1].tag, len(s.checkers),
                     s.checkers[-1].angle) for s in self.world.stacks if s.checkers]
            return marks, tops

    def score(self, goals):
        """goals: [(checker, cell, level)] -> (placed, total, problems). ETZ 2.4 rules, true sheet position."""
        ok, problems = 0, []
        for c, cell, level in goals:
            s, i = self.world.where(c)
            if s is None:
                problems.append('%s: not on the field (held?)' % c.colour); continue
            X, Y = self.world.sheet.to_field(s.mx, s.my)
            good = F.placed_in(X, Y, cell) and i == level and c.lid_up and not s.fallen
            ok += good
            if not good:
                problems.append('%s %s: at (%.1f, %.1f) level %d, wanted %s level %d' % (
                    c.colour, c.tag, X, Y, i, F.cell_name(cell), level))
        return ok, len(goals), problems

    # ------------------------------------------------------------ commands (firmware protocol)
    def _cmd(self, line, from_queue=False):
        p = line.split(); r = self._say
        if not p:
            return
        c, a = p[0], p[1:]
        one = self.ax.get(a[0]) if a else None
        try:
            if c == 'ping': self.wdtrip = 0; r('pong'); return
            if c == 'stream': self.stream = int(a[0]); r('ok stream %s' % a[0]); return
            if c == 'wd': self.wd = int(a[0]); self.wdtrip = 0; r('ok wd %s' % a[0]); return
            if c == 'echo': r('ok echo %s' % a[0]); return
            if c == 'json': r(self._json()); return
            if c == 'stop':
                self._queue_stop()
                for n in self.AXES:
                    q = self.pos(n); self._start(n, q, T=0.0)
                r('ok stop'); return
            if c == 'q':
                if not a: r('err q <command>'); return
                self.queue.append(' '.join(a)); r('ok q %d' % len(self.queue)); return
            if c == 'qrun': self.q_running, self.q_done = True, 0; r('ok qrun %d' % len(self.queue)); return
            if c == 'qclear': self.queue = []; self.q_running = False; r('ok qclear'); return
            if c == 'qstat': r('ok qstat %d %s' % (len(self.queue), 'running' if self.q_running else 'idle')); return
            if c == 'idle': self.idle = int(a[0]); r('ok idle %s' % a[0]); return
            if c in ('speed', 'accel', 'jerk', 'crash'):
                key = {'speed': 'spd', 'accel': 'acc', 'jerk': 'jerk', 'crash': 'cpct'}[c]
                for x in self.ax.values():
                    if not one or x is one: x[key] = int(float(a[-1]))
                r('ok %s %s %s' % (c, one['n'] if one else 'all', a[-1])); return
            if c == 'led':
                self.led_red = int(a[-1]); r('ok led red %d' % self.led_red); return
            if c == 'servo':
                us = max(500.0, min(2500.0, float(a[0])))
                self.servo0, self.servo1, self.servo_t0 = self.servo_now(), us, self.vt
                self.servo_T = M.lift_time(self.face_h(self.servo0), self.face_h(us), self.cal)
                self.servo_done_sent = False
                r('ok servo %d' % us); return
            if c == 'mag':
                if a[0] == 'on':
                    self.mag, self.mag_t_on = 1, self.vt
                else:
                    self.mag = 0; self.mag_t_off = self.vt; self._drop()
                r('ok mag %s' % a[0]); return
            if self.vbat_state == 2 and c in ('gomm', 'linemm', 'line', 'm', 'r', 'g', 'all', 'home', 'wrist'):
                r('err battery'); return
            if c == 'home':
                names = ('x', 'y') if (not a or a[0] == 'all') else (a[0],)
                for n in names:
                    x = self.ax[n]
                    T = M.move_time(self.pos(n), 2000.0, 6400.0) + 0.6        # search, back off, slow touch
                    self._start(n, 0.0, T=T)
                    x.update(homed=1, lost=0)
                r('ok home %s' % ('all' if len(names) > 1 else names[0])); return
            if c == 'gomm':
                n, mm = a[0], float(a[1])
                if n in self.limits and self.ax[n]['homed'] and not (self.limits[n][0] - 1e-6 <= mm <= self.limits[n][1] + 1e-6):
                    r('err limit %s' % n); return
                self._start(n, mm * self.spm(n)); r('ok gomm %s' % n); return
            if c == 'wrist':
                d = float(a[0])
                cur = self.wrist_deg()
                tgt = cur + ((d - cur + 180.0) % 360.0 - 180.0)            # shortest way to the absolute angle
                self._start('w', tgt * self.spm('w'), v=self.ax['w']['spd'], acc=self.ax['w']['acc'])
                r('ok wrist %s' % a[0]); return
            if c in ('linemm', 'line'):
                X, Y = float(a[0]), float(a[1])
                if c == 'line':
                    X, Y = X / self.spm('x'), Y / self.spm('y')
                for n, v in (('x', X), ('y', Y)):
                    if self.ax[n]['homed'] and not (self.limits[n][0] - 1e-6 <= v <= self.limits[n][1] + 1e-6):
                        r('err limit %s' % n); return
                dx = X - self.pos('x') / self.spm('x'); dy = Y - self.pos('y') / self.spm('y')
                cal = dict(self.cal, speed_x=self.ax['x']['spd'], speed_y=self.ax['y']['spd'],
                           accel_x=self.ax['x']['acc'], accel_y=self.ax['y']['acc'],
                           jerk_ms=max(self.ax['x']['jerk'], self.ax['y']['jerk']))
                T = M.line_time(dx, dy, cal)
                self._start('x', X * self.spm('x'), T=T); self._start('y', Y * self.spm('y'), T=T)
                r('ok %s' % c); return
            if c == 'all':
                for n in self.AXES: self._start(n, self.ax[n]['p1'] + float(a[0]) * STEPS_PER_REV)
                r('ok all'); return
            if c == 'mem': r('  RAM free 231000 bytes of 327680 (twin)'); return
            if c == 'status':
                for n in self.AXES: r('[%s] OK (twin) pos %d homed %d' % (n, self.pos(n), self.ax[n]['homed']))
                return
            if c == 'heat':
                for x in self.ax.values(): r('  [%s] motor ~%.1f C (twin)' % (x['n'], x['mt']))
                r('ok heat'); return
            if c == 'selftest':
                for t in ('drive power on', 'battery %.2f V' % self.vbat, '[x] driver answers', '[y] driver answers', '[w] driver answers'):
                    r('  PASS  ' + t)
                r('ok selftest PASS (0 warnings)'); return
            if c == 'log': r('  boot 1  0.5 s  boot: power on (twin)'); r('ok log'); return
            if c == 'save':
                n = a[0] if a else 'boot'; self.saved[n] = {k: dict(v) for k, v in self.ax.items()}; self.prof = n
                r('ok save ' + n); return
            if c == 'load':
                n = a[0] if a else 'boot'
                if n not in self.saved: r('err no profile %s (see: profiles)' % n); return
                for k, v in self.saved[n].items():
                    for f in ('spd', 'acc', 'jerk', 'cpct', 'mA', 'hold', 'inv'): self.ax[k][f] = v[f]
                self.prof = n; r('ok load ' + n); return
            if c == 'profiles':
                for n in self.saved: r('  ' + n)
                r('ok profiles (now: %s)' % self.prof); return
            if c == 'defaults': self.prof = 'defaults'; r('ok defaults'); return
            if c == 'test': r('ok test'); return
            x = one
            if not x: r('err unknown command or axis - type help'); return
            n = x['n']
            if c == 'r': self._start(n, x['p1'] + float(a[1]) * STEPS_PER_REV); r('ok r ' + n); return
            if c == 'm': self._start(n, x['p1'] + int(a[1])); r('ok m ' + n); return
            if c == 'g': self._start(n, int(a[1])); r('ok g ' + n); return
            if c == 'zero': x.update(p0=0.0, p1=0.0, T=0.0, lost=0); r('ok zero ' + n); return
            if c == 'cur': x['mA'] = min(int(a[1]), x['rated']); r('ok cur %s %s' % (n, x['mA'])); return
            if c == 'hold': x['hold'] = int(a[1]); r('ok hold %s %s' % (n, a[1])); return
            if c == 'on': x.update(on=1, sleep=0); r('ok on ' + n); return
            if c == 'off': x.update(on=0, sleep=0, lost=1); r('ok off ' + n); return
            if c == 'dir': x['inv'] ^= 1; r('ok dir %s %d' % (n, x['inv'])); return
            if c == 'tune': r('ok tune %s speed 11200 accel 44800 (twin)' % n); return
            r('err unknown command - type help')
        except (IndexError, ValueError) as e:
            r('err %s: %s' % (c, e))

# ---------------------------------------------------------------- self-test
def _wait(tw, cond, limit=60.0):
    t_end = tw.vt + limit
    while tw.vt < t_end:
        tw._advance(0.01)
        if cond():
            return True
    return False

def self_test():
    ok = True
    def check(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print('  %-58s %s' % (name, 'ok' if cond else 'FAILED'))
    cal = M.load_cal()
    tw = Twin(speed=1.0)
    tw.world.put_cell('Д1', 'red')
    tw.world.put_cell('Б3', 'blue'); tw.world.put_cell('Б3', 'green')        # a stack of 2 in Б3
    tw._cmd('home all'); _wait(tw, lambda: not tw.moving())
    check('homing: both axes homed, position 0', tw.ax['x']['homed'] and tw.pos('x') == 0)
    tw._cmd('gomm x 500'); check('soft limit refuses x 500 mm', tw.out.decode().strip().endswith('err limit x'))
    tw.out = b''
    # timing: a line move lasts what machine.line_time says
    for n in ('x', 'y'):
        tw.ax[n]['spd'], tw.ax[n]['acc'] = int(cal['speed_x']), int(cal['accel_x'])
    t0 = tw.vt; tw._cmd('linemm 100 200'); _wait(tw, lambda: not tw.moving())
    want = M.line_time(100, 200, dict(cal, jerk_ms=0))
    check('line 100/200 mm takes %.2f s (machine.py %.2f s)' % (tw.vt - t0, want), abs((tw.vt - t0) - want) < 0.05 * want + 0.02)
    # pick Д1 and place it in Д5
    def goto_field(cell, h):
        mx, my = tw.world.sheet.to_machine(*F.cell_centre(*F.parse_cell(cell)))
        ax, ay = M.magnet_to_axis(mx, my, cal)
        tw._cmd('servo %d' % M.servo_us(cal['h_carry'], cal)); _wait(tw, lambda: not tw.moving())
        tw._cmd('linemm %.2f %.2f' % (ax, ay)); _wait(tw, lambda: not tw.moving())
        tw._cmd('servo %d' % M.servo_us(h, cal)); _wait(tw, lambda: not tw.moving())
    red = tw.world.stacks[0].checkers[0]
    goto_field('Д1', M.stack_top(1)); tw._cmd('mag on'); _wait(tw, lambda: tw.held is not None, 1.0)
    check('magnet picks the red checker in Д1', tw.held is red)
    goto_field('Д5', M.stack_top(0) + 5.0); tw._cmd('mag off')
    placed, total, probs = tw.score([(red, F.parse_cell('Д5'), 0)])
    check('red placed in Д5 (within 10 mm)', placed == 1)
    # take the top of the Б3 stack and put it on Д5
    green = None
    for s in tw.world.stacks:
        if len(s.checkers) == 2: green = s.checkers[-1]
    goto_field('Б3', M.stack_top(2)); tw._cmd('mag on'); _wait(tw, lambda: tw.held is not None, 1.0)
    check('top of the Б3 stack picked (green)', tw.held is green)
    goto_field('Д5', M.stack_top(1) + 0.5); tw._cmd('mag off')
    check('green stacked on red in Д5 (level 1)', tw.score([(green, F.parse_cell('Д5'), 1)])[0] == 1)
    # crash: moving low over a stack
    tw._cmd('servo %d' % M.servo_us(5.0, cal)); _wait(tw, lambda: not tw.moving())
    mx, my = tw.world.sheet.to_machine(*F.cell_centre(*F.parse_cell('Д5')))
    ax, ay = M.magnet_to_axis(mx, my, cal)
    tw.out = b''; tw._cmd('linemm %.2f %.2f' % (ax, ay - 40)); _wait(tw, lambda: not tw.moving())
    tw._cmd('linemm %.2f %.2f' % (ax, ay)); _wait(tw, lambda: not tw.moving())
    check('moving low into a stack -> CRASH event', 'CRASH' in tw.out.decode())
    # queue
    tw2 = Twin(); tw2._cmd('home all'); _wait(tw2, lambda: not tw2.moving())
    for q in ('q gomm x 50', 'q wait 300', 'q linemm 20 100', 'q servo 1700', 'qrun'):
        tw2._cmd(q)
    _wait(tw2, lambda: not tw2.q_running, 30)
    check('queue runs 4 steps and reports q done', 'q done 4' in tw2.out.decode() and abs(tw2.pos('y') / 80 - 100) < 0.01)
    # battery
    tw2.out = b''; tw2.vbat = 14.003; _wait(tw2, lambda: tw2.vbat_state == 2, 400)
    tw2._cmd('gomm x 10')
    check('battery below 14.0 V -> battery stop, moves refused', 'battery stop' in tw2.out.decode() and tw2.out.decode().strip().endswith('err battery'))
    print('twin self-test:', 'PASS' if ok else 'FAIL')
    return ok

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--test' in sys.argv:
        sys.exit(0 if self_test() else 1)
    print(__doc__)
