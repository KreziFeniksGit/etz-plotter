"""Export the whole device as coloured, grouped STEP and FreeCAD files.
Run inside FreeCAD (GUI needed for colours):  freecad export_gui.py
Writes out/ETZ_plotter_parked.step/.FCStd and out/ETZ_plotter_working.step/.FCStd,
plus every printed part (print orientation) in out/printed/ as STEP (no STL: slicers open STEP)."""
import os, sys, traceback
HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
sys.path.insert(0, HERE)
LOG = open(os.path.join(HERE, 'out', 'export_log.txt'), 'w')
try:
    import FreeCAD as App
    import FreeCADGui as Gui
    import ImportGui
    import assembly as A
    import wrist_module as W
    import frame as F
    import dfm

    BRANCH_ORDER = ['Base_and_Y_axis', 'Y_carriage_and_X_axis', 'Wrist_module', 'Electronics_and_controls', 'Cables_and_chains', 'Fasteners', 'Field_reference']

    def make_doc(name, parts):
        doc = App.newDocument(name)
        groups = {}
        top = doc.addObject('App::Part', 'ETZ_plotter')
        for b in BRANCH_ORDER:
            g = doc.addObject('App::Part', b)
            top.addObject(g)
            groups[b] = g
        for k, (s, grp, kind, col) in parts.items():
            o = doc.addObject('Part::Feature', k)
            o.Shape = s
            o.Label = k
            groups[A.branch(k, kind)].addObject(o)
            c = F.COL.get(col, (0.6, 0.6, 0.6))
            o.ViewObject.ShapeColor = c
            if A.branch(k, kind) == 'Field_reference':
                o.ViewObject.Transparency = 0
        doc.recompute()
        return doc, top

    out = os.path.join(HERE, 'out')
    for tag, pose in (('parked', (F.PYC0, F.PXB0, W.H_MAX, 0.0)), ('working', (250.0, 400.0, 5.0, 90.0))):
        parts = A.world(*pose, fasteners=True, detail=True)          # real vendor models where we have them
        doc, top = make_doc('ETZ_plotter_' + tag, parts)
        ImportGui.export([top], os.path.join(out, 'ETZ_plotter_%s.step' % tag))
        doc.saveAs(os.path.join(out, 'ETZ_plotter_%s.FCStd' % tag))
        LOG.write('%s: %d parts\n' % (tag, len(parts)))
        App.closeDocument(doc.Name)

    # printed parts, print orientation
    pdir = os.path.join(out, 'printed')
    os.makedirs(pdir, exist_ok=True)
    frame = F.build_frame()
    for k, (s, g, kind, col) in frame.items():
        if kind == 'printed':
            if k.startswith('y_beam_riser'):
                if k != 'y_beam_riser_40':
                    continue
                fn = 'y_beam_riser_x4'
            elif k.startswith('foot_'):
                if k != 'foot_1':
                    continue
                fn = 'foot_x4'
            else:
                fn = k
            ax, deg = A.print_orient(k)
            p = dfm.orient(s, ax, deg)
            p.exportStep(os.path.join(pdir, fn + '.step'))
    wparts, _ = W.build_all()
    for k, s in wparts.items():
        fn, (ax, deg), how, qty = W.PRINTED[k]
        p = dfm.orient(s, ax, deg)
        p.exportStep(os.path.join(pdir, 'wrist_' + k + '.step'))
    LOG.write('DONE\n')
except Exception:
    LOG.write(traceback.format_exc())
finally:
    LOG.close()
    os._exit(0)
