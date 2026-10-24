"""
Link to the ESP32 firmware (v4) over the USB serial port.
- opens the port WITHOUT resetting the board (DTR / RTS held low), switches the console to program mode
  (echo 0), asks for a status line every STREAM_MS (stream) and arms the firmware watchdog (wd): the laptop sends a
  ping every PING_MS; if the laptop dies or the cable is pulled, the motors stop within WD_MS.
- a background thread reads lines: '{...}' = status (kept in .state), everything else goes to the log queue.
FakeEsp: a stand-in board for trying the app without hardware (esp_dashboard.py --demo).
"""
import json, queue, threading, time

STREAM_MS, PING_MS, WD_MS = 250, 400, 1500
ESP_HINTS = ('CH34', 'CP210', 'USB-SERIAL', 'USB SERIAL', 'UART', 'ESP32', 'JTAG')

def list_ports():
    """[(device, description)], the likely ESP32 port first"""
    from serial.tools import list_ports as lp
    ports = [(p.device, p.description or '') for p in lp.comports()]
    return sorted(ports, key=lambda p: not any(h in p[1].upper() for h in ESP_HINTS))

class EspLink:
    def __init__(self):
        self.ser = None
        self.state = None          # last status (dict from the firmware's json line)
        self.state_time = 0.0
        self.log = queue.Queue()   # (kind, text): kind 'rx' / 'tx' / 'info' / 'err'
        self._stop = threading.Event()
        self._lock = threading.Lock()

    # ------------------------------------------------------------ connection
    def connect(self, port, fake=False):
        if fake:
            self.ser = FakeEsp()
        else:
            import serial
            s = serial.Serial()
            s.port, s.baudrate, s.timeout = port, 115200, 0.1
            s.dtr = False; s.rts = False          # keep the ESP32 running (these lines reset it on the DevKit)
            s.open()
            self.ser = s
        self._stop.clear()
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._pinger, daemon=True).start()
        time.sleep(0.2)
        for c in ('echo 0', 'stream %d' % STREAM_MS, 'wd %d' % WD_MS):
            self.send(c)
        self.log.put(('info', 'connected to %s' % ('demo board' if fake else port)))

    def disconnect(self):
        if not self.ser:
            return
        try:
            for c in ('wd 0', 'stream 0', 'echo 1'):
                self.send(c)
            time.sleep(0.1)
        except Exception:
            pass
        self._stop.set()
        time.sleep(0.15)
        try:
            self.ser.close()
        except Exception:
            pass
        self.ser = None
        self.state = None
        self.log.put(('info', 'disconnected'))

    @property
    def connected(self):
        return self.ser is not None

    def alive(self):
        """seconds since the last status line (None = never)"""
        return None if not self.state_time else time.time() - self.state_time

    def send(self, line, quiet=False):
        if not self.ser:
            return
        with self._lock:
            self.ser.write((line.strip() + '\n').encode())
        if not quiet:
            self.log.put(('tx', line.strip()))

    # ------------------------------------------------------------ threads
    def _reader(self):
        buf = b''
        while not self._stop.is_set():
            try:
                data = self.ser.read(512)
            except Exception as e:
                self.log.put(('err', 'serial port lost: %s' % e)); self.ser = None; return
            if not data:
                continue
            buf += data
            while b'\n' in buf:
                raw, buf = buf.split(b'\n', 1)
                line = raw.decode(errors='replace').strip().lstrip('> ').strip()
                if not line:
                    continue
                if line.startswith('{'):
                    try:
                        self.state = json.loads(line); self.state_time = time.time()
                    except ValueError:
                        self.log.put(('rx', line))
                elif line != 'pong':
                    self.log.put(('rx', line))

    def _pinger(self):
        while not self._stop.is_set():
            try:
                self.send('ping', quiet=True)
            except Exception:
                pass
            self._stop.wait(PING_MS / 1000)

# ---------------------------------------------------------------- demo board (no hardware)
class FakeEsp:
    """Behaves like the firmware (v4) for the commands the dashboard uses: motors move at their own speed,
    a simple heat model, idle switch-off, watchdog, line moves, profiles in memory."""
    STEPS = 3200

    def __init__(self):
        self.ax = {n: dict(n=n, pos=0.0, tgt=0, ok=1, on=1, mA=m, inv=0, sleep=0, t_act=time.time(), spd=3200, acc=6400,
                           jerk=0, hold=50, mt=25.0, warm=0, hot=0, lost=0, cpct=30, rated=r, lv=0.0, lv_line=0)
                   for n, m, r in (('x', 900, 2000), ('y', 900, 2000), ('w', 600, 700))}
        self.stream, self.wd, self.idle = 0, 0, 60000
        self.t0 = time.time()
        self.prof, self.saved, self.crashes = 'defaults', {}, 0
        self.out = b''
        self.t_last = time.time(); self.t_stream = 0; self.t_cmd = time.time(); self.wdtrip = 0
        self.lock = threading.Lock()

    def _say(self, s):
        self.out += (s + '\r\n').encode()

    def _step(self):
        now = time.time(); dt = now - self.t_last; self.t_last = now
        for a in self.ax.values():
            d = a['tgt'] - a['pos']
            moving = abs(d) > 0.5 and a['on']
            a['lv'] = a['lv_line'] if (moving and a['lv_line']) else a['spd']
            if moving:
                a['pos'] += max(-a['lv'] * dt, min(a['lv'] * dt, d)); a['t_act'] = now
            else:
                a['lv_line'] = 0
                if self.idle and a['on'] and (now - a['t_act']) * 1000 > self.idle:     # idle timer, like the firmware
                    a['on'], a['sleep'] = 0, 1
                    self._say('event idle %s: not used for %d s, driver off' % (a['n'], self.idle // 1000))
            i = 0 if not a['on'] else a['mA'] if moving else a['mA'] * a['hold'] / 100
            steady = 80 * (i / a['rated']) ** 2
            a['mt'] += (25 + steady - a['mt']) * dt / 60     # demo: 1 min time constant so it can be seen
        if self.stream and (now - self.t_stream) * 1000 >= self.stream:
            self.t_stream = now; self._say(self._json())
        if self.wd and not self.wdtrip and (now - self.t_cmd) * 1000 > self.wd:
            for a in self.ax.values(): a['tgt'] = round(a['pos'])
            self.wdtrip = 1; self._say('event watchdog: no ping, motors stopped')

    def _json(self):
        import random
        axs = []
        for a in self.ax.values():
            run = int(abs(a['tgt'] - a['pos']) > 0.5 and a['on'])
            axs.append(dict(n=a['n'], pos=int(a['pos']), tgt=a['tgt'], run=run, ok=a['ok'], on=a['on'], mA=a['mA'], inv=a['inv'],
                            sleep=a['sleep'], spd=a['spd'], acc=a['acc'], jerk=a['jerk'], v=int(a['lv']) if run else 0,
                            hold=a['hold'], mt=round(a['mt'], 1), warm=a['warm'], hot=a['hot'], lost=a['lost'], cpct=a['cpct'],
                            sgavg=200, sg=random.randint(150, 260) if run else 0, cs=20 if a['on'] else 0,
                            otpw=0, ot=0, s2g=0, ol=0, temp=0))
        return json.dumps(dict(t=int((time.time() - self.t0) * 1000), wd=self.wd, wdtrip=self.wdtrip, idle=self.idle,
                               heap=231000 + random.randint(0, 2000), heapmin=226500, heapsize=327680,
                               loop=random.randint(65000, 71000), ctemp=38.5, vbat=15.6, drive=1, busy='',
                               prof=self.prof, crashes=self.crashes, warn=70, limit=90, ax=axs), separators=(',', ':'))

    def write(self, data):
        with self.lock:
            for line in data.decode().splitlines():
                self._cmd(line.strip().lower())

    def _wake(self, x):
        x['t_act'] = time.time()
        if x['sleep']:
            x['on'], x['sleep'] = 1, 0; self._say('event idle %s: driver back on' % x['n'])

    def _cmd(self, line):
        self.t_cmd = time.time()
        p = line.split(); r = self._say
        if not p: return
        c, a = p[0], p[1:]
        one = self.ax.get(a[0]) if a else None
        if c == 'ping': self.wdtrip = 0; r('pong'); return
        if c == 'stream': self.stream = int(a[0]); r('ok stream %s' % a[0]); return
        if c == 'wd': self.wd = int(a[0]); self.wdtrip = 0; r('ok wd %s' % a[0]); return
        if c == 'echo': r('ok echo %s' % a[0]); return
        if c == 'json': r(self._json()); return
        if c == 'stop':
            for x in self.ax.values(): x['tgt'] = round(x['pos'])
            r('ok stop'); return
        if c == 'idle': self.idle = int(a[0]) * 1000; r('ok idle %s' % a[0]); return
        if c in ('speed', 'accel', 'jerk', 'crash'):
            key = {'speed': 'spd', 'accel': 'acc', 'jerk': 'jerk', 'crash': 'cpct'}[c]
            for x in self.ax.values():
                if not one or x is one: x[key] = int(a[-1])
            r('ok %s %s %s' % (c, one['n'] if one else 'all', a[-1])); return
        if c == 'mem': r('  RAM free 231000 bytes of 327680 (demo board)'); return
        if c == 'status': r('[demo] all drivers OK'); return
        if c == 'heat':
            for x in self.ax.values(): r('  [%s] motor ~%.1f C (demo)' % (x['n'], x['mt']))
            r('ok heat'); return
        if c == 'selftest':
            for t in ('drive power on', 'battery 15.60 V', '[x] driver answers', '[y] driver answers', '[w] driver answers'):
                r('  PASS  ' + t)
            r('ok selftest PASS (0 warnings)'); return
        if c == 'log': r('  boot 1  0.5 s  boot: power on (demo)'); r('ok log'); return
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
        if c == 'all':
            for x in self.ax.values(): self._wake(x); x['tgt'] += round(float(a[0]) * self.STEPS)
            r('ok all'); return
        if c == 'line':
            X, Y = self.ax['x'], self.ax['y']
            dx, dy = abs(int(a[0]) - X['pos']), abs(int(a[1]) - Y['pos'])
            L = max(1.0, (dx * dx + dy * dy) ** 0.5)
            V = min(X['spd'] / max(dx / L, 1e-3), Y['spd'] / max(dy / L, 1e-3))
            for ax_, d, t in ((X, dx, int(a[0])), (Y, dy, int(a[1]))):
                self._wake(ax_); ax_['tgt'] = t; ax_['lv_line'] = max(1.0, V * d / L)
            r('ok line'); return
        x = one
        if not x: r('err unknown command or axis - type help'); return
        if c in ('r', 'm', 'g'): self._wake(x)
        if c in ('on', 'off'): x['sleep'] = 0; x['t_act'] = time.time()
        if c == 'r': x['tgt'] += round(float(a[1]) * self.STEPS); r('ok r ' + a[0]); return
        if c == 'm': x['tgt'] += int(a[1]); r('ok m ' + a[0]); return
        if c == 'g': x['tgt'] = int(a[1]); r('ok g ' + a[0]); return
        if c == 'zero': x['pos'] = 0.0; x['tgt'] = 0; x['lost'] = 0; r('ok zero ' + a[0]); return
        if c == 'cur': x['mA'] = min(int(a[1]), x['rated']); r('ok cur %s %s' % (a[0], x['mA'])); return
        if c == 'hold': x['hold'] = int(a[1]); r('ok hold %s %s' % (a[0], a[1])); return
        if c == 'on': x['on'] = 1; r('ok on ' + a[0]); return
        if c == 'off': x['on'] = 0; x['lost'] = 1; x['tgt'] = round(x['pos']); r('ok off ' + a[0]); return
        if c == 'dir': x['inv'] ^= 1; r('ok dir %s %d' % (a[0], x['inv'])); return
        if c == 'tune': r('ok tune %s speed 11200 accel 44800 (demo)' % a[0]); return
        r('err unknown command - type help')

    def read(self, n):
        time.sleep(0.02)
        with self.lock:
            self._step()
            d, self.out = self.out[:n], self.out[n:]
        return d

    def close(self):
        pass

# ---------------------------------------------------------------- quick check from a terminal
if __name__ == '__main__':
    # python esp_link.py          -> list ports;   python esp_link.py COM5   -> connect, show status, type commands
    # python esp_link.py demo     -> the same with the demo board
    import sys
    if len(sys.argv) < 2:
        for d, desc in list_ports(): print(d, ' ', desc)
        print('run again with the port, e.g.  python esp_link.py COM5   (or  demo)'); sys.exit()
    link = EspLink()
    link.connect(None if sys.argv[1] == 'demo' else sys.argv[1], fake=sys.argv[1] == 'demo')
    def show():
        while not link.log.empty():
            k, t = link.log.get(); print(('> ' if k == 'tx' else '  ') + t)
        s = link.state
        if s:
            print('  status: ' + '   '.join('%s pos %d %s%s' % (a['n'], a['pos'], 'OK' if a['ok'] else 'NO ANSWER',
                  ' moving' if a['run'] else ' sleeping' if a.get('sleep') else '' if a['on'] else ' off') for a in s['ax']))
        else:
            print('  no status line yet')
    time.sleep(0.6); show()
    print('type a command (e.g.  r x 1 ), Enter alone = refresh, q = quit')
    try:
        while True:
            c = input('cmd> ').strip()
            if c == 'q': break
            if c: link.send(c)
            time.sleep(0.4); show()
    finally:
        link.disconnect()
