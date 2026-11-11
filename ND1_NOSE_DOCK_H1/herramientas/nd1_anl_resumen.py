"""Sustituye en el resumen del modelo (JSON de nd1_final.py) los datos que usan
las hojas de calculo por los valores reales de una corrida de STAAD (.ANL):
tabla modal, peso sismico, reacciones del caso 4 y STEEL TAKE-OFF.

uso: python3 nd1_anl_resumen.py resumen.json RESULTADOS.ANL resumen_anl.json"""
import sys, os, json, re, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from staadlite import anlread
import nd1_eval

RHO = 0.00783341          # kg/cm3 (material STEEL del modelo)


def takeoff(anl):
    L = open(anl, 'r', encoding='latin-1').read().splitlines()
    out = {}
    for i, l in enumerate(L):
        if 'STEEL TAKE-OFF' in l and any('PROFILE' in x for x in L[i:i + 5]):
            j = i
            while j < len(L) and 'TOTAL =' not in L[j]:
                m = re.match(r'\s+ST\s+(\S+)\s+([\d.]+)\s+([\d.]+)\s*$', L[j])
                if m:
                    out[m.group(1)] = dict(L=float(m.group(2)), W=float(m.group(3)))
                m = re.match(r'\s+PRISMATIC STEEL\s+([\d.]+)\s+([\d.]+)\s*$', L[j])
                if m:
                    out['PRISMATIC STEEL'] = dict(L=float(m.group(1)), W=float(m.group(2)))
                j += 1
            out['TOTAL'] = float(re.search(r'TOTAL =\s+([\d.]+)', L[j]).group(1))
            return out
    raise ValueError('no se encontro el STEEL TAKE-OFF')


def weights(anl):
    """Peso sismico = MODAL WEIGHT + |MISSING WEIGHT| (direcciones X y Z)."""
    txt = open(anl, 'r', encoding='latin-1').read()
    mm = re.search(r'MISSING WEIGHT X Y Z\s+(\S+)\s+(\S+)\s+(\S+)', txt)
    mw = re.search(r'MODAL WEIGHT X Y Z\s+(\S+)\s+(\S+)\s+(\S+)', txt)
    mis = [abs(float(mm.group(k))) for k in (1, 2, 3)]
    mod = [float(mw.group(k)) for k in (1, 2, 3)]
    return mod[0] + mis[0], mod[2] + mis[2]


def main(resumen, anl, out):
    S = json.load(open(resumen))
    c = dict(nd1_eval.nd1_std.Gen().c)
    c.update({k: v for k, v in S['cfg'].items() if k != 'SEC'})
    # ------------------------------------------------ tabla modal de STAAD
    fr = anlread.frequencies(anl)
    pa = anlread.participation(anl)
    wx, wz = weights(anl)
    W = round(wx, 2)
    rows = []
    for k in range(1, nd1_eval.SHEET_MODES + 1):
        f, T = fr[k]
        rows.append(dict(mode=k, f=f, T=T, px=pa[k][0], pz=pa[k][2], csm=nd1_eval.csm_sheet(c, nd1_eval._xl_round(T, 2))))
    old = S['sheet']
    new = dict(rows=rows, W=W, hn=old['hn'], Ta=old['Ta'], cs_a=old['cs_a'])
    for d, key in (('X', 'px'), ('Z', 'pz')):
        vb = [r['csm'] * W * r[key] / 100.0 for r in rows]
        vmod = math.sqrt(sum(v * v for v in vb))
        pmax = max(r[key] for r in rows)
        dom = next(r for r in rows if r[key] == pmax)
        vest1 = W * dom['csm']
        vest2 = W * old['cs_a']
        vmin = max(0.8 * vest2, 0.9 * vest1)
        new[d] = dict(dom=dom['mode'], T=dom['T'], part=pmax, sum=sum(r[key] for r in rows), Vmod=vmod, Vest1=vest1, Vest2=vest2,
                      Vmin=vmin, factor=max(vmin / vmod, 1.0))
        print('sismo %s: modo %d T=%.5f part=%.2f%% suma(43)=%.2f%%  factor hoja con STAAD=%.4f  (calculo previo %.4f, en el STD %s)' % (
            d, dom['mode'], dom['T'], pmax, new[d]['sum'], new[d]['factor'], old[d]['factor'], S['cfg']['F' + d]))
    print('peso sismico STAAD: X=%.2f Z=%.2f  (calculo previo %.2f)' % (wx, wz, old['W']))
    S['sheet'] = new
    # ------------------------------------------------ reacciones del caso 4
    RA = anlread.reactions(anl)
    n4 = 0
    for n in S['reactions']:
        v = RA.get((int(n), 4))
        if v is not None:
            S['reactions'][n]['4'] = [float(x) for x in v]
            n4 += 1
    print('reacciones del caso 4 tomadas del ANL: %d de %d apoyos' % (n4, len(S['reactions'])))
    # ------------------------------------------------ cuantificacion
    to = takeoff(anl)
    Ltag = {}
    for e, d in S['design'].items():
        Ltag[d['tag']] = Ltag.get(d['tag'], 0.0) + d['L']
    for name in list(S['takeoff']):
        if name in to:
            S['takeoff'][name]['W'] = to[name]['W']
            S['takeoff'][name]['L'] = to[name]['L']
    tg = S['takeoff_tag']
    u = to['MC10-14']['W'] / to['MC10-14']['L']
    tg['LC'] = Ltag['LC'] * u
    tg['LM'] = to['MC10-14']['W'] - tg['LC']
    u = to['PIPS7']['W'] / to['PIPS7']['L']
    tg['CFC'] = Ltag['CFC'] * u
    tg['CF'] = to['PIPS7']['W'] - tg['CFC']
    # redondos: cubierta por su diametro; muros = total de PRISMATIC STEEL - cubierta
    wtc = sum(d['L'] * d['A'] * RHO for d in S['rods'].values() if d['tag'] == 'TC')
    tg['TC'] = wtc
    tg['TM'] = to['PRISMATIC STEEL']['W'] - wtc
    print('take-off STAAD: total %.3f kg  (calculo previo %.3f)' % (to['TOTAL'], S['weight']))
    S['weight'] = to['TOTAL']
    S['fuente'] = os.path.basename(anl)
    json.dump(S, open(out, 'w'), indent=1)


if __name__ == '__main__':
    main(*sys.argv[1:4])
