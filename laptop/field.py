"""
The competition field (A4 sheet) and a drawing of it.
Field coordinates: mm, origin = centre of ArUco mark 27 (rules), x to the right, y up.
VERIFY: the exact sheet layout (where the three marks and the grid sit) against the drawing in the full rules text;
only the numbers in LAYOUT need changing, everything else follows.
"""
import numpy as np
import cv2

ARUCO_DICT = cv2.aruco.DICT_4X4_50
MARK_IDS = (27, 28, 29)
LAYOUT = dict(
    sheet=(297.0, 210.0),            # A4 landscape, mm
    mark_size=18.0,                  # black square side (rules)
    # buffer column + 9 columns = 280 mm of the 297 mm width; 6 rows = 168 of 210 mm, the marks sit in the bands
    # above / below the grid  VERIFY all of this against the rules drawing
    marks={27: (20.0, 10.5), 28: (277.0, 10.5), 29: (20.0, 199.5)},   # mark centres on the sheet (from its lower-left)
    cell=28.0,                       # grid cell (rules)
    cols=9, rows=6,                  # grid 9 x 6 (rules)
    grid_ll=(36.5, 21.0),            # lower-left corner of grid column 1 (the buffer column is left of it)
    buffer_cols=1,                   # buffer column left of the grid (rules: "buffer column")  VERIFY side
)
COLOURS = ('red', 'green', 'blue', 'yellow', 'magenta')
BGR = {'red': (40, 40, 220), 'green': (60, 170, 40), 'blue': (200, 90, 20), 'yellow': (30, 210, 240), 'magenta': (190, 40, 200)}

def sheet_to_field(x, y):
    o = LAYOUT['marks'][27]
    return x - o[0], y - o[1]

def mark_corners_field(mid):
    """the 4 corners of a mark in field mm, in OpenCV's order (top-left, top-right, bottom-right, bottom-left as printed)"""
    cx, cy = sheet_to_field(*LAYOUT['marks'][mid])
    h = LAYOUT['mark_size'] / 2
    return np.array([(cx - h, cy + h), (cx + h, cy + h), (cx + h, cy - h), (cx - h, cy - h)], np.float32)

def cell_centre(col, row):
    """col 0 = buffer column, 1..9 grid columns; row 1..6 from the bottom. Returns field mm."""
    gx, gy = LAYOUT['grid_ll']
    c = LAYOUT['cell']
    return sheet_to_field(gx + (col - 1 + 0.5) * c, gy + (row - 1 + 0.5) * c)

def cell_of(x, y):
    """field mm -> (col, row) or None if outside the grid / buffer"""
    gx, gy = sheet_to_field(*LAYOUT['grid_ll'])
    c = LAYOUT['cell']
    col = int(np.floor((x - gx) / c)) + 1
    row = int(np.floor((y - gy) / c)) + 1
    if 1 - LAYOUT['buffer_cols'] <= col <= LAYOUT['cols'] and 1 <= row <= LAYOUT['rows']:
        return col, row
    return None

def cell_name(cr):
    if cr is None:
        return '-'
    col, row = cr
    return ('B' if col <= 0 else str(col)) + 'ABCDEF'[row - 1]

# ---------------------------------------------------------------- drawing (for the screen test)
def render(px_per_mm=4.0, checkers=(), stickers=()):
    """Top-down picture of the sheet. checkers: [(col, row, colour)], stickers: [(col, row, text)] (QR on a white disc).
    Returns the BGR image."""
    W, H = LAYOUT['sheet']
    s = px_per_mm
    img = np.full((int(H * s), int(W * s), 3), 255, np.uint8)
    P = lambda x, y: (int(round(x * s)), int(round((H - y) * s)))      # sheet mm -> pixel (y up)
    gx, gy = LAYOUT['grid_ll']
    c = LAYOUT['cell']
    for k in range(-LAYOUT['buffer_cols'], LAYOUT['cols'] + 1):
        cv2.line(img, P(gx + k * c, gy), P(gx + k * c, gy + LAYOUT['rows'] * c), (0, 0, 0), max(1, int(s * 0.4)))
    for k in range(LAYOUT['rows'] + 1):
        cv2.line(img, P(gx - LAYOUT['buffer_cols'] * c, gy + k * c), P(gx + LAYOUT['cols'] * c, gy + k * c), (0, 0, 0), max(1, int(s * 0.4)))
    d = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    ms = LAYOUT['mark_size']
    for mid, (mx, my) in LAYOUT['marks'].items():
        n = int(round(ms * s))
        m = cv2.aruco.generateImageMarker(d, mid, n)
        x0, y0 = P(mx - ms / 2, my + ms / 2)
        img[y0:y0 + n, x0:x0 + n] = cv2.cvtColor(m, cv2.COLOR_GRAY2BGR)
        cv2.putText(img, str(mid), P(mx - 4, my - ms / 2 - 6), cv2.FONT_HERSHEY_SIMPLEX, s * 0.25, (0, 0, 0), max(1, int(s / 3)))
    o = LAYOUT['marks'][27]
    for col, row, colour in checkers:
        fx, fy = cell_centre(col, row)
        cv2.circle(img, P(fx + o[0], fy + o[1]), int(13 * s), BGR[colour], -1, cv2.LINE_AA)
    enc = cv2.QRCodeEncoder.create()
    for col, row, text in stickers:
        fx, fy = cell_centre(col, row)
        cx, cy = P(fx + o[0], fy + o[1])
        cv2.circle(img, (cx, cy), int(13 * s), (235, 235, 235), -1, cv2.LINE_AA)
        q = enc.encode(text)
        n = int(17 * s)
        q = cv2.resize(q, (n, n), interpolation=cv2.INTER_NEAREST)
        img[cy - n // 2:cy - n // 2 + n, cx - n // 2:cx - n // 2 + n] = cv2.cvtColor(q, cv2.COLOR_GRAY2BGR)
    return img
