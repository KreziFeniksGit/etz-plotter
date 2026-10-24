"""
ETZ plotter dashboard: live status of the ESP32 and the three drivers, manual control, protection, command log.
Run:   laptop\\.venv\\Scripts\\python laptop\\esp_dashboard.py          (with the ESP32 on USB, port marked UART)
       laptop\\.venv\\Scripts\\python laptop\\esp_dashboard.py --demo   (no hardware: a simulated board)
Close the PlatformIO serial monitor first - only one program can use the port.
"""
import sys, threading
import tkinter as tk
from tkinter import ttk
from esp_link import EspLink, list_ports

STEPS_PER_REV = 3200
AXES = (('x', 'X axis'), ('y', 'Y axis'), ('w', 'Wrist'))
GREEN, RED, GREY, AMBER, BLUE = '#2e9e44', '#d23b3b', '#9a9a9a', '#e0a020', '#cfd8ef'
CAMERA_INDEX = 1          # the USB webcam (0 = the laptop's own camera)

def spin(parent, lo, hi, inc, val, width=6):
    s = ttk.Spinbox(parent, from_=lo, to=hi, increment=inc, width=width)
    s.set(val)
    return s

class AxisPanel(ttk.LabelFrame):
    def __init__(self, master, app, key, title):
        super().__init__(master, text=title, padding=8)
        self.app, self.key = app, key
        self.drv = tk.Label(self, text='driver ?', fg='white', bg=GREY, width=14)
        self.drv.grid(row=0, column=0, columnspan=2, sticky='w')
        self.mov = tk.Label(self, text='', width=10)
        self.mov.grid(row=0, column=2, columnspan=2, sticky='e')
        self.pos = ttk.Label(self, text='pos -', font=('Segoe UI', 14, 'bold'))
        self.pos.grid(row=1, column=0, columnspan=4, sticky='w', pady=(6, 0))
        self.info = ttk.Label(self, text='', foreground='#555')
        self.info.grid(row=2, column=0, columnspan=4, sticky='w')
        self.heat = tk.Label(self, text='motor -', anchor='w')
        self.heat.grid(row=3, column=0, columnspan=4, sticky='we')
        ttk.Label(self, text='load').grid(row=4, column=0, sticky='w')
        self.load = ttk.Progressbar(self, maximum=510, length=160)
        self.load.grid(row=4, column=1, columnspan=3, sticky='we', pady=2)
        self.flags = tk.Label(self, text='', fg=RED)
        self.flags.grid(row=5, column=0, columnspan=4, sticky='w')
        b = ttk.Frame(self); b.grid(row=6, column=0, columnspan=4, pady=(6, 0))
        for i, (t, turns) in enumerate((('-1 turn', -1), ('-0.1', -0.1), ('+0.1', 0.1), ('+1 turn', 1))):
            ttk.Button(b, text=t, width=7, command=lambda v=turns: app.cmd('r %s %g' % (key, v))).grid(row=0, column=i, padx=1)
        c = ttk.Frame(self); c.grid(row=7, column=0, columnspan=4, pady=(4, 0))
        ttk.Button(c, text='Zero', width=6, command=lambda: app.cmd('zero ' + key)).grid(row=0, column=0, padx=1)
        self.onoff = ttk.Button(c, text='Off', width=6, command=self.toggle)
        self.onoff.grid(row=0, column=1, padx=1)
        ttk.Button(c, text='Reverse', width=8, command=lambda: app.cmd('dir ' + key)).grid(row=0, column=2, padx=1)
        ttk.Button(c, text='Tune', width=6, command=lambda: app.cmd('tune ' + key)).grid(row=0, column=3, padx=1)
        d = ttk.Frame(self); d.grid(row=8, column=0, columnspan=4, pady=(4, 0), sticky='w')
        ttk.Label(d, text='current mA').grid(row=0, column=0, sticky='w')
        self.cur = spin(d, 100, 2000, 50, 900 if key != 'w' else 600)
        self.cur.grid(row=0, column=1, padx=2)
        ttk.Label(d, text='hold %').grid(row=0, column=2)
        self.hold = spin(d, 0, 100, 10, 50, 4); self.hold.grid(row=0, column=3, padx=2)
        ttk.Button(d, text='Set', width=4, command=self.set_current).grid(row=0, column=4)
        ttk.Label(d, text='speed').grid(row=1, column=0, sticky='w')
        self.spd = spin(d, 50, 16000, 400, 3200); self.spd.grid(row=1, column=1, padx=2)
        ttk.Label(d, text='accel').grid(row=1, column=2)
        self.acc = spin(d, 100, 400000, 1600, 6400, 7); self.acc.grid(row=1, column=3, padx=2)
        ttk.Button(d, text='Set', width=4, command=self.set_motion).grid(row=1, column=4)
        ttk.Label(d, text='S-curve ms').grid(row=2, column=0, sticky='w')
        self.jerk = spin(d, 0, 500, 10, 0, 4); self.jerk.grid(row=2, column=1, padx=2, sticky='w')
        ttk.Label(d, text='crash %').grid(row=2, column=2)
        self.crash = spin(d, 0, 90, 5, 30, 4); self.crash.grid(row=2, column=3, padx=2, sticky='w')
        ttk.Button(d, text='Set', width=4, command=self.set_guard).grid(row=2, column=4)
        self.is_on = True
        self.synced = False       # boxes filled from the board once after connecting

    def toggle(self):
        self.app.cmd(('off ' if self.is_on else 'on ') + self.key)

    def set_current(self):
        self.app.cmd('cur %s %s' % (self.key, self.cur.get()))
        self.app.cmd('hold %s %s' % (self.key, self.hold.get()))

    def set_motion(self):
        self.app.cmd('speed %s %s' % (self.key, self.spd.get()))
        self.app.cmd('accel %s %s' % (self.key, self.acc.get()))

    def set_guard(self):
        self.app.cmd('jerk %s %s' % (self.key, self.jerk.get()))
        self.app.cmd('crash %s %s' % (self.key, self.crash.get()))

    def update_from(self, a, s):
        if a is None:
            self.drv.config(text='driver ?', bg=GREY); self.pos.config(text='pos -'); self.info.config(text='')
            self.mov.config(text='', bg='#f0f0f0'); self.flags.config(text=''); self.load['value'] = 0
            self.heat.config(text='motor -', bg='#f0f0f0'); self.synced = False
            return
        if not self.synced:
            for box, k in ((self.cur, 'mA'), (self.hold, 'hold'), (self.spd, 'spd'), (self.acc, 'acc'),
                           (self.jerk, 'jerk'), (self.crash, 'cpct')):
                if k in a:
                    box.set(a[k])
            self.synced = True
        ok = a['ok']
        self.drv.config(text='driver OK' if ok else 'NO ANSWER', bg=GREEN if ok else RED)
        sleep = a.get('sleep', 0)
        self.is_on = bool(a['on']) or bool(sleep)
        self.onoff.config(text='Off' if self.is_on else 'On')
        state = 'moving' if a['run'] else 'HOT' if a.get('hot') else 'sleeping' if sleep else 'free' if not a['on'] else 'holding'
        self.mov.config(text=state, bg=AMBER if a['run'] else RED if a.get('hot') else BLUE if sleep
                        else '#cccccc' if not a['on'] else '#bfe3c6')
        self.pos.config(text='pos %d  (%.3f turns)' % (a['pos'], a['pos'] / STEPS_PER_REV))
        self.info.config(text='target %d   %d mA   %s\nspeed now %d / max %s   accel %s   S-curve %s ms' % (
            a['tgt'], a['mA'], 'reversed' if a['inv'] else 'normal dir', a.get('v', 0), a.get('spd', '?'),
            a.get('acc', '?'), a.get('jerk', 0)))
        mt = a.get('mt')
        if mt is not None:
            warn, lim = s.get('warn', 70), s.get('limit', 90)
            col = '#f6c6c6' if mt >= lim - 5 else '#f8e3a8' if mt >= warn - 10 else '#d9f0dc'
            self.heat.config(text='motor about %.0f C  (warn %d, off %d)  standing current %s%%%s' % (
                mt, warn, lim, a.get('hold', '?'), '  LOWERED' if a.get('warm') else ''), bg=col)
        self.load['value'] = a['sg'] if a['run'] else 0
        f = []
        if a.get('lost'): f.append('POSITION NOT TRUSTED (crash / off): zero or home it')
        if a['ot']: f.append('DRIVER OVERHEATED')
        elif a['otpw'] or a['temp']: f.append('driver hot (%d C+)' % a['temp'] if a['temp'] else 'driver hot (pre-warning)')
        if a['s2g']: f.append('SHORT to GND')
        if a['ol'] and a['run']: f.append('OPEN LOAD (motor wire?)')
        self.flags.config(text='\n'.join(f))

class App(tk.Tk):
    def __init__(self, demo=False):
        super().__init__()
        self.title('ETZ plotter - ESP32 dashboard' + (' (DEMO)' if demo else ''))
        self.geometry('1060x900')
        self.link, self.demo = EspLink(), demo
        top = ttk.Frame(self, padding=6); top.pack(fill='x')
        ttk.Label(top, text='Port').pack(side='left')
        self.port = ttk.Combobox(top, width=30, state='readonly'); self.port.pack(side='left', padx=4)
        ttk.Button(top, text='Refresh', command=self.refresh_ports).pack(side='left')
        self.conn_btn = ttk.Button(top, text='Connect', command=self.toggle_conn); self.conn_btn.pack(side='left', padx=6)
        self.lamp = tk.Label(top, text='  not connected  ', bg=GREY, fg='white'); self.lamp.pack(side='left', padx=4)
        self.power = tk.Label(top, text='', width=24); self.power.pack(side='left', padx=4)
        self.busy = tk.Label(top, text='', fg='white'); self.busy.pack(side='left', padx=4)
        stop = tk.Button(top, text='STOP ALL', bg=RED, fg='white', font=('Segoe UI', 11, 'bold'), command=lambda: self.cmd('stop'))
        stop.pack(side='right')
        mid = ttk.Frame(self, padding=6); mid.pack(fill='x')
        self.panels = {}
        for i, (k, t) in enumerate(AXES):
            p = AxisPanel(mid, self, k, t); p.grid(row=0, column=i, padx=4, sticky='n'); self.panels[k] = p
        sysf = ttk.LabelFrame(self, text='ESP32', padding=(6, 2)); sysf.pack(fill='x', padx=6, pady=(0, 4))
        ttk.Label(sysf, text='RAM used').pack(side='left')
        self.ram = ttk.Progressbar(sysf, maximum=100, length=140); self.ram.pack(side='left', padx=4)
        self.sys = ttk.Label(sysf, text='-'); self.sys.pack(side='left', padx=6)
        ttk.Button(sysf, text='Memory details', command=lambda: self.cmd('mem')).pack(side='right')
        g = ttk.Frame(self, padding=(6, 0)); g.pack(fill='x')
        ttk.Label(g, text='all motors: speed').pack(side='left')
        self.spd = ttk.Entry(g, width=6); self.spd.insert(0, '3200'); self.spd.pack(side='left', padx=3)
        ttk.Button(g, text='Set', width=4, command=lambda: self.cmd('speed ' + self.spd.get())).pack(side='left')
        ttk.Label(g, text='  accel').pack(side='left')
        self.acc = ttk.Entry(g, width=7); self.acc.insert(0, '6400'); self.acc.pack(side='left', padx=3)
        ttk.Button(g, text='Set', width=4, command=lambda: self.cmd('accel ' + self.acc.get())).pack(side='left')
        ttk.Button(g, text='All +1 turn', command=lambda: self.cmd('all 1')).pack(side='left', padx=(14, 2))
        ttk.Button(g, text='All -1 turn', command=lambda: self.cmd('all -1')).pack(side='left', padx=2)
        ttk.Label(g, text='   XY line to steps').pack(side='left')
        self.lx = ttk.Entry(g, width=7); self.lx.insert(0, '3200'); self.lx.pack(side='left', padx=2)
        self.ly = ttk.Entry(g, width=7); self.ly.insert(0, '1600'); self.ly.pack(side='left', padx=2)
        ttk.Button(g, text='Go', width=4, command=lambda: self.cmd('line %s %s' % (self.lx.get(), self.ly.get()))).pack(side='left')
        self.wd = ttk.Label(g, text=''); self.wd.pack(side='right')
        h = ttk.Frame(self, padding=(6, 4)); h.pack(fill='x')
        ttk.Button(h, text='Self-test', command=self.self_test).pack(side='left', padx=2)
        ttk.Button(h, text='Driver status', command=lambda: self.cmd('status')).pack(side='left', padx=2)
        ttk.Button(h, text='Motor heat', command=lambda: self.cmd('heat')).pack(side='left', padx=2)
        ttk.Button(h, text='Black box', command=lambda: self.cmd('log')).pack(side='left', padx=2)
        ttk.Button(h, text='Crash log', command=lambda: self.cmd('log crash')).pack(side='left', padx=2)
        ttk.Label(h, text='   profile').pack(side='left')
        self.prof = ttk.Combobox(h, width=10, values=('boot', 'fast', 'careful')); self.prof.set('boot')
        self.prof.pack(side='left', padx=3)
        ttk.Button(h, text='Save', width=5, command=lambda: self.cmd('save ' + self.prof.get())).pack(side='left')
        ttk.Button(h, text='Load', width=5, command=self.load_profile).pack(side='left')
        ttk.Button(h, text='List', width=4, command=lambda: self.cmd('profiles')).pack(side='left')
        ttk.Button(h, text='Defaults', command=self.defaults).pack(side='left', padx=2)
        self.prof_now = ttk.Label(h, text=''); self.prof_now.pack(side='left', padx=6)
        ttk.Button(h, text='Route planner', command=self.planner).pack(side='right', padx=2)
        lf = ttk.LabelFrame(self, text='Log', padding=4); lf.pack(fill='both', expand=True, padx=6, pady=6)
        self.logbox = tk.Text(lf, height=10, font=('Consolas', 9), state='disabled')
        self.logbox.pack(fill='both', expand=True)
        for tag, col in (('tx', '#1a5fb4'), ('rx', '#222'), ('info', '#2e7d32'), ('err', RED), ('alarm', RED),
                         ('note', '#b07000'), ('pass', GREEN)):
            self.logbox.tag_config(tag, foreground=col)
        self.logbox.tag_config('alarm', font=('Consolas', 9, 'bold'))
        e = ttk.Frame(lf); e.pack(fill='x', pady=(4, 0))
        ttk.Label(e, text='command').pack(side='left')
        self.entry = ttk.Entry(e); self.entry.pack(side='left', fill='x', expand=True, padx=4)
        self.entry.bind('<Return>', lambda ev: self.send_entry())
        ttk.Button(e, text='Send', command=self.send_entry).pack(side='left')
        self.refresh_ports()
        self.protocol('WM_DELETE_WINDOW', self.on_close)
        self.after(100, self.tick)

    # ------------------------------------------------------------ actions
    def refresh_ports(self):
        ports = [] if self.demo else list_ports()
        self.port['values'] = ['DEMO board'] if self.demo else ['%s  %s' % p for p in ports]
        if self.port['values']:
            self.port.current(0)

    def toggle_conn(self):
        if self.link.connected:
            self.link.disconnect(); self.conn_btn.config(text='Connect'); return
        try:
            self.link.connect(self.port.get().split()[0] if not self.demo else None, fake=self.demo)
            self.conn_btn.config(text='Disconnect')
            for p in self.panels.values():
                p.synced = False
        except Exception as e:
            self.write('err', 'could not open the port: %s  (is the PlatformIO monitor still open?)' % e)

    def cmd(self, line):
        if not self.link.connected:
            self.write('err', 'not connected'); return
        self.link.send(line)

    def load_profile(self):
        self.cmd('load ' + self.prof.get())
        for p in self.panels.values():
            p.synced = False

    def defaults(self):
        self.cmd('defaults')
        for p in self.panels.values():
            p.synced = False

    def self_test(self):
        self.cmd('selftest')
        def cam():                   # the laptop's part: does the camera open and give pictures?
            try:
                import cv2
                cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
                ok, frame = cap.read() if cap.isOpened() else (False, None)
                cap.release()
                msg = ('  PASS  camera %d: picture %dx%d' % (CAMERA_INDEX, frame.shape[1], frame.shape[0])) if ok \
                    else '  FAIL  camera %d: no picture (plugged in? other program using it?)' % CAMERA_INDEX
            except Exception as e:
                msg = '  WARN  camera check not possible: %s' % e
            self.link.log.put(('rx', msg))
        threading.Thread(target=cam, daemon=True).start()

    def planner(self):
        import route_planner
        route_planner.window(self.link, master=self)

    def send_entry(self):
        t = self.entry.get().strip()
        if t:
            self.cmd(t); self.entry.delete(0, 'end')

    def write(self, kind, text):
        if kind == 'rx':
            u = text.upper()
            if 'CRASH' in u or 'HOT' in u or 'WATCHDOG' in u or 'FAIL' in u or text.startswith('err'):
                kind = 'alarm'
            elif text.startswith('event') or 'WARN' in u:
                kind = 'note'
            elif 'PASS' in u:
                kind = 'pass'
        self.logbox.config(state='normal')
        self.logbox.insert('end', ('> ' if kind == 'tx' else '') + text + '\n', kind)
        self.logbox.see('end'); self.logbox.config(state='disabled')

    # ------------------------------------------------------------ refresh
    def tick(self):
        while not self.link.log.empty():
            self.write(*self.link.log.get())
        age = self.link.alive()
        s = self.link.state
        if not self.link.connected:
            self.lamp.config(text='  not connected  ', bg=GREY)
            self.power.config(text='', bg='#f0f0f0'); self.busy.config(text='', bg='#f0f0f0')
            for p in self.panels.values(): p.update_from(None, {})
            if self.conn_btn.cget('text') != 'Connect': self.conn_btn.config(text='Connect')
        elif age is None or age > 1.0:
            self.lamp.config(text='  no data from ESP32  ', bg=RED)
        else:
            self.lamp.config(text='  ESP32 alive  ', bg=GREEN)
        if s and self.link.connected:
            for a in s['ax']:
                if a['n'] in self.panels: self.panels[a['n']].update_from(a, s)
            self.wd.config(text='watchdog %s ms%s   idle off %s' % (s['wd'], '  TRIPPED' if s['wdtrip'] else '',
                                                               '%d s' % (s['idle'] // 1000) if s.get('idle') else 'never'),
                           foreground=RED if s['wdtrip'] else '#555')
            if 'vbat' in s:
                v, on = s['vbat'], s.get('drive', 1)
                self.power.config(text='drive power %s   battery %.1f V' % ('ON' if on else 'OFF', v),
                                  bg=GREEN if on and v >= 14.8 else AMBER if on and v >= 14.0 else RED, fg='white')
            b = s.get('busy', '')
            self.busy.config(text='  busy: %s  ' % b if b else '', bg=AMBER if b else '#f0f0f0')
            self.prof_now.config(text='now: %s   crashes %s' % (s.get('prof', '?'), s.get('crashes', 0)))
            if 'heap' in s:
                used = s['heapsize'] - s['heap']
                self.ram['value'] = 100.0 * used / max(1, s['heapsize'])
                up = s['t'] // 1000
                self.sys.config(text='%d kB used of %d kB  (most ever %d kB)   loop %d /s   chip %.0f C   up %d:%02d:%02d' % (
                    used // 1024, s['heapsize'] // 1024, (s['heapsize'] - s['heapmin']) // 1024, s['loop'], s['ctemp'],
                    up // 3600, up // 60 % 60, up % 60))
        self.after(100, self.tick)

    def on_close(self):
        try:
            self.link.disconnect()
        finally:
            self.destroy()

if __name__ == '__main__':
    App(demo='--demo' in sys.argv).mainloop()
