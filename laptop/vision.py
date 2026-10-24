"""
Vision: camera image -> field coordinates (mm) -> checkers with colour and cell, QR codes with text and cell.
Own algorithms on top of OpenCV primitives (allowed by the rules): ArUco detection, homography, HSV thresholds, contours.
"""
import numpy as np
import cv2
import field as F

PX_MM = 2.5                       # resolution of the straightened view (2.5 px/mm: a 26 mm checker = 65 px, plenty)
CHECKER_D = 26.0                  # checker diameter, mm (rules)
SAT_MIN, VAL_MIN = 80, 60         # "coloured" = saturated and not dark (screens / prints differ: tune here)
HUE = [('red', 0, 9), ('yellow', 18, 38), ('green', 39, 88), ('blue', 89, 130), ('magenta', 131, 166), ('red', 167, 180)]

class Vision:
    def __init__(self):
        self.det = cv2.aruco.ArucoDetector(cv2.aruco.getPredefinedDictionary(F.ARUCO_DICT), cv2.aruco.DetectorParameters())
        self.qr = cv2.QRCodeDetectorAruco()        # sturdier finder than the classic one
        self.qr1 = cv2.QRCodeDetector()
        self.H = None              # image -> field mm
        self.marks = {}

    # ------------------------------------------------------------ field
    def find_field(self, img):
        """Homography from the ArUco marks: ONE mark (4 corners) is enough - the wrist camera rarely sees more.
        More marks in view = more accurate far from them. Returns True if found."""
        corners, ids, _ = self.det.detectMarkers(img)
        self.marks = {}
        src, dst = [], []
        if ids is not None:
            for c, i in zip(corners, ids.flatten()):
                if int(i) in F.MARK_IDS:
                    self.marks[int(i)] = c.reshape(4, 2)
                    src.extend(c.reshape(4, 2)); dst.extend(F.mark_corners_field(int(i)))
        if len(self.marks) >= 1:
            self.H, _ = cv2.findHomography(np.array(src, np.float32), np.array(dst, np.float32), cv2.RANSAC, 3.0)
            return self.H is not None
        return False

    def to_field(self, pts):
        p = cv2.perspectiveTransform(np.array(pts, np.float32).reshape(-1, 1, 2), self.H)
        return p.reshape(-1, 2)

    def to_image(self, pts):
        p = cv2.perspectiveTransform(np.array(pts, np.float32).reshape(-1, 1, 2), np.linalg.inv(self.H))
        return p.reshape(-1, 2)

    def topdown(self, img):
        """Straightened view of the field area F.VIEW, PX_MM pixels per mm (y up on the field = up in the picture)."""
        x0, y0, x1, y1 = F.VIEW
        s = PX_MM
        T = np.array([[s, 0, -x0 * s], [0, -s, y1 * s], [0, 0, 1]], np.float64)      # field mm -> view pixel
        return cv2.warpPerspective(img, T @ self.H, (int((x1 - x0) * s), int((y1 - y0) * s))), T

    # ------------------------------------------------------------ checkers
    def checkers(self, img):
        """[(colour, x_mm, y_mm, cell)] of coloured discs about 26 mm across.
        Checkers in neighbouring cells are only 2 mm apart and merge in the mask, so centres are found as the peaks of
        the distance transform (the middle of each disc is the point furthest from its edge), not as whole blobs."""
        top, T = self.topdown(img)
        hsv = cv2.cvtColor(top, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, (0, SAT_MIN, VAL_MIN), (180, 255, 255))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        R = CHECKER_D / 2 * PX_MM
        dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        peaks = (dist >= 0.65 * R) & (dist == cv2.dilate(dist, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(1.2 * R),) * 2)))
        ys, xs = np.nonzero(peaks)
        centres = []
        for x, y in sorted(zip(xs, ys), key=lambda p: -dist[p[1], p[0]]):      # strongest first, drop near-duplicates
            if all((x - a) ** 2 + (y - b) ** 2 > (1.2 * R) ** 2 for a, b in centres):
                centres.append((x, y))
        out = []
        r = int(0.6 * R)
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        inside = xx ** 2 + yy ** 2 <= r * r
        for cx, cy in centres:
            x0, y0 = int(cx) - r, int(cy) - r
            if x0 < 0 or y0 < 0 or x0 + 2 * r + 1 > mask.shape[1] or y0 + 2 * r + 1 > mask.shape[0]:
                continue                                       # disc cut by the edge of the view: skip
            sl = (slice(y0, y0 + 2 * r + 1), slice(x0, x0 + 2 * r + 1))
            h = hsv[..., 0][sl][inside & (mask[sl] > 0)]
            colour = classify_hue(h)
            fx, fy = (np.linalg.inv(T) @ np.array([cx, cy, 1.0]))[:2]
            out.append((colour, float(fx), float(fy), F.cell_of(fx, fy)))
        return sorted(out, key=lambda t: (t[3] or (99, 99)))

    # ------------------------------------------------------------ QR codes
    def qrcodes(self, img, thorough=False):
        """[(text, x_mm, y_mm, cell, corners_in_image)]: the whole picture at once (fast); with thorough=True also
        every visible cell on its own, straightened and enlarged (slow, but reads small tilted codes)."""
        out, seen = [], set()
        try:
            ok, texts, pts, _ = self.qr.detectAndDecodeMulti(img)
        except cv2.error:
            ok, texts, pts = False, [], None
        if ok and pts is not None:
            for t, p in zip(texts, pts):
                if not t:
                    continue
                c = p.reshape(4, 2).mean(axis=0)
                fx, fy = self.to_field([c])[0] if self.H is not None else (np.nan, np.nan)
                cell = F.cell_of(fx, fy) if self.H is not None else None
                seen.add(cell)
                out.append((t, float(fx), float(fy), cell, p.reshape(4, 2)))
        if self.H is None or not thorough:
            return out
        s = 10.0                                               # px per mm for the cell crops
        hh, ww = img.shape[:2]
        for col, row in F.all_cells():
                if (col, row) in seen:
                    continue
                px, py = self.to_image([F.cell_centre(col, row)])[0]
                if not (0 <= px < ww and 0 <= py < hh):        # cell not in the picture
                    continue
                fx, fy = F.cell_centre(col, row)
                h = F.CELL / 2 + 2.0
                # field square around the cell -> crop image (y up -> y down)
                dst = np.float32([[0, 0], [2 * h * s, 0], [2 * h * s, 2 * h * s], [0, 2 * h * s]])
                src = self.to_image([(fx - h, fy + h), (fx + h, fy + h), (fx + h, fy - h), (fx - h, fy - h)]).astype(np.float32)
                crop = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (int(2 * h * s), int(2 * h * s)))
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                t, p = '', None
                sharp = cv2.addWeighted(gray, 1.8, cv2.GaussianBlur(gray, (0, 0), 2.0), -0.8, 0)     # unsharp mask
                for g in (gray, sharp, cv2.threshold(sharp, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]):
                    t, p, _ = self.qr1.detectAndDecode(g)
                    if t:
                        break
                if t:
                    corners = self.to_image([(fx - h + q[0] / s, fy + h - q[1] / s) for q in p.reshape(4, 2)])
                    out.append((t, fx, fy, (col, row), corners))
        return out

def classify_hue(h):
    """hue values of one blob (OpenCV 0..180) -> colour name; red wraps around 0/180, so it is counted from both ends"""
    if len(h) == 0:
        return '?'
    votes = {}
    for name, lo, hi in HUE:
        votes[name] = votes.get(name, 0) + int(((h >= lo) & (h <= hi)).sum())
    best = max(votes, key=votes.get)
    return best if votes[best] > 0.5 * len(h) else '?'

def annotate(img, v, checkers, qrs):
    """draw what was found on the camera image"""
    out = img.copy()
    for i, c in v.marks.items():
        cv2.polylines(out, [c.astype(int)], True, (0, 255, 0), 2)
        cv2.putText(out, str(i), tuple(c[0].astype(int)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    if v.H is not None:
        c = F.CELL
        x0, x1, y0, y1 = -c * (F.COLS + 0.5), -c * 0.5, -c * 0.5, c * (F.ROWS - 0.5)
        for k in range(F.COLS + 1):
            a, b = v.to_image([(x0 + k * c, y0), (x0 + k * c, y1)])
            cv2.line(out, tuple(a.astype(int)), tuple(b.astype(int)), (255, 200, 0), 1)
        for k in range(F.ROWS + 1):
            a, b = v.to_image([(x0, y0 + k * c), (x1, y0 + k * c)])
            cv2.line(out, tuple(a.astype(int)), tuple(b.astype(int)), (255, 200, 0), 1)
        for colour, fx, fy, cell in checkers:
            p = v.to_image([(fx, fy)])[0].astype(int)
            cv2.circle(out, tuple(p), 6, (255, 255, 255), -1)
            cv2.putText(out, '%s %s' % (colour, F.cell_name(cell, latin=True)), (p[0] + 8, p[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    for t, fx, fy, cell, p in qrs:
        cv2.polylines(out, [p.astype(int)], True, (0, 0, 255), 2)
        cv2.putText(out, 'QR "%s" %s' % (t, F.cell_name(cell, latin=True)), tuple(p[0].astype(int)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
    return out
