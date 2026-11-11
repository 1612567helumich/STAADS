"""Compara variantes del ND1 (JSON nombre -> cfg).  Cada variante se corre dos
veces: la primera para obtener los factores de escala del espectro y los modos
dominantes, la segunda ya con ellos."""
import sys, os, json, math, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nd1_eval
out = sys.argv[1]
variants = json.loads(open(sys.argv[2]).read())
only = sys.argv[3:] if len(sys.argv) > 3 else None
KEYS = ['COL', 'VR', 'VT', 'CS', 'CI', 'CSL', 'CIL', 'MON', 'DIA', 'DIAE', 'LC', 'LM', 'LMT', 'DIN', 'DINE', 'PC', 'PE']
for name, cfg in variants.items():
    if only and name not in only:
        continue
    t0 = time.time()
    cfg = dict(cfg)
    g, m = nd1_eval.build(cfg, out)
    rep = nd1_eval.evaluate(g, m, verbose=False)
    sf = rep['sf']
    cfg.update(FX=math.ceil(sf['X']['factor'] * 1000 - 1e-6) / 1000.0, FZ=math.ceil(sf['Z']['factor'] * 1000 - 1e-6) / 1000.0,
               DOM_X=sf['X']['dom'], DOM_Z=sf['Z']['dom'])
    g, m = nd1_eval.build(cfg, out)
    rep = nd1_eval.evaluate(g, m, verbose=False)
    mr = rep['maxratio']
    print('%-30s W=%6.0f kg (%.1f kg/m2)  deriva s=%.4f v=%.4f  part=%.1f/%.1f  T=%.3f/%.3f fX=%.3f fZ=%.3f  fallas=%d  (%.0f s)' % (
        name, rep['weight'], rep['weight'] / 240.0, rep['drift_s'], rep['drift_w'], rep['part'][0], rep['part'][1],
        rep['sf']['X']['T'], rep['sf']['Z']['T'], cfg['FX'], cfg['FZ'], len(rep['fails']), time.time() - t0))
    print('     ' + ' '.join('%s=%.2f' % (k, mr[k]) for k in KEYS if k in mr) + '  | TM=%.2f TMF=%.2f TC=%.2f' % (
        rep['rod_TM'], rep.get('rod_TMF', 0), rep['rod_TC']))
    sys.stdout.flush()
