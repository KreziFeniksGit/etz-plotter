"""read a KiCad (kicadsexpr) netlist: components {ref: dict(value, footprint, tstamp)} and nets {name: [(ref, pin)]}"""
import re

def parse(text):
    tok = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()"]+')
    stack, cur = [], []
    for m in tok.finditer(text):
        t = m.group(0)
        if t == '(':
            stack.append(cur); cur = []
        elif t == ')':
            done = cur; cur = stack.pop(); cur.append(done)
        elif t[0] == '"':
            cur.append(t[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        else:
            cur.append(t)
    return cur[0]

def kid(e, key):
    for k in e:
        if isinstance(k, list) and k and k[0] == key:
            return k
    return None

def read(path, keep_unconnected=False):
    root = parse(open(path, encoding='utf-8').read())
    comps, nets = {}, {}
    for c in kid(root, 'components')[1:]:
        ts = kid(c, 'tstamps')
        comps[kid(c, 'ref')[1]] = dict(value=kid(c, 'value')[1], footprint=kid(c, 'footprint')[1],
                                       tstamp=ts[1] if ts else '')
    for n in kid(root, 'nets')[1:]:
        name = kid(n, 'name')[1].lstrip('/')
        nodes = [(kid(a, 'ref')[1], kid(a, 'pin')[1]) for a in n if isinstance(a, list) and a[0] == 'node']
        if keep_unconnected or not name.startswith('unconnected-'):
            nets[name] = nodes
    return comps, nets
