import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import nd1_eval
from staadlite import design
std = sys.argv[1]; cfg = json.loads(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].startswith('{') else {}
tags = sys.argv[3].split(',') if len(sys.argv) > 3 else ['LM']
nshow = int(sys.argv[4]) if len(sys.argv) > 4 else 12
g, m = nd1_eval.build(cfg, std)
rep = nd1_eval.evaluate(g, m, verbose=False)
R = rep['R']
for tag in tags:
    lst = sorted(((rep['design'][e]['ratio'], e) for e in g.bytag[tag]), reverse=True)[:nshow]
    print('==', tag)
    for r, e in lst:
        d = rep['design'][e]; a, b = m.members[e]
        f = d['forces']; p = d['parts']; c = d['cap']
        print('  m%-4d %s->%s L=%6.1f  rel=%.3f lc%d x=%5.1f %-9s P=%8.1f Vy=%8.1f Vz=%8.1f My=%9.1f Mz=%10.1f | pr=%.3f mx=%.3f my=%.3f | Pc=%.0f Mcx=%.0f Mcy=%.0f  %s' % (
            e, tuple(round(v, 1) for v in m.nodes[a]), tuple(round(v, 1) for v in m.nodes[b]), g.L(e), r, d['lc'], d['loc'], d['ref'], f['P'], f['Vy'], f['Vz'], f['My'], f['Mz'],
            p['pr'], p['mx'], p['my'], c.Pc, c.Mcx, c.Mcy, {k: v for k, v in g.minfo[e].items() if k not in ('tag', 'rel')}))
