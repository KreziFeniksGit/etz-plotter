"""
Helpers for the hand-routed (not auto-routed) single-sided home boards: place footprints, read pad positions,
lay tracks along given waypoints, GND pour, save with the home rules. Used by build_drivers.py (and the other split boards).
Run the board scripts with KiCad's Python.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.argv = [sys.argv[0], '--no-route']
import pcbnew
import build_pcb as B          # footprints (B.F), home pad shapes, home rules (HOME = True)

def mm(x, y):
    return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))

class Board:
    def __init__(self, w, h, title):
        self.b = pcbnew.BOARD()
        self.w, self.h = w, h
        self.nets = {}
        self.fp = {}
        r = pcbnew.PCB_SHAPE(self.b)
        r.SetShape(pcbnew.SHAPE_T_RECT); r.SetStart(mm(0, 0)); r.SetEnd(mm(w, h))
        r.SetLayer(pcbnew.Edge_Cuts); r.SetWidth(pcbnew.FromMM(0.1))
        self.b.Add(r)
        for layer, mirror, txt in ((pcbnew.F_SilkS, False, title), (pcbnew.B_Cu, True, title.upper())):
            t = pcbnew.PCB_TEXT(self.b); t.SetText(txt); t.SetLayer(layer); t.SetMirrored(mirror)
            t.SetPosition(mm(w / 2, h - 2.5))
            t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.3), pcbnew.FromMM(1.3))); t.SetTextThickness(pcbnew.FromMM(0.25))
            self.b.Add(t)

    def net(self, name):
        if name not in self.nets:
            self.nets[name] = pcbnew.NETINFO_ITEM(self.b, name)
            self.b.Add(self.nets[name])
        return self.nets[name]

    def part(self, ref, key, value, x, y, rot=0.0, pads=None):
        lib, name = B.F[key].split(':')
        fp = pcbnew.FootprintLoad(os.path.join(B.FP, lib + '.pretty'), name)
        fp.SetReference(ref); fp.SetValue(value)
        fp.SetPosition(mm(x, y)); fp.SetOrientationDegrees(rot)
        if ref.startswith('H'):
            fp.Reference().SetVisible(False)
        if ref.startswith('J'):
            v = fp.Value(); v.SetLayer(pcbnew.F_SilkS); v.SetVisible(True)
            v.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.9), pcbnew.FromMM(0.9))); v.SetTextThickness(pcbnew.FromMM(0.15))
        self.b.Add(fp)
        B.home_pads(fp)
        for p in fp.Pads():
            p.SetThermalSpokeAngleDegrees(0)          # straight spokes: diagonal ones find no room between 2.54 mm pins
            n = (pads or {}).get(int(p.GetNumber())) if p.GetNumber().isdigit() else None
            if n:
                p.SetNet(self.net(n))
        self.fp[ref] = fp
        return fp

    def pad(self, ref, num):
        """(x, y) of a pad centre in mm"""
        for p in self.fp[ref].Pads():
            if p.GetNumber() == str(num):
                q = p.GetPosition()
                return (pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))
        raise KeyError((ref, num))

    def track(self, pts, net, width, layer=None):
        """copper track through the waypoints (mm); bottom copper unless layer = pcbnew.F_Cu (= a wire link on the top)"""
        n = self.net(net)
        for a, b in zip(pts[:-1], pts[1:]):
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(mm(*a)); t.SetEnd(mm(*b)); t.SetWidth(pcbnew.FromMM(width))
            t.SetLayer(pcbnew.B_Cu if layer is None else layer); t.SetNet(n)
            self.b.Add(t)

    def link(self, ref, net, a, b, first_exists=False):
        """wire link: two 2 mm through-hole pads joined by an insulated wire on the component side (drawn as a top track).
        first_exists: the first end is a pad of an earlier link (a chain of links)"""
        for k, q in enumerate((a, b)):
            if k == 0 and first_exists:
                continue
            fp = self.part('%s%s' % (ref, 'AB'[k]), 'tp', 'wire link', q[0], q[1], 0, {1: net})
            for p in fp.Pads():
                ls = pcbnew.LSET()
                for l in (pcbnew.F_Cu, pcbnew.B_Cu, pcbnew.F_Mask, pcbnew.B_Mask):
                    ls.AddLayer(l)
                p.SetLayerSet(ls)
        self.track([a, b], net, 0.8, pcbnew.F_Cu)

    def holes(self, inset=4.0):
        for k, (x, y) in enumerate(((inset, inset), (self.w - inset, inset), (inset, self.h - inset), (self.w - inset, self.h - inset))):
            self.part('H%d' % (k + 1), 'hole', 'M3', x, y)

    def gnd_pour(self, clearance=0.6):
        z = pcbnew.ZONE(self.b)
        z.SetLayer(pcbnew.B_Cu); z.SetNet(self.net('GND'))
        z.SetLocalClearance(pcbnew.FromMM(clearance)); z.SetMinThickness(pcbnew.FromMM(0.6))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(pcbnew.FromMM(0.6)); z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.8))
        ol = z.Outline(); ol.NewOutline()
        for x, y in ((1, 1), (self.w - 1, 1), (self.w - 1, self.h - 1), (1, self.h - 1)):
            ol.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
        self.b.Add(z)

    def save(self, path):
        B.set_rules(self.b)
        pcbnew.ZONE_FILLER(self.b).Fill(self.b.Zones())
        pcbnew.SaveBoard(path, self.b)
        b2 = pcbnew.LoadBoard(path)          # attach the .kicad_pro (net classes)
        B.set_rules(b2)
        pcbnew.ZONE_FILLER(b2).Fill(b2.Zones())
        pcbnew.SaveBoard(path, b2)

def drc(path):
    import subprocess, json, collections
    cli = os.path.join(os.path.dirname(sys.executable), 'kicad-cli.exe')
    rep = path[:-10] + '_drc.json'
    subprocess.run([cli, 'pcb', 'drc', '--format', 'json', '--refill-zones', '-o', rep, path], capture_output=True)
    d = json.load(open(rep))
    v = [x for x in d['violations'] if 'silk' not in x['type']]
    return d['unconnected_items'], v

def render(path, png, side='bottom'):
    import subprocess
    cli = os.path.join(os.path.dirname(sys.executable), 'kicad-cli.exe')
    subprocess.run([cli, 'pcb', 'render', '--side', side, '--width', '1400', '--height', '1600', '--quality', 'basic', '-o', png, path],
                   capture_output=True)
