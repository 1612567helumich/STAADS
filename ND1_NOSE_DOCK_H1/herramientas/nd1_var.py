import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nd1_eval
out = sys.argv[1]
variants = json.loads(open(sys.argv[2]).read())
for name, cfg in variants.items():
    g, m = nd1_eval.build(cfg, out)
    rep = nd1_eval.evaluate(g, m, verbose=False)
    mr = rep['maxratio']
    keys = ['COL', 'VR', 'VT', 'CS', 'CI', 'CSL', 'CIL', 'MON', 'DIA', 'DIAE', 'LC', 'LM', 'DIN', 'DINE', 'PC', 'PE']
    print('%-26s W=%6.0f kg  deriva s=%.4f v=%.4f  part=%.1f/%.1f  fX=%.3f fZ=%.3f  fallas=%d' % (name, rep['weight'], rep['drift_s'], rep['drift_w'], rep['part'][0], rep['part'][1], rep['sf']['X']['factor'], rep['sf']['Z']['factor'], len(rep['fails'])))
    print('     ' + ' '.join('%s=%.2f' % (k, mr[k]) for k in keys if k in mr) + '  | TM=%.2f TMF=%.2f TC=%.2f' % (rep['rod_TM'], rep.get('rod_TMF', 0), rep['rod_TC']))
