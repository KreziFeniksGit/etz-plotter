"""
Shows a test field full-screen (for a camera looking at the laptop screen, when there is no printer).
Keys: N = new random checkers and QR stickers, Q / Esc = quit. The true layout is printed in the console.
Run:  laptop\\.venv\\Scripts\\python laptop\\show_field.py
"""
import random
import cv2
import field as F

def random_layout(n_checkers=6, n_qr=3):
    cells = [(c, r) for c in range(0, F.LAYOUT['cols'] + 1) for r in range(1, F.LAYOUT['rows'] + 1)]
    random.shuffle(cells)
    checkers = [(c, r, random.choice(F.COLOURS)) for c, r in cells[:n_checkers]]
    stickers = [(c, r, 'TASK-%d' % random.randint(1, 99)) for c, r in cells[n_checkers:n_checkers + n_qr]]
    return checkers, stickers

def main():
    win = 'ETZ test field'
    cv2.namedWindow(win, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(win, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    while True:
        checkers, stickers = random_layout()
        print('\nshown now:')
        for c, r, col in checkers:
            print('  checker %-8s in %s' % (col, F.cell_name((c, r))))
        for c, r, t in stickers:
            print('  QR      %-8s in %s' % (t, F.cell_name((c, r))))
        cv2.imshow(win, F.render(5.0, checkers, stickers))
        k = cv2.waitKey(0) & 0xFF
        if k in (ord('q'), 27):
            break
    cv2.destroyAllWindows()

if __name__ == '__main__':
    main()
