"""
The ETZ 2026-27 field (A4 portrait), measured from the official drawing (Egor's picture, 24 Oct):
- 6 columns  А Б В Г Д Е  (А on the right, next to the marks 27 / 28), 9 rows 0..8 (0 at the bottom), cells 28 mm.
- buffer row above row 8: 5 places, columns А..Д (mark 29 stands where Е would be).
- ArUco DICT_4X4_50, 18 mm: 27 bottom-right = ORIGIN, 28 top-right, 29 top-left; printed turned 90 deg.
Field coordinates: mm, origin = centre of mark 27, x to the right, y up (as the sheet is seen in the drawing).
Everything sits on the 28 mm grid of mark 27: cell (col, row) centre = (-28 * (col + 1), 28 * row).
Column index col: 0 = А ... 5 = Е; row 0..8, row 9 = buffer.
"""
import numpy as np
import cv2

ARUCO_DICT = cv2.aruco.DICT_4X4_50
MARK_IDS = (27, 28, 29)
CELL = 28.0
COLS, ROWS = 6, 9
BUFFER_ROW = 9
BUFFER_COLS = 5                       # А..Д
MARK_SIZE = 18.0
MARKS = {27: (0.0, 0.0), 28: (0.0, 224.0), 29: (-168.0, 252.0)}
COL_RU = 'АБВГДЕ'
COL_LAT = 'ABVGDE'                    # for text drawn on images (OpenCV fonts have no Cyrillic)
VIEW = (-200.0, -24.0, 14.0, 270.0)   # field area shown in the straightened view (x0, y0, x1, y1)
COLOURS = ('red', 'green', 'blue', 'yellow', 'magenta')
BGR = {'red': (40, 40, 220), 'green': (60, 170, 40), 'blue': (200, 90, 20), 'yellow': (30, 210, 240), 'magenta': (190, 40, 200)}

def mark_corners_field(mid):
    """corners of a mark in field mm, in the order OpenCV reports them. The marks are printed turned 90 deg, so
    OpenCV's corner 0 is at the bottom-left of each mark (measured on the drawing), then clockwise."""
    cx, cy = MARKS[mid]
    h = MARK_SIZE / 2
    return np.array([(cx - h, cy - h), (cx - h, cy + h), (cx + h, cy + h), (cx + h, cy - h)], np.float32)

def cell_centre(col, row):
    return -CELL * (col + 1), CELL * row

def all_cells():
    cells = [(c, r) for r in range(ROWS) for c in range(COLS)]
    return cells + [(c, BUFFER_ROW) for c in range(BUFFER_COLS)]

def cell_of(x, y):
    """field mm -> (col, row) of the cell it is in, or None"""
    col = int(np.floor(-x / CELL + 0.5)) - 1
    row = int(np.floor(y / CELL + 0.5))
    if 0 <= col < COLS and 0 <= row < ROWS:
        return col, row
    if row == BUFFER_ROW and 0 <= col < BUFFER_COLS:
        return col, row
    return None

def cell_name(cr, latin=False):
    if cr is None:
        return '-'
    col, row = cr
    letter = (COL_LAT if latin else COL_RU)[col]
    return ('buf-' if latin else 'буфер ') + letter if row == BUFFER_ROW else letter + str(row)

# ---------------------------------------------------------------- drawing (for the screen test)
SHEET = (210.0, 297.0)
ORIGIN_ON_SHEET = (193.4, 23.9)       # mark 27 centre from the sheet's lower-left (measured)

def render(px_per_mm=3.0, checkers=(), stickers=()):
    """The sheet as in the drawing. checkers: [(col, row, colour)], stickers: [(col, row, text)] = QR on a white disc."""
    W, H = SHEET
    s = px_per_mm
    img = np.full((int(round(H * s)), int(round(W * s)), 3), 255, np.uint8)
    ox, oy = ORIGIN_ON_SHEET
    P = lambda x, y: (int(round((x + ox) * s)), int(round((H - (y + oy)) * s)))   # field mm -> pixel
    th = max(1, int(round(0.35 * s)))
    x0, x1 = -CELL * (COLS + 0.5), -CELL * 0.5
    y0, y1 = -CELL * 0.5, CELL * (ROWS - 0.5)
    # thick black edges left and bottom, red grid, dashed-looking green circles, centre dots
    cv2.rectangle(img, P(x0 - 6, y0 - 6), P(x0, y1), (0, 0, 0), -1)
    cv2.rectangle(img, P(x0 - 6, y0 - 6), P(x1, y0), (0, 0, 0), -1)
    for k in range(COLS + 1):
        cv2.line(img, P(x0 + k * CELL, y0), P(x0 + k * CELL, y1), (60, 60, 220), th)
    for k in range(ROWS + 1):
        cv2.line(img, P(x0, y0 + k * CELL), P(x1, y0 + k * CELL), (60, 60, 220), th)
    for col, row in all_cells():
        cx, cy = P(*cell_centre(col, row))
        cv2.circle(img, (cx, cy), int(13 * s), (90, 170, 90), th, cv2.LINE_AA)
        if row < ROWS:
            cv2.circle(img, (cx, cy), int(3 * s), (0, 0, 0), -1, cv2.LINE_AA)
    for col in range(COLS):
        cv2.putText(img, COL_LAT[col], P(-CELL * (col + 1) - 2, CELL * 9.55), cv2.FONT_HERSHEY_SIMPLEX, 0.12 * s, (120, 120, 120), 1)
    for row in range(ROWS):
        cv2.putText(img, str(row), P(-CELL * 0.4, CELL * row + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.12 * s, (120, 120, 120), 1)
    d = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    n = int(round(MARK_SIZE * s))
    for mid, (mx, my) in MARKS.items():
        m = np.rot90(cv2.aruco.generateImageMarker(d, mid, n), 1)     # turned 90 deg as on the official sheet
        x, y = P(mx - MARK_SIZE / 2, my + MARK_SIZE / 2)
        img[y:y + n, x:x + n] = cv2.cvtColor(np.ascontiguousarray(m), cv2.COLOR_GRAY2BGR)
    for col, row, colour in checkers:
        cv2.circle(img, P(*cell_centre(col, row)), int(13 * s), BGR[colour], -1, cv2.LINE_AA)
    enc = cv2.QRCodeEncoder.create()
    for col, row, text in stickers:
        cx, cy = P(*cell_centre(col, row))
        cv2.circle(img, (cx, cy), int(13 * s), (235, 235, 235), -1, cv2.LINE_AA)
        q = cv2.resize(enc.encode(text), (int(17 * s),) * 2, interpolation=cv2.INTER_NEAREST)
        k = q.shape[0]
        img[cy - k // 2:cy - k // 2 + k, cx - k // 2:cx - k // 2 + k] = cv2.cvtColor(q, cv2.COLOR_GRAY2BGR)
    return img
