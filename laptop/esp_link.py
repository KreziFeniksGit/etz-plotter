"""
Link to the ESP32 firmware (v4) over the USB serial port.
- opens the port WITHOUT resetting the board (DTR / RTS held low), switches the console to program mode
  (echo 0), asks for a status line every STREAM_MS (stream) and arms the firmware watchdog (wd): the laptop sends a
  ping every PING_MS; if the laptop dies or the cable is pulled, the motors stop within WD_MS.
- a background thread reads lines: '{...}' = status (kept in .state), everything else goes to the log queue.
FakeEsp: the digital twin (twin.py) as a stand-in board (esp_dashboard.py --demo, run.py --twin).
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
    def connect(self, port, fake=False, speed=1.0):
        if fake:
            self.ser = FakeEsp(speed)
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
# The digital twin (twin.py) behaves like the firmware and simulates the plotter and the field.
def FakeEsp(speed=1.0):
    from twin import Twin
    return Twin(speed=speed)

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
