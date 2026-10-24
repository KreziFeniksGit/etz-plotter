"""
Live camera test: finds the field (ArUco 27/28/29), the coloured checkers and the QR codes, and shows them.
Windows: "camera" (what was found, drawn on the image) and "top view" (the sheet straightened, 4 px/mm).
Keys: Q / Esc quit, R careful QR search, S save a snapshot, P print what is seen.
Run:  laptop\\.venv\\Scripts\\python laptop\\camera_test.py [camera number, default 0]
"""
import sys, time
import cv2
import field as F
sys.stdout.reconfigure(encoding="utf-8")      # Cyrillic cell names (А0 ... Е8) on any Windows console
from vision import Vision, annotate

def main():
    cam = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    cap = cv2.VideoCapture(cam, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))      # compressed: webcams give full fps only this way
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280); cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if not cap.isOpened():
        print('camera %d not found - try camera_test.py 1' % cam); return
    v = Vision()
    last = ''
    n, t0, fps, qr = 0, time.time(), 0.0, []
    while True:
        ok, img = cap.read()
        if not ok:
            print('no frame'); break
        found = v.find_field(img)
        ch = v.checkers(img) if found else []
        if n % 5 == 0:
            qr = v.qrcodes(img)                     # the quick QR search a few times a second (R = careful search)
        n += 1
        if n % 10 == 0:
            fps = 10 / (time.time() - t0); t0 = time.time()
        out = annotate(img, v, ch, qr)
        if not found:
            cv2.putText(out, 'field not found: need 2 of the marks 27 / 28 / 29 in view', (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        cv2.putText(out, '%.1f fps' % fps, (out.shape[1] - 130, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
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
        if k == ord('r') and found:
            t = time.time(); qr = v.qrcodes(img, thorough=True)
            print('careful QR search: %d found in %.1f s' % (len(qr), time.time() - t))
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
