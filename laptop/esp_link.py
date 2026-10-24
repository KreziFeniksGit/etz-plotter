"""
Link to the ESP32 firmware (v2) over the USB serial port.
- opens the port WITHOUT resetting the board (DTR / RTS held low), switches the console to program mode
  (echo 0), asks for a status line every STREAM_MS (stream) and arms the firmware watchdog (wd): the laptop sends a
  ping every PING_MS; if the laptop dies or the cable is pulled, the motors stop within WD_MS.
- a background thread reads lines: '{...}' = status (kept in .state), everything else goes to the log queue.
FakeEsp: a stand-in board for trying the app without hardware (esp_dashboard.py --demo).
"""
import json, queue, threading, time

STREAM_MS, PING_MS, WD_MS = 150, 400, 1500
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
    """Behaves like the firmware for the commands the dashboard uses: motors move at the set speed."""
    STEPS = 3200

    def __init__(self):
        self.ax = {n: dict(n=n, pos=0.0, tgt=0, ok=1, on=1, mA=m, inv=0) for n, m in (('x', 900), ('y', 900), ('w', 600))}
        self.spd, self.acc, self.stream, self.wd = 3200, 6400, 0, 0
        self.out = b''
        self.t_last = time.time(); self.t_stream = 0; self.t_cmd = time.time(); self.wdtrip = 0
        self.lock = threading.Lock()

    def _step(self):
        now = time.time(); dt = now - self.t_last; self.t_last = now
        for a in self.ax.values():
            d = a['tgt'] - a['pos']
            if abs(d) > 0.5 and a['on']:
                a['pos'] += max(-self.spd * dt, min(self.spd * dt, d))
        if self.stream and (now - self.t_stream) * 1000 >= self.stream:
            self.t_stream = now; self.out += (self._json() + '\r\n').encode()
        if self.wd and not self.wdtrip and (now - self.t_cmd) * 1000 > self.wd:
            for a in self.ax.values(): a['tgt'] = round(a['pos'])
            self.wdtrip = 1; self.out += b'event watchdog: no ping, motors stopped\r\n'

    def _json(self):
        import random
        axs = []
        for a in self.ax.values():
            run = int(abs(a['tgt'] - a['pos']) > 0.5 and a['on'])
            axs.append(dict(n=a['n'], pos=int(a['pos']), tgt=a['tgt'], run=run, ok=a['ok'], on=a['on'], mA=a['mA'], inv=a['inv'],
                            sg=random.randint(150, 260) if run else 0, cs=20 if a['on'] else 0, otpw=0, ot=0, s2g=0, ol=0, temp=0))
        return json.dumps(dict(t=int(time.time() * 1000) % 10 ** 9, spd=self.spd, acc=self.acc, wd=self.wd, wdtrip=self.wdtrip, ax=axs),
                          separators=(',', ':'))

    def write(self, data):
        with self.lock:
            for line in data.decode().splitlines():
                self._cmd(line.strip().lower())

    def _cmd(self, line):
        self.t_cmd = time.time()
        p = line.split(); r = lambda s: self.__dict__.__setitem__('out', self.out + (s + '\r\n').encode())
        if not p: return
        c, a = p[0], p[1:]
        if c == 'ping': self.wdtrip = 0; r('pong'); return
        if c == 'stream': self.stream = int(a[0]); r('ok stream %s' % a[0]); return
        if c == 'wd': self.wd = int(a[0]); self.wdtrip = 0; r('ok wd %s' % a[0]); return
        if c == 'echo': r('ok echo %s' % a[0]); return
        if c == 'json': r(self._json()); return
        if c == 'stop':
            for x in self.ax.values(): x['tgt'] = round(x['pos'])
            r('ok stop'); return
        if c == 'speed': self.spd = int(a[0]); r('ok speed %s' % a[0]); return
        if c == 'accel': self.acc = int(a[0]); r('ok accel %s' % a[0]); return
        if c == 'status': r('[demo] all drivers OK'); return
        if c == 'test': r('ok test'); return
        if c == 'all':
            for x in self.ax.values(): x['tgt'] += round(float(a[0]) * self.STEPS)
            r('ok all'); return
        x = self.ax.get(a[0]) if a else None
        if not x: r('err unknown command or axis - type help'); return
        if c == 'r': x['tgt'] += round(float(a[1]) * self.STEPS); r('ok r ' + a[0]); return
        if c == 'm': x['tgt'] += int(a[1]); r('ok m ' + a[0]); return
        if c == 'g': x['tgt'] = int(a[1]); r('ok g ' + a[0]); return
        if c == 'zero': x['pos'] = 0.0; x['tgt'] = 0; r('ok zero ' + a[0]); return
        if c == 'cur': x['mA'] = int(a[1]); r('ok cur %s %s' % (a[0], a[1])); return
        if c == 'on': x['on'] = 1; r('ok on ' + a[0]); return
        if c == 'off': x['on'] = 0; x['tgt'] = round(x['pos']); r('ok off ' + a[0]); return
        if c == 'dir': x['inv'] ^= 1; r('ok dir %s %d' % (a[0], x['inv'])); return
        r('err unknown command - type help')

    def read(self, n):
        time.sleep(0.02)
        with self.lock:
            self._step()
            d, self.out = self.out[:n], self.out[n:]
        return d

    def close(self):
        pass
