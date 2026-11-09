"""print each footprint's courtyard box and pad offsets (rotation 0) - helper for planning the placement"""
import os, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nl
FP = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), 'share', 'kicad', 'footprints')
comps, nets = nl.read(os.path.join(HERE, 'etz_test.net'))
seen = set()
mm = pcbnew.ToMM
for ref, c in comps.items():
    fpid = c['footprint']
    if fpid in seen: continue
    seen.add(fpid)
    lib, name = fpid.split(':')
    fp = pcbnew.FootprintLoad(os.path.join(HERE, 'etz.pretty') if lib == 'etz' else os.path.join(FP, lib + '.pretty'), name)
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox()
    print('%-5s %-60s x %.1f..%.1f y %.1f..%.1f' % (ref, fpid, mm(bb.GetX()), mm(bb.GetRight()), mm(bb.GetY()), mm(bb.GetBottom())))
    print('      ', ' '.join('%s(%.2f,%.2f)' % (p.GetNumber(), mm(p.GetPosition().x), mm(p.GetPosition().y)) for p in fp.Pads())[:200])
