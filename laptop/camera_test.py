"""
Live camera test: finds the field (ArUco 27/28/29), the coloured checkers and the QR codes, and shows them.
Windows: "camera" (what was found, drawn on the image) and "top view" (the sheet straightened, 4 px/mm).
Keys: Q / Esc quit, S save a snapshot, P print what is seen.
Run:  laptop\\.venv\\Scripts\\python laptop\\camera_test.py [camera number, default 0]
"""
import sys, time
import cv2
import field as F
from vision import Vision, annotate

def main():
    cam = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    cap = cv2.VideoCapture(cam, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    if not cap.isOpened():
        print('camera %d not found - try camera_test.py 1' % cam); return
    v = Vision()
    last = ''
    while True:
        ok, img = cap.read()
        if not ok:
            print('no frame'); break
        found = v.find_field(img)
        ch = v.checkers(img) if found else []
        qr = v.qrcodes(img)
        out = annotate(img, v, ch, qr)
        if not found:
            cv2.putText(out, 'field not found: need 2 of the marks 27 / 28 / 29 in view', (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.imshow('camera', cv2.resize(out, None, fx=0.6, fy=0.6) if out.shape[1] > 1400 else out)
        if found:
            top, _ = v.topdown(img)
            cv2.imshow('top view', cv2.resize(top, None, fx=0.7, fy=0.7))
        text = '; '.join('%s %s' % (c, F.cell_name(cell)) for c, _, _, cell in ch) + \
               ' | ' + '; '.join('QR %s %s' % (t, F.cell_name(cell)) for t, _, _, cell, _ in qr)
        if text != last:
            print(time.strftime('%H:%M:%S'), text); last = text
        k = cv2.waitKey(1) & 0xFF
        if k in (ord('q'), 27):
            break
        if k == ord('s'):
            fn = 'snap_%s.png' % time.strftime('%H%M%S'); cv2.imwrite(fn, img); print('saved', fn)
        if k == ord('p'):
            for c, x, y, cell in ch:
                print('  checker %-8s %s  (%.1f, %.1f) mm' % (c, F.cell_name(cell), x, y))
            for t, x, y, cell, _ in qr:
                print('  QR %-12s %s  (%.1f, %.1f) mm' % (t, F.cell_name(cell), x, y))
    cap.release(); cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
