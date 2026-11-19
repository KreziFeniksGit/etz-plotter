"""
A4 sheet of checker stickers for camera tests: ArUco (DICT_4X4_50), AprilTag (tag36h11) and QR codes, each centred
in a 26 mm circle (the checker). Print at 100 % ("actual size", not "fit to page"), cut along the grey circles.
Check the 100 mm scale bar with a ruler after printing.

Sizes (rules, docs/etz_rules_summary.md): QR >= 15 x 15 mm, version 1 (21 x 21 modules). Square markers are made as
big as fits inside the circle with a white quiet zone around them.
Run:  laptop\\.venv\\Scripts\\python laptop\\make_stickers.py   -> laptop/out/stickers_a4.png (300 dpi), then it reads
the sheet back with the same detectors as vision (every sticker must be found).
"""
import os, struct, sys, zlib
import numpy as np
import cv2
import field as F
sys.stdout.reconfigure(encoding="utf-8")

DPI = 300
MM = DPI / 25.4                      # px per mm
A4 = (210.0, 297.0)
CHECKER_D = 26.0                     # cut circle = checker diameter
PITCH = (31.0, 32.0)                 # sticker spacing x, y (room for the cut and a small label)
SQUARE = CHECKER_D / 2 ** 0.5        # 18.4 mm: biggest square inside the circle
ARUCO_MM = 13.5                      # black square incl. border (6 cells: 2.25 mm/cell, quiet zone >= 1 cell)
APRIL_MM = 13.5                      # tag36h11 black square (8 cells: 1.7 mm/cell)
QR_MM = 15.0                         # rules minimum: 21 modules -> 0.71 mm/module
ARUCO_IDS = [i for i in range(50) if i not in F.MARK_IDS][:16]   # 16 of each kind = 48 = a full sheet (6 x 8)
APRIL_IDS = list(range(16))
QR_TEXTS = ['QR%02d' % i for i in range(1, 11)] + ['A1', 'B2', 'C3', 'D4', 'E5', 'ETZ']
HERE = os.path.dirname(os.path.abspath(__file__))

def px(mm):
    return int(round(mm * MM))

def marker(dict_id, i, cells):
    d = cv2.aruco.getPredefinedDictionary(dict_id)
    return cv2.aruco.generateImageMarker(d, i, cells * 20)        # 20 px per cell, scaled later (nearest)

def qr(text):
    p = cv2.QRCodeEncoder_Params(); p.version = 1
    m = cv2.QRCodeEncoder.create(p).encode(text)
    ys, xs = np.nonzero(m < 128)                                   # strip the encoder's own quiet zone
    m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    assert m.shape == (21, 21), (text, m.shape)
    return m

def paste(page, img, cx, cy, size_mm):
    s = px(size_mm)
    im = cv2.resize(img, (s, s), interpolation=cv2.INTER_NEAREST)
    x0, y0 = cx - s // 2, cy - s // 2
    page[y0:y0 + s, x0:x0 + s] = im

def label(page, text, cx, cy):
    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
    cv2.putText(page, text, (cx - w // 2, cy + px(CHECKER_D / 2 + 3.2)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 110, 2, cv2.LINE_AA)

def make():
    page = np.full((px(A4[1]), px(A4[0])), 255, np.uint8)
    items = ([('aruco', i) for i in ARUCO_IDS] + [('april', i) for i in APRIL_IDS] + [('qr', t) for t in QR_TEXTS])
    cols = int((A4[0] - 10) // PITCH[0])
    x0 = (A4[0] - cols * PITCH[0]) / 2 + PITCH[0] / 2
    y0 = 14.0 + PITCH[1] / 2
    placed = []
    for n, (kind, v) in enumerate(items):
        r, c = divmod(n, cols)
        cx, cy = px(x0 + c * PITCH[0]), px(y0 + r * PITCH[1])
        if cy + px(PITCH[1] / 2) > page.shape[0] - px(8):
            print('sheet full, dropped from', kind, v); break
        cv2.circle(page, (cx, cy), px(CHECKER_D / 2), 170, 2, cv2.LINE_AA)                  # cut line
        if kind == 'aruco':
            paste(page, marker(cv2.aruco.DICT_4X4_50, v, 6), cx, cy, ARUCO_MM); label(page, 'ArUco %d' % v, cx, cy)
        elif kind == 'april':
            paste(page, marker(cv2.aruco.DICT_APRILTAG_36h11, v, 8), cx, cy, APRIL_MM); label(page, 'April %d' % v, cx, cy)
        else:
            paste(page, qr(v), cx, cy, QR_MM); label(page, 'QR "%s"' % v, cx, cy)
        placed.append((kind, v, cx, cy))
    # header and a 100 mm scale bar
    cv2.putText(page, 'ETZ checker stickers - print at 100 %, cut on the grey circles (26 mm)', (px(10), px(7)),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2, cv2.LINE_AA)
    yb = page.shape[0] - px(6)
    cv2.rectangle(page, (px(10), yb - px(1.5)), (px(110), yb), 0, -1)
    cv2.putText(page, '100 mm: measure me', (px(113), yb), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 0, 2, cv2.LINE_AA)
    return page, placed

def save_png(path, img):
    """PNG with a pHYs chunk so the printer knows it is 300 dpi (cv2 cannot write it)."""
    ok, buf = cv2.imencode('.png', img); b = buf.tobytes()
    ppm = int(round(DPI / 0.0254))
    data = struct.pack('>IIB', ppm, ppm, 1)
    chunk = struct.pack('>I', len(data)) + b'pHYs' + data + struct.pack('>I', zlib.crc32(b'pHYs' + data) & 0xffffffff)
    i = 8 + 25                                                     # after the signature and IHDR
    open(path, 'wb').write(b[:i] + chunk + b[i:])

def check(page, placed):
    """Read the sheet back as a camera at ~4 px/mm would, every sticker must be found with the right value."""
    small = cv2.resize(page, None, fx=0.35, fy=0.35, interpolation=cv2.INTER_AREA)       # 300 dpi -> ~4.1 px/mm
    bad = []
    found = {}
    for name, d in (('aruco', cv2.aruco.DICT_4X4_50), ('april', cv2.aruco.DICT_APRILTAG_36h11)):
        det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(d), cv2.aruco.DetectorParameters())
        cs, ids, _ = det.detectMarkers(small)
        found[name] = set() if ids is None else {int(i) for i in ids.flatten()}
    for kind, v, cx, cy in placed:
        if kind in found:
            if v not in found[kind]:
                bad.append((kind, v))
        else:
            h = px(CHECKER_D / 2 + 1)
            crop = page[cy - h:cy + h, cx - h:cx + h]
            crop = cv2.resize(crop, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
            t, _, _ = cv2.QRCodeDetector().detectAndDecode(crop)
            if t != v:
                bad.append((kind, v, t))
    extra = {n: s - {v for kk, v, _, _ in placed if kk == n} for n, s in found.items()}
    return bad, extra

if __name__ == '__main__':
    page, placed = make()
    out = os.path.join(HERE, 'out'); os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'stickers_a4.png')
    save_png(path, page)
    bad, extra = check(page, placed)
    print('%d stickers -> %s' % (len(placed), path))
    print('read back: %s, wrong extra ids: %s' % ('all found' if not bad else 'MISSING %s' % bad, extra))
    sys.exit(1 if bad or any(extra.values()) else 0)
