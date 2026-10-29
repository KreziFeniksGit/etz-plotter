"""
The ETZ 2026-27 operational field, in the OFFICIAL coordinates of the ETZ (short version 02.10.2026, sections 2.2 and
appendix A; copy in docs/etz_kratko_26_27.pdf):
- origin O = centre of ArUco mark 27 (DICT_4X4_50, 18 mm); X along the long side of the sheet from mark 27 towards
  mark 28; Y along the short side from mark 27 towards the cells; millimetres.
- 9 columns 0..8 and 6 rows А..Е (А nearest the marks 27 / 28), cells 28 mm. A cell is named row letter + column
  number, e.g. Б3; its centre is X = 28 * n, Y = 28 * k (n = column, k = row number: А = 1 ... Е = 6). Б3 = (84, 56).
- buffer ("столбец отбоя"): column 9 (X = 252), rows А..Д (k = 1..5).
- marks: 27 at (0, 0) under column 0, 28 at (224, 0) under column 8, 29 at (252, 168) in the buffer column at row Е.
- service area under the field (Y about -18..+9 between the marks) is the organisers': no checkers there.
- black bands 6 mm wide bound the grid on the left (X < -14) and at the top (Y > 182).
A cell is a tuple (n, k); the buffer places are (9, 1) .. (9, 5).
(Up to 29 Oct the code used a transposed, mirrored frame; the cell names were the same.)
"""
import numpy as np
import cv2

ARUCO_DICT = cv2.aruco.DICT_4X4_50
MARK_IDS = (27, 28, 29)
CELL = 28.0
COLS = 9                               # columns n = 0..8
ROWS = 6                               # rows k = 1..6 (А..Е)
BUFFER_COL = 9                         # buffer column, rows 1..5 (А..Д)
BUFFER_ROWS = 5
MARK_SIZE = 18.0
MARKS = {27: (0.0, 0.0), 28: (224.0, 0.0), 29: (252.0, 168.0)}
ROW_RU = 'АБВГДЕ'
ROW_LAT = 'ABVGDE'                     # transliteration (OpenCV fonts have no Cyrillic): A Б=B В=V Г=G Д=D Е=E
BAND = 6.0                             # black bands left and top
VIEW = (-24.0, -16.0, 270.0, 196.0)    # field area shown in the straightened view (x0, y0, x1, y1)
COLOURS = ('red', 'green', 'blue', 'yellow', 'magenta')
BGR = {'red': (40, 40, 220), 'green': (60, 170, 40), 'blue': (200, 90, 20), 'yellow': (30, 210, 240), 'magenta': (190, 40, 200)}
SERVICE_AREA = (8.0, -16.0, 216.0, 9.0)   # under the field between the marks (x0, y0, x1, y1): never place a checker here
PLACE_TOL = 10.0                       # ETZ 2.4: placed if the centre is within 10 mm of the cell centre

def mark_corners_field(mid):
    """corners of a mark in field mm, in the order OpenCV reports them (top-left, top-right, bottom-right,
    bottom-left of the marker image). In the official frame the marks stand upright (Y up)."""
    cx, cy = MARKS[mid]
    h = MARK_SIZE / 2
    return np.array([(cx - h, cy + h), (cx + h, cy + h), (cx + h, cy - h), (cx - h, cy - h)], np.float32)

def cell_centre(n, k):
    """centre of cell (column n, row k) in field mm; also works for the buffer (n = 9)"""
    return CELL * n, CELL * k

def buffer_centre(k):
    return cell_centre(BUFFER_COL, k)

def is_buffer(cell):
    return cell is not None and cell[0] == BUFFER_COL

def field_cells():
    return [(n, k) for k in range(1, ROWS + 1) for n in range(COLS)]

def buffer_cells():
    return [(BUFFER_COL, k) for k in range(1, BUFFER_ROWS + 1)]

def all_cells():
    return field_cells() + buffer_cells()

def cell_of(x, y):
    """field mm -> the cell (n, k) whose centre is nearest, or None outside the grid and the buffer"""
    n = int(np.floor(x / CELL + 0.5))
    k = int(np.floor(y / CELL + 0.5))
    if 0 <= n < COLS and 1 <= k <= ROWS:
        return n, k
    if n == BUFFER_COL and 1 <= k <= BUFFER_ROWS:
        return n, k
    return None

def placed_in(x, y, cell):
    """ETZ 2.4: a checker counts as placed in a cell if its centre is within 10 mm of the cell centre"""
    cx, cy = cell_centre(*cell)
    return (x - cx) ** 2 + (y - cy) ** 2 <= PLACE_TOL ** 2

def in_service_area(x, y, r=13.0):
    x0, y0, x1, y1 = SERVICE_AREA
    return x0 - r < x < x1 + r and y0 - r < y < y1 + r

def cell_name(cell, latin=False):
    """(n, k) -> 'Б3' ('B3' with latin=True); buffer -> 'отбой Б' / 'buf-B'"""
    if cell is None:
        return '-'
    n, k = cell
    letter = (ROW_LAT if latin else ROW_RU)[k - 1]
    if n == BUFFER_COL:
        return ('buf-' if latin else 'отбой ') + letter
    return letter + str(n)

_LETTERS = {}
for _i, (_ru, _lat) in enumerate(zip(ROW_RU, ROW_LAT)):
    _LETTERS[_ru] = _LETTERS[_ru.lower()] = _LETTERS[_lat] = _LETTERS[_lat.lower()] = _i + 1

def parse_cell(text):
    """'Б3', 'b3', 'B 3', 'отбой Б', 'buf-B' -> (n, k); raises ValueError"""
    t = text.strip().replace(' ', '').replace('-', '')
    low = t.lower()
    for pre in ('отбой', 'buf', 'буфер'):
        if low.startswith(pre):
            k = _LETTERS.get(t[len(pre):])
            if k is None or k > BUFFER_ROWS:
                raise ValueError('no buffer place %r (А..Д)' % text)
            return BUFFER_COL, k
    if len(t) >= 2 and t[0] in _LETTERS and t[1:].isdigit():
        n, k = int(t[1:]), _LETTERS[t[0]]
        if 0 <= n < COLS:
            return n, k
    raise ValueError('no cell %r: use a row letter А..Е and a column 0..8, e.g. Б3' % text)

# ---------------------------------------------------------------- drawing (for the screen test and the self-test)
SHEET = (297.0, 210.0)                 # A4 landscape as in ETZ fig. 2 (X to the right, Y up)
ORIGIN_ON_SHEET = (23.9, 16.6)         # mark 27 centre from the sheet's lower-left (measured on the drawing)

def render(px_per_mm=3.0, checkers=(), stickers=()):
    """The sheet as in ETZ fig. 2. checkers: [(n, k, colour)], stickers: [(n, k, text)] = QR on a white disc."""
    W, H = SHEET
    s = px_per_mm
    img = np.full((int(round(H * s)), int(round(W * s)), 3), 255, np.uint8)
    ox, oy = ORIGIN_ON_SHEET
    P = lambda x, y: (int(round((x + ox) * s)), int(round((H - (y + oy)) * s)))   # field mm -> pixel
    th = max(1, int(round(0.35 * s)))
    x0, x1 = -CELL / 2, CELL * (COLS - 0.5)
    y0, y1 = CELL / 2, CELL * (ROWS + 0.5)
    # black bands left and top, red grid, green circles, centre dots
    cv2.rectangle(img, P(x0 - BAND, y0), P(x0, y1 + BAND), (0, 0, 0), -1)
    cv2.rectangle(img, P(x0 - BAND, y1 + BAND), P(x1, y1), (0, 0, 0), -1)
    for i in range(COLS + 1):
        cv2.line(img, P(x0 + i * CELL, y0), P(x0 + i * CELL, y1), (60, 60, 220), th)
    for i in range(ROWS + 1):
        cv2.line(img, P(x0, y0 + i * CELL), P(x1, y0 + i * CELL), (60, 60, 220), th)
    for cell in all_cells():
        cx, cy = P(*cell_centre(*cell))
        cv2.circle(img, (cx, cy), int(12.25 * s), (90, 170, 90), th, cv2.LINE_AA)
        if not is_buffer(cell):
            cv2.circle(img, (cx, cy), int(3 * s), (0, 0, 0), -1, cv2.LINE_AA)
    for k in range(1, ROWS + 1):
        cv2.putText(img, ROW_LAT[k - 1], P(CELL * 9.6, CELL * k - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.12 * s, (120, 120, 120), 1)
    for n in range(COLS):
        cv2.putText(img, str(n), P(CELL * n + 10, CELL * 0.35), cv2.FONT_HERSHEY_SIMPLEX, 0.12 * s, (120, 120, 120), 1)
    d = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    m = int(round(MARK_SIZE * s))
    for mid, (mx, my) in MARKS.items():
        mk = cv2.aruco.generateImageMarker(d, mid, m)              # upright in the official frame
        x, y = P(mx - MARK_SIZE / 2, my + MARK_SIZE / 2)
        img[y:y + m, x:x + m] = cv2.cvtColor(mk, cv2.COLOR_GRAY2BGR)
    for n, k, colour in checkers:
        cv2.circle(img, P(*cell_centre(n, k)), int(13 * s), BGR[colour], -1, cv2.LINE_AA)
    enc = cv2.QRCodeEncoder.create()
    for n, k, text in stickers:
        cx, cy = P(*cell_centre(n, k))
        cv2.circle(img, (cx, cy), int(13 * s), (235, 235, 235), -1, cv2.LINE_AA)
        q = cv2.resize(enc.encode(text), (int(17 * s),) * 2, interpolation=cv2.INTER_NEAREST)
        a = q.shape[0]
        img[cy - a // 2:cy - a // 2 + a, cx - a // 2:cx - a // 2 + a] = cv2.cvtColor(q, cv2.COLOR_GRAY2BGR)
    return img

def _self_check():
    assert cell_centre(*parse_cell('Б3')) == (84.0, 56.0)              # ETZ fig. 2 example
    assert parse_cell('B3') == parse_cell('б3') == (3, 2)
    assert buffer_centre(1) == (252.0, 28.0) and parse_cell('отбой Д') == (9, 5)
    assert cell_name((3, 2)) == 'Б3' and cell_name((9, 5)) == 'отбой Д' and cell_name((0, 6), latin=True) == 'E0'
    assert MARKS[28] == cell_centre(8, 0) and MARKS[29] == cell_centre(9, 6)   # marks on the same 28 mm grid
    assert all(cell_of(*cell_centre(*c)) == c for c in all_cells())
    assert cell_of(8, 3) is None and cell_of(260, 168) is None        # below row А / on mark 29: no cell
    assert placed_in(84 + 9.9, 56, (3, 2)) and not placed_in(84 + 10.1, 56, (3, 2))
    return True

if __name__ == '__main__':
    print('field self-check:', _self_check())
