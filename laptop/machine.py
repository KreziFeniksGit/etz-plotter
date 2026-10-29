"""
The plotter's numbers for the laptop side (planner, digital twin, run program): one place, so they always agree.
Coordinates:
- field  (X, Y): official ETZ frame, mm, origin = mark 27 (see field.py)
- machine (mx, my): the polygon frame of the CAD model (frame/frame.py): x along the 600 mm side, y along 500, mm
- carriage (PXB, PYC): X carriage pivot x and Y carriage centre y as in the CAD model (assembly.world())
- axis (ax, ay): firmware positions in mm from the home switches (`gomm`, `linemm`)
Nominal sheet position (CAD frame.field_reference): mx = 564.5 - Y, my = 116.5 + X. The real sheet may be 5 mm off and
3 deg turned (ETZ 2.2): FieldTransform.fit() finds it from the measured mark positions.
Calibrated values (bring-up, docs/bringup.md) are kept in machine_cal.json next to this file; defaults below.
Everything marked VERIFY is an estimate until measured on the real plotter.
"""
import json, math, os

HERE = os.path.dirname(os.path.abspath(__file__))
CAL_FILE = os.path.join(HERE, 'machine_cal.json')

# ---------------------------------------------------------------- geometry from the CAD model (wrist/wrist_module.py, frame/frame.py)
MAG_DX, MAG_DY = 110.0, 18.5           # magnet axis from (PXB, PYC): wrist_module MAG_X, MAG_Y
PXB_RANGE = (287.0, 430.0)             # X carriage travel (CLAUDE.md)
PYC_RANGE = (40.0, 376.0)              # Y carriage travel
PARK = (287.0, 40.0)                   # parked carriage (inside zones 1 + 2)
R_ARM, H_MID = 80.0, 22.5              # lift parallelogram arm, magnet face height with the arms level
H_MIN, H_MAX = 5.0, 40.0               # magnet face height range
CHECKER_H = 5.0                        # checker height (ETZ 2.3)
NOMINAL_ORIGIN = (564.5, 116.5)        # mark 27 in machine mm (CAD)

DEFAULTS = {
    # firmware axis zero = home switch; the carriage position there (VERIFY at bring-up: home, then measure)
    'home_pxb': 287.0, 'home_pyc': 40.0,
    'steps_per_mm_x': 80.0, 'steps_per_mm_y': 80.0,       # GT2 belt, 20T pulley, 200 steps x 16 microsteps
    'steps_per_deg_w': 3200.0 / 360.0,                     # wrist motor drives the magnet hub directly
    # servo pulse for the arms level (h = H_MID) and pulse change per degree of arm angle (VERIFY: calibrate h = 5 / 40)
    'servo_us_level': 1500.0, 'servo_us_per_deg': 10.0, 'servo_sign': 1.0,
    # motion (firmware defaults; `tune` results go here)
    'speed_x': 8000.0, 'speed_y': 8000.0, 'accel_x': 40000.0, 'accel_y': 40000.0, 'jerk_ms': 20.0,
    'speed_w': 4800.0, 'accel_w': 20000.0,
    # times (VERIFY): MG996R about 0.19 s / 60 deg at 4.8 V; magnet field build-up / release
    'servo_s_per_deg': 0.19 / 60.0, 'servo_settle': 0.08,
    'mag_grab': 0.12, 'mag_release': 0.15,
    'h_carry': 36.0,                   # face height while carrying over stacks (5 stacked = 25 mm + held checker 5 + margin)
    'h_clear': 2.0,                    # extra height when approaching a stack top
    'capture_r': 6.0,                  # magnet catches a checker whose centre is within this (VERIFY with the real magnet)
}

def load_cal(path=CAL_FILE):
    cal = dict(DEFAULTS)
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            cal.update(json.load(f))
    return cal

def save_cal(cal, path=CAL_FILE):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({k: v for k, v in cal.items() if DEFAULTS.get(k) != v}, f, indent=1)

# ---------------------------------------------------------------- field <-> machine
class FieldTransform:
    """rigid 2D transform field (X, Y) -> machine (mx, my): rotation a (rad) + offset"""
    def __init__(self, a=math.pi / 2, ox=NOMINAL_ORIGIN[0], oy=NOMINAL_ORIGIN[1]):
        self.a, self.ox, self.oy = a, ox, oy

    def to_machine(self, X, Y):
        c, s = math.cos(self.a), math.sin(self.a)
        return self.ox + c * X - s * Y, self.oy + s * X + c * Y

    def to_field(self, mx, my):
        c, s = math.cos(self.a), math.sin(self.a)
        dx, dy = mx - self.ox, my - self.oy
        return c * dx + s * dy, -s * dx + c * dy

    @classmethod
    def fit(cls, pairs):
        """least-squares rigid fit from [((X, Y) field, (mx, my) measured machine)], at least 2 points"""
        n = len(pairs)
        fx = sum(p[0][0] for p in pairs) / n; fy = sum(p[0][1] for p in pairs) / n
        mx = sum(p[1][0] for p in pairs) / n; my = sum(p[1][1] for p in pairs) / n
        sxx = sxy = 0.0
        for (X, Y), (u, v) in pairs:
            a, b, c, d = X - fx, Y - fy, u - mx, v - my
            sxx += a * c + b * d                 # cos part
            sxy += a * d - b * c                 # sin part
        ang = math.atan2(sxy, sxx)
        t = cls(ang, 0.0, 0.0)
        px, py = t.to_machine(fx, fy)
        t.ox, t.oy = mx - px, my - py
        return t

    def residual(self, pairs):
        return max(math.dist(self.to_machine(*f), m) for f, m in pairs)

    def describe(self):
        return 'turned %.2f deg, mark 27 at (%.1f, %.1f) mm' % (math.degrees(self.a) - 90.0, self.ox, self.oy)

# ---------------------------------------------------------------- machine <-> carriage <-> firmware axis
def magnet_to_carriage(mx, my):
    return mx - MAG_DX, my - MAG_DY

def carriage_to_magnet(pxb, pyc):
    return pxb + MAG_DX, pyc + MAG_DY

def carriage_to_axis(pxb, pyc, cal):
    return pxb - cal['home_pxb'], pyc - cal['home_pyc']

def axis_to_carriage(ax, ay, cal):
    return ax + cal['home_pxb'], ay + cal['home_pyc']

def magnet_to_axis(mx, my, cal):
    return carriage_to_axis(*magnet_to_carriage(mx, my), cal)

def axis_to_magnet(ax, ay, cal):
    return carriage_to_magnet(*axis_to_carriage(ax, ay, cal))

def reachable(mx, my, tol=0.0):
    pxb, pyc = magnet_to_carriage(mx, my)
    return (PXB_RANGE[0] - tol <= pxb <= PXB_RANGE[1] + tol) and (PYC_RANGE[0] - tol <= pyc <= PYC_RANGE[1] + tol)

def clamp_to_reach(mx, my):
    """nearest magnet position the carriages can reach; returns (mx, my, how far it moved in mm)"""
    pxb, pyc = magnet_to_carriage(mx, my)
    cx = min(max(pxb, PXB_RANGE[0]), PXB_RANGE[1])
    cy = min(max(pyc, PYC_RANGE[0]), PYC_RANGE[1])
    nx, ny = carriage_to_magnet(cx, cy)
    return nx, ny, math.hypot(nx - mx, ny - my)

def worst_reach_shortfall(step_deg=0.5):
    """How far cells can lie outside the magnet's reach when the sheet is placed anywhere the ETZ allows
    (5 mm shift, 3 deg turn about the sheet centre). 29 Oct 2026: about 11.9 mm (row Е) and 8.1 mm (row А / buffer А)
    in machine x: the X travel (PXB 287..430) only just covers the nominal sheet."""
    import field as F
    cx, cy = F.SHEET[0] / 2 - F.ORIGIN_ON_SHEET[0], F.SHEET[1] / 2 - F.ORIGIN_ON_SHEET[1]   # sheet centre, field mm
    nominal = FieldTransform()
    cmx, cmy = nominal.to_machine(cx, cy)
    worst = (0.0, None)
    k = int(round(3.0 / step_deg))
    for i in range(-k, k + 1):
        for dx in range(-5, 6):
            for dy in range(-5, 6):
                if dx * dx + dy * dy > 25:
                    continue
                t = FieldTransform(math.pi / 2 + math.radians(i * step_deg), 0.0, 0.0)
                px, py = t.to_machine(cx, cy)
                t.ox, t.oy = cmx - px + dx, cmy - py + dy
                for c in F.all_cells():
                    d = clamp_to_reach(*t.to_machine(*F.cell_centre(*c)))[2]
                    if d > worst[0]:
                        worst = (d, F.cell_name(c))
    return worst

def axis_limits(cal):
    lo = carriage_to_axis(PXB_RANGE[0], PYC_RANGE[0], cal)
    hi = carriage_to_axis(PXB_RANGE[1], PYC_RANGE[1], cal)
    return (lo[0], hi[0]), (lo[1], hi[1])

# ---------------------------------------------------------------- lift
def arm_angle(h):
    """arm angle (deg) for magnet face height h (wrist_module.pose: th = asin((h - H_MID) / R_ARM))"""
    h = min(max(h, H_MIN), H_MAX)
    return math.degrees(math.asin((h - H_MID) / R_ARM))

def servo_us(h, cal):
    return cal['servo_us_level'] + cal['servo_sign'] * cal['servo_us_per_deg'] * arm_angle(h)

def lift_time(h0, h1, cal):
    return abs(arm_angle(h1) - arm_angle(h0)) * cal['servo_s_per_deg'] + cal['servo_settle']

def stack_top(levels):
    """magnet face height that touches the top of a stack of `levels` checkers"""
    return CHECKER_H * levels

# ---------------------------------------------------------------- motion time (same profile as firmware/lib/StepGen)
def move_time(dist, v, a, jerk_ms=0.0):
    """seconds for a point-to-point move of `dist` (any unit) with max speed v and accel a (same units).
    Trapezoid, plus the S-curve ramp: with jerk ramp tj the move takes about tj longer (checked against the StepGen
    integer simulation: 3200 steps at 3200/6400, jerk 50 ms -> 1.562 s vs 1.495 + 0.05)."""
    d = abs(dist)
    if d < 1e-9:
        return 0.0
    if d < v * v / a:
        t = 2.0 * math.sqrt(d / a)
    else:
        t = d / v + v / a
    return t + jerk_ms / 1000.0

def line_time(dx, dy, cal):
    """time for the firmware `linemm` move (both axes same profile shape, each within its own limits)"""
    L = math.hypot(dx, dy)
    if L < 1e-9:
        return 0.0
    ux, uy = abs(dx) / L, abs(dy) / L
    vx, vy = cal['speed_x'] / cal['steps_per_mm_x'], cal['speed_y'] / cal['steps_per_mm_y']
    axx, ayy = cal['accel_x'] / cal['steps_per_mm_x'], cal['accel_y'] / cal['steps_per_mm_y']
    V = min(vx / ux if ux > 1e-3 else 1e9, vy / uy if uy > 1e-3 else 1e9)
    A = min(axx / ux if ux > 1e-3 else 1e9, ayy / uy if uy > 1e-3 else 1e9)
    return move_time(L, V, A, cal['jerk_ms'])

def wrist_time(d0, d1, cal):
    d = abs((d1 - d0 + 180.0) % 360.0 - 180.0)          # shortest way round
    return move_time(d * cal['steps_per_deg_w'], cal['speed_w'], cal['accel_w'], 0.0)

def speed_mm_s(cal):
    return min(cal['speed_x'] / cal['steps_per_mm_x'], cal['speed_y'] / cal['steps_per_mm_y'])

def _self_check():
    cal = dict(DEFAULTS)
    t = FieldTransform()
    assert all(abs(a - b) < 1e-9 for a, b in zip(t.to_machine(0, 0), NOMINAL_ORIGIN))
    assert all(abs(a - b) < 1e-9 for a, b in zip(t.to_machine(84, 56), (564.5 - 56, 116.5 + 84)))   # Б3 as in the CAD
    assert all(abs(a - b) < 1e-9 for a, b in zip(t.to_field(*t.to_machine(30, 40)), (30, 40)))
    # a sheet 4 mm off and 2.5 deg turned is found again from the three marks
    real = FieldTransform(math.pi / 2 + math.radians(2.5), 566.0, 112.0)
    pairs = [(m, real.to_machine(*m)) for m in ((0, 0), (224, 0), (252, 168))]
    fit = FieldTransform.fit(pairs)
    assert fit.residual(pairs) < 1e-6 and abs(fit.a - real.a) < 1e-9
    # every cell centre of the nominal sheet is within 1 mm of the magnet's reach (row Е is 0.5 mm short)
    import field as F
    assert all(reachable(*t.to_machine(*F.cell_centre(*c)), tol=1.0) for c in F.all_cells())
    assert abs(servo_us(H_MID, cal) - cal['servo_us_level']) < 1e-9
    assert speed_mm_s(cal) >= 100.0                   # ETZ: at least 100 mm/s
    return True

if __name__ == '__main__':
    print('machine self-check:', _self_check())
    cal = load_cal()
    print('speed %.0f mm/s; across the field (250 mm diagonal) %.2f s' % (speed_mm_s(cal), line_time(150, 200, cal)))
    d, cell = worst_reach_shortfall()
    print('worst case (sheet 5 mm off, 3 deg turned): a cell centre up to %.1f mm outside the magnet reach (%s)' % (d, cell))
