import time; t=time.time()
import frame as F
P = F.build_frame()
bad = []
for k, (s, g, kind, col) in P.items():
    if s is None or s.isNull() or not s.isValid():
        bad.append(k)
print('parts', len(P), 'bad', bad, 'fillet skips', F.W.FILLET_LOG, round(time.time()-t,1), 's')
for k, (s, g, kind, col) in P.items():
    if kind == 'printed':
        print('%-18s vol %8.0f  solids %d  bbox %s' % (k, s.Volume, len(s.Solids), [round(v,1) for v in (s.BoundBox.XLength, s.BoundBox.YLength, s.BoundBox.ZLength)]))
