"""
Camera on the test stand (camera_stand/): what the wrist camera will see, before the plotter exists.
Works close up, where the field marks are usually out of view, so everything is measured in the image itself:
  - focus: sharpness of the centre (variance of the Laplacian), with the best value seen so far.
    The Sandberg Flex is fixed focus (made for ~0.5 m and further): turn its lens to refocus close, watch this number.
  - checkers: coloured discs -> colour, diameter in px, px/mm (a checker is 26 mm) and the lens height that gives it.
  - QR codes (text), ArUco marks (id; 27/28/29 = field marks; if one is seen, checker field positions and cells too).
Keys: Q / Esc quit, S save a snapshot (laptop/snapshots), P print what is seen, B reset the best focus,
      C toggle checker search, + / - change the assumed horizontal FOV.
Run:  laptop\\.venv\\Scripts\\python laptop\\cam_stand.py [camera number, default 0] [width height]
Only tested without a camera (synthetic picture, --test). Numbers marked VERIFY come from a retailer page.
"""
import math, os, sys, time
import numpy as np
import cv2
import field as F
from vision import Vision, classify_hue, SAT_MIN, VAL_MIN, CHECKER_D
sys.stdout.reconfigure(encoding="utf-8")

HFOV_DEG = 72.0              # Sandberg Flex 1080P horizontal field of view (retailer spec, VERIFY with a ruler)
HERE = os.path.dirname(os.path.abspath(__file__))

def sharpness(img):
    """Variance of the Laplacian over the centre half of the picture: bigger = sharper (only compare at one scene)."""
    h, w = img.shape[:2]
    g = cv2.cvtColor(img[h // 4:3 * h // 4, w // 4:3 * w // 4], cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(g, cv2.CV_64F).var())

def focal_px(width, hfov_deg):
    return width / 2 / math.tan(math.radians(hfov_deg) / 2)

def find_checkers(img, min_d=20):
    """[(colour, cx, cy, d_px)] of saturated round blobs in the raw image. Close up one checker is big, so whole
    blobs are used (no merged neighbours expected at this scale); blobs cut by the image edge are skipped."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, (0, SAT_MIN, VAL_MIN), (180, 255, 255))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    H, W = mask.shape
    out = []
    for c in cs:
        area = cv2.contourArea(c)
        (cx, cy), r = cv2.minEnclosingCircle(c)
        if 2 * r < min_d or area < 0.6 * math.pi * r * r:          # too small or not round
            continue
        if cx - r < 2 or cy - r < 2 or cx + r > W - 2 or cy + r > H - 2:
            continue
        m = np.zeros_like(mask); cv2.drawContours(m, [c], -1, 255, -1)
        colour = classify_hue(hsv[..., 0][(m > 0) & (mask > 0)])
        d = 2 * math.sqrt(area / math.pi)                          # equal-area diameter: steadier than the enclosing circle
        out.append((colour, cx, cy, d))
    return out

def measure(img, f_px):
    """Everything this program reports for one frame."""
    ch = find_checkers(img)
    res = {'sharp': sharpness(img), 'checkers': []}
    for colour, cx, cy, d in ch:
        res['checkers'].append({'colour': colour, 'px': (round(cx), round(cy)), 'd_px': round(d, 1),
                                'px_per_mm': round(d / CHECKER_D, 2), 'height_mm': round(f_px * CHECKER_D / d, 1)})
    return res

def draw(img, res, marks, qrs, best, hfov, fps, tg=()):
    for kind, i, pts, ang in tg:
        col = (255, 255, 0) if kind == 'ArUco' else (0, 165, 255)
        cv2.polylines(img, [pts.astype(np.int32)], True, col, 3)
        cv2.circle(img, tuple(pts[0].astype(int)), 8, (0, 0, 255), -1)                    # corner 0 = tag's top-left
        c = pts.mean(axis=0).astype(int)
        cv2.putText(img, '%s %d  %.0f deg' % (kind, i, ang), (c[0] - 90, c[1]), cv2.FONT_HERSHEY_SIMPLEX, 1.0, col, 3)
    for c in res['checkers']:
        cx, cy = c['px']
        cv2.circle(img, (cx, cy), int(c['d_px'] / 2), (255, 255, 255), 2)
        cv2.putText(img, '%s %.1f px/mm h~%.0f' % (c['colour'], c['px_per_mm'], c['height_mm']), (cx - 60, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        if 'cell' in c:
            cv2.putText(img, '%s (%.0f, %.0f)' % (c['cell'] or '-', *c['field']), (cx - 60, cy + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    for i, pts in marks.items():
        cv2.polylines(img, [pts.astype(np.int32)], True, (0, 255, 0), 2)
        cv2.putText(img, 'mark %d' % i, tuple(pts[0].astype(int)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    for text, pts in qrs:
        cv2.polylines(img, [pts.astype(np.int32)], True, (255, 0, 255), 2)
        cv2.putText(img, 'QR: ' + text[:30], tuple(pts[0].astype(int)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 255), 2)
    h, w = img.shape[:2]
    cv2.rectangle(img, (w // 4, h // 4), (3 * w // 4, 3 * h // 4), (128, 128, 128), 1)    # focus area
    bar = int(min(1.0, res['sharp'] / max(best, 1e-6)) * 300)
    cv2.rectangle(img, (10, 10), (10 + bar, 30), (0, 200, 255), -1); cv2.rectangle(img, (10, 10), (310, 30), (255, 255, 255), 1)
    cv2.putText(img, 'focus %.0f (best %.0f)  FOV %.0f deg  %.0f fps' % (res['sharp'], best, hfov, fps), (320, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

QR = cv2.QRCodeDetectorAruco()   # on a real checker sticker (tight-cut, blue around): 40/40 frames vs 7/40 for the classic one

TAG_DETS = [(name, cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(d), cv2.aruco.DetectorParameters()))
            for name, d in (('ArUco', cv2.aruco.DICT_4X4_50), ('April', cv2.aruco.DICT_APRILTAG_36h11))]

def tags(img):
    """[(kind, id, corners 4x2, angle deg)] of checker tags: ArUco 4x4 (field marks 27/28/29 left out) and AprilTag 36h11.
    Angle = direction of the tag's top edge (corner 0 -> 1) in the image, 0 = pointing right, clockwise positive."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    out = []
    for name, det in TAG_DETS:
        cs, ids, _ = det.detectMarkers(g)
        for c, i in zip(cs, [] if ids is None else ids.flatten()):
            if name == 'ArUco' and int(i) in F.MARK_IDS:
                continue
            p = c[0]; dx, dy = p[1] - p[0]
            out.append((name, int(i), p, math.degrees(math.atan2(dy, dx))))
    return out

def qr_codes(img):
    ok, texts, pts, _ = QR.detectAndDecodeMulti(img)
    return [(t, p) for t, p in zip(texts, pts) if t] if ok else []

def add_field(res, v):
    """If a field mark is in view: checker centres in field mm and their cells."""
    for c in res['checkers']:
        fx, fy = v.to_field([c['px']])[0]
        c['field'] = (float(fx), float(fy)); c['cell'] = F.cell_name(*F.cell_of(fx, fy)) if F.cell_of(fx, fy) else None

def main():
    a = [x for x in sys.argv[1:] if not x.startswith('-')]
    cam = int(a[0]) if a else 0
    W, H = (int(a[1]), int(a[2])) if len(a) >= 3 else (1920, 1080)
    cap = cv2.VideoCapture(cam, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, W); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, H)
    if not cap.isOpened():
        print('camera %d not found - try cam_stand.py 1' % cam); return
    v, hfov, best, find, fps = Vision(), HFOV_DEG, 0.0, True, 0.0
    n, t0, qrs = 0, time.time(), []
    snaps = os.path.join(HERE, 'snapshots'); os.makedirs(snaps, exist_ok=True)
    while True:
        ok, img = cap.read()
        if not ok:
            print('no frame'); break
        f_px = focal_px(img.shape[1], hfov)
        res = measure(img, f_px) if find else {'sharp': sharpness(img), 'checkers': []}
        best = max(best, res['sharp'])
        if v.find_field(img):
            add_field(res, v)
        if n % 2 == 0:
            qrs = qr_codes(img)
        tg = tags(img)
        n += 1
        if time.time() - t0 > 1:
            fps, n, t0 = n / (time.time() - t0), 0, time.time()
        shown = img.copy()
        draw(shown, res, v.marks, qrs, best, hfov, fps, tg)
        cv2.imshow('cam stand', cv2.resize(shown, (shown.shape[1] * 960 // shown.shape[1], shown.shape[0] * 960 // shown.shape[1])))
        k = cv2.waitKey(1) & 0xFF
        if k in (27, ord('q')):
            break
        if k == ord('s'):
            p = os.path.join(snaps, time.strftime('cam_%H%M%S.png')); cv2.imwrite(p, img); print('saved', p)
        if k == ord('p'):
            print('focus %.0f' % res['sharp'], res['checkers'], [t for t, _ in qrs], sorted(v.marks),
                  ['%s %d %.0f deg' % (k, i, a) for k, i, _, a in tg])
        if k == ord('b'):
            best = 0.0
        if k == ord('c'):
            find = not find
        if k in (ord('+'), ord('=')):
            hfov += 1
        if k == ord('-'):
            hfov -= 1
    cap.release(); cv2.destroyAllWindows()

def selftest():
    """Synthetic picture: a red and a blue checker as a camera with HFOV_DEG would see them from 60 mm, and a QR code."""
    W, H, h = 1920, 1080, 60.0
    f = focal_px(W, HFOV_DEG); d = f * CHECKER_D / h
    img = np.full((H, W, 3), 235, np.uint8)
    cv2.circle(img, (480, 540), int(d / 2), (40, 40, 220), -1)              # red (BGR)
    cv2.circle(img, (1440, 540), int(d / 2), (220, 80, 30), -1)             # blue
    sharp1 = sharpness(img)
    res = measure(img, f)
    got = sorted((c['colour'], c['height_mm']) for c in res['checkers'])
    print('checkers', res['checkers'])
    assert [g[0] for g in got] == ['blue', 'red'], got
    assert all(abs(g[1] - h) < 1.5 for g in got), got
    blur = cv2.GaussianBlur(img, (31, 31), 10)
    assert sharpness(blur) < sharp1, 'blur must lower the focus score'
    qr = cv2.QRCodeEncoder.create().encode('ETZ test')
    qr = cv2.resize(qr, None, fx=12, fy=12, interpolation=cv2.INTER_NEAREST)
    img2 = np.full((H, W, 3), 255, np.uint8); img2[100:100 + qr.shape[0], 100:100 + qr.shape[1]] = qr[..., None]
    q = [t for t, _ in qr_codes(img2)]
    assert q == ['ETZ test'], q
    img3 = np.full((H, W, 3), 255, np.uint8)
    for x0, d, i in ((200, cv2.aruco.DICT_4X4_50, 7), (900, cv2.aruco.DICT_APRILTAG_36h11, 5), (1500, cv2.aruco.DICT_4X4_50, 27)):
        m = cv2.aruco.generateImageMarker(cv2.aruco.getPredefinedDictionary(d), i, 320)
        img3[300:620, x0:x0 + 320] = m[..., None]
    rot = cv2.warpAffine(img3, cv2.getRotationMatrix2D((W / 2, H / 2), -30, 0.8), (W, H), borderValue=(255, 255, 255))
    got = sorted((k, i, round(a)) for k, i, _, a in tags(rot))
    assert [(k, i) for k, i, _ in got] == [('April', 5), ('ArUco', 7)], got          # field mark 27 left out
    assert all(abs(a - 30) <= 2 for _, _, a in got), got
    print('cam_stand selftest: ok (checkers, height from size, focus score, QR, ArUco + AprilTag ids and angle)')

if __name__ == '__main__':
    selftest() if '--test' in sys.argv else main()
