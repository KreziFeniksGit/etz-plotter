"""
Self-test without a camera: draws a field with known checkers and QR codes, photographs it "badly" (perspective,
blur, noise, darker, colour cast like a screen), runs the vision and checks it finds everything in the right cells.
Run:  laptop\\.venv\\Scripts\\python laptop\\selftest.py
"""
import random
import numpy as np
import cv2
import field as F
from vision import Vision

def fake_photo(img, seed):
    rng = np.random.default_rng(seed)
    h, w = img.shape[:2]
    big = np.full((int(h * 1.5), int(w * 1.5), 3), 40, np.uint8)
    big[h // 4:h // 4 + h, w // 4:w // 4 + w] = img
    H2, W2 = big.shape[:2]
    j = lambda: rng.uniform(-0.08, 0.08)
    src = np.float32([[0, 0], [W2, 0], [W2, H2], [0, H2]])
    dst = np.float32([[W2 * j(), H2 * j()], [W2 * (1 + j()), H2 * j()], [W2 * (1 + j()), H2 * (1 + j())], [W2 * j(), H2 * (1 + j())]])
    out = cv2.warpPerspective(big, cv2.getPerspectiveTransform(src, dst), (W2, H2), borderValue=(40, 40, 40))
    out = cv2.GaussianBlur(out, (5, 5), 1.0)
    out = out.astype(np.float32) * rng.uniform(0.7, 1.0) + rng.normal(0, 6, out.shape)
    out[..., 0] *= rng.uniform(0.9, 1.1); out[..., 2] *= rng.uniform(0.9, 1.1)          # screen-like colour cast
    return np.clip(out, 0, 255).astype(np.uint8)

def main(trials=10):
    v = Vision()
    good = 0
    for t in range(trials):
        random.seed(t)
        cells = F.all_cells()
        random.shuffle(cells)
        ch = [(c, r, random.choice(F.COLOURS)) for c, r in cells[:6]]
        st = [(c, r, 'T%d' % k) for k, (c, r) in enumerate(cells[6:9])]
        img = fake_photo(F.render(8.0, ch, st), t)          # 8 px/mm: a 1080p camera seeing ~ 240 mm, or closer
        found = v.find_field(img)
        got_ch = {(cell, col) for col, _, _, cell in v.checkers(img)} if found else set()
        got_qr = {(cell, txt) for txt, _, _, cell, _ in v.qrcodes(img)}
        want_ch = {((c, r), col) for c, r, col in ch}
        want_qr = {((c, r), txt) for c, r, txt in st}
        ok = found and got_ch == want_ch and got_qr == want_qr
        good += ok
        print('trial %d: field %s, checkers %d/%d, QR %d/%d %s' % (
            t, 'ok' if found else 'NOT FOUND', len(got_ch & want_ch), len(want_ch), len(got_qr & want_qr), len(want_qr),
            'OK' if ok else '<- missed %s %s extra %s %s' % (want_ch - got_ch, want_qr - got_qr, got_ch - want_ch, got_qr - want_qr)))
    print('%d / %d trials fully correct' % (good, trials))

if __name__ == '__main__':
    main()
