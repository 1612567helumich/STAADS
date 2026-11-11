"""Construccion final del modelo ND1: itera los factores de escala del espectro y
el modo dominante, escribe el STD y un resumen JSON de resultados."""
import sys, os, json, math, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nd1_eval, nd1_std
from staadlite import design

CFG = {
    "DIAE_PANELS_L": 3, "DIAE_PANELS": 0,
    "BACK_TRUSS": True,                      # armadura en el plano del muro del eje 3 (sin tensores atras)
    "SEC": {
        "COL": ("AISC", "W12X26"),           # unico perfil IR
        "TM": ("PRIS", 1.905),               # tensores de muros laterales 3/4"
        "PE": ("UPT", 10, "PTR4-14"),        # postes de puerta de emergencia (como H5-H6)
    },
}
COMMENT = [
    'NOSE DOCK H1 (ND1) - SUPERESTRUCTURA.  R1.1',
    'PLANTA 15.00 X 16.00 M, EJES A-B-C (X) Y 3-2-1 (Z), FRENTE ABIERTO EN EJE 1',
    'N.S.E. = 11.66 M (EJE 3), PENDIENTE 5.1 %, CUERDA INFERIOR EN N.I.E. = 9.36 M',
    'FORMA TIPO ND23 (ARMADURAS), CARGAS TIPO H5-H6 (ONEWAY POR GRUPOS Y MASA',
    'SISMICA EN PUNTA DE COLUMNAS).  NTDS / NTDV / RESESCO EL SALVADOR',
    'COLUMNAS: UN SOLO PERFIL IR (W12X26, A572 GR.50)',
    'EJE 3 SIN TENSORES: ARMADURA EN EL PLANO DEL MURO (VIGA SUPERIOR - CAJON)',
    'MONTEN CAJON (MCC) DONDE REMATAN CONTRAFLAMBEOS DE MURO Y POSTES DE PUERTAS',
    'EL TENSOR JUNTO A LA PUERTA DE EMERGENCIA ARRANCA EN EL CAJON DE +3.00',
]

def main(out_std, out_json, cfg0=None, comment=None):
    cfg = dict(cfg0 or CFG)
    COMMENT_ = comment or COMMENT
    g, m = nd1_eval.build(cfg, out_std, COMMENT_)
    rep = nd1_eval.evaluate(g, m, verbose=False)
    sf = rep['sf']
    cfg.update(FX=math.ceil(sf['X']['factor'] * 1000 - 1e-6) / 1000.0, FZ=math.ceil(sf['Z']['factor'] * 1000 - 1e-6) / 1000.0,
               DOM_X=sf['X']['dom'], DOM_Z=sf['Z']['dom'])
    g, m = nd1_eval.build(cfg, out_std, COMMENT_)
    rep = nd1_eval.evaluate(g, m, verbose=True)
    R = rep['R']; st = R.st; mr = R.modal
    c = g.c
    # ----------------------------------------------------------- resumen JSON
    S = {}
    S['cfg'] = {k: v for k, v in cfg.items()}
    S['geom'] = dict(nodes=len(m.nodes), members=len(m.members), supports=len(m.supports))
    S['sections'] = {tag: st.elems[g.bytag[tag][0]].sec.name for tag in g.ORDER if g.bytag[tag]}
    S['counts'] = {tag: len(g.bytag[tag]) for tag in g.ORDER if g.bytag[tag]}
    S['ranges'] = {tag: [min(g.bytag[tag]), max(g.bytag[tag])] for tag in g.ORDER if g.bytag[tag]}
    S['tips'] = {k: dict(node=n, xyz=list(m.nodes[n]), mass=g.masses[k], detail=g.mass_detail[k]) for k, n in g.tipnodes.items()}
    S['centers'] = {k: g.nid[v] for k, v in g.center.items()}
    S['supports'] = g.supports
    S['towards'] = g.towards
    S['wind'] = dict(q=g.wind['q'], info=g.wind['info'], cases={str(k): v for k, v in g.wind['cases'].items()},
                     strip=g.wind_extra['strip'], door_w=g.wind_extra['door_w'], edoor_w=g.wind_extra['edoor_w'])
    from nd1_gen import fmt_list
    lowm = {k: ' '.join(fmt_list(v)) for k, v in g.wind_extra['low'].items()}
    lowm['pc'] = ' '.join(fmt_list(g.wind_extra['pc']))
    lowm['pe'] = ' '.join(fmt_list(g.wind_extra['pe']))
    S['wind']['low_members'] = lowm
    S['modal'] = dict(T=[float(t) for t in mr.T], f=[float(f) for f in mr.freq], px=[float(v) for v in mr.part['X']], pz=[float(v) for v in mr.part['Z']],
                      W=float(mr.wtot['X']), tc_inactive=sorted(R.tc_modal))
    S['sf'] = {d: {k: (float(v) if not isinstance(v, int) else v) for k, v in s.items()} for d, s in rep['sf'].items()}
    S['sheet'] = rep['sheet']
    S['base_shear'] = {str(k): {d: float(v[1]) for d, v in R.base_shear(k).items()} for k in R.spec_cases}
    # derivas
    dr = {}
    for name, n in list(g.tipnodes.items()) + [('centro ' + k, g.nid[v]) for k, v in g.center.items()]:
        H = m.nodes[n][1]
        rows = []
        for lc in list(range(16, 32)):
            u = R.node_disp(lc, n)
            rows.append(dict(lc=lc, ux=float(u[0]), uy=float(u[1]), uz=float(u[2])))
        dr[name] = dict(node=n, H=H, rows=rows)
    S['drift'] = dr
    S['drift_max'] = dict(sismo=rep['drift_s'], viento=rep['drift_w'])
    # diseño
    des = {}
    for e, r in rep['design'].items():
        des[str(e)] = dict(tag=g.minfo[e]['tag'], sec=st.elems[e].sec.name, ratio=r['ratio'], lc=r['lc'], loc=r['loc'], ref=r['ref'], L=g.L(e))
    S['design'] = des
    S['maxratio'] = rep['maxratio']
    # tensores
    rods = {}
    for tag in ('TM', 'TMF', 'TC'):
        for e in g.bytag.get(tag, []):
            tmax = 0; lcm = None
            for lc in nd1_eval.DESIGN_LCS:
                T = R.section_forces(lc, e, 2)[0, 1]
                if T > tmax: tmax, lcm = float(T), lc
            A = st.elems[e].sec.A
            rods[str(e)] = dict(tag=tag, d=st.elems[e].sec.d, A=A, T=tmax, lc=lcm, cap=0.9 * 2530 * A, L=g.L(e), nodes=list(m.members[e]))
    S['rods'] = rods
    # reacciones
    reac = {}
    for n in m.supports:
        reac[str(n)] = {str(lc): [float(v) for v in R.reaction(lc, n)] for lc in [1, 2] + list(range(4, 67)) if lc != 3}
    S['reactions'] = reac
    S['sumreac'] = {str(k): [float(v) for v in sum(R.reac[k].values())] for k in R.reac}
    # cuantificacion
    wt = collections.defaultdict(float); ln = collections.defaultdict(float)
    wt_tag = collections.defaultdict(float)
    for e, el in st.elems.items():
        w = el.sec.A * el.rho * el.L
        wt[el.sec.name] += w; ln[el.sec.name] += el.L; wt_tag[g.minfo[e]['tag']] += w
    S['takeoff'] = {k: dict(L=ln[k], W=wt[k]) for k in wt}
    S['takeoff_tag'] = dict(wt_tag)
    S['weight'] = rep['weight']
    S['iters'] = {str(k): v for k, v in R.iters.items()}
    S['inactive'] = {str(k): sorted(v) for k, v in R.inactive.items()}
    S['deflect'] = {}
    u = R.disp(32)
    for tag in ('LC', 'CS', 'CSL', 'VR'):
        worst = (0, None)
        for e in g.bytag[tag]:
            el = st.elems[e]
            for n in (el.n1, el.n2):
                worst = max(worst, (abs(float(u[6 * st.nidx[n] + 1])), n))
        S['deflect'][tag] = dict(dy=worst[0], node=worst[1])
    json.dump(S, open(out_json, 'w'), indent=1)
    print('\nfactores finales FX=%.3f FZ=%.3f  dominantes X=%d Z=%d' % (cfg['FX'], cfg['FZ'], cfg['DOM_X'], cfg['DOM_Z']))
    print('lineas > 79:', sum(1 for l in open(out_std, encoding='latin-1').read().splitlines() if len(l) > 79))

ALT = {
    'W14X22': (
        {"DIAE_PANELS_L": 3, "DIAE_PANELS": 0, "BACK_TRUSS": True,
         "SEC": {"COL": ("AISC", "W14X22"), "TM": ("PRIS", 1.905)}},
        ['NOSE DOCK H1 (ND1) - SUPERESTRUCTURA.  R1.1 - ALTERNATIVA CON W14X22',
         'MISMA GEOMETRIA Y CARGAS QUE EL MODELO PRINCIPAL (W12X26); SOLO CAMBIA LA',
         'COLUMNA.  ES MAS LIGERA PERO SUS MODOS EN Z SALEN REPARTIDOS (MODOS',
         'LOCALES DE MUROS POR EL EJE DEBIL DE LA COLUMNA) Y EL FACTOR DE ESCALA',
         'DEL ESPECTRO EN Z RESULTA ALTO.  VER RESUMEN_ND1'],
    ),
}

if __name__ == '__main__':
    if len(sys.argv) > 3:
        cfg, com = ALT[sys.argv[3]]
        main(sys.argv[1], sys.argv[2], cfg, com)
    else:
        main(sys.argv[1], sys.argv[2])
