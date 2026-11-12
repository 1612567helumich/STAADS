"""Construccion final del modelo ND1: itera los factores de escala del espectro y
el modo dominante, escribe el STD y un resumen JSON de resultados."""
import sys, os, json, math, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import nd1_eval, nd1_std
from staadlite import design

PAR_MEDIA = 1.7961       # diametro equivalente a 2 redondos de 1/2" (misma area)

CFG = {
    "DIAE_PANELS_L": 3, "DIAE_PANELS": 0,
    "BACK_TRUSS": True,                      # armadura en el plano del muro del eje 3 (sin tensores atras)
    "SEC": {
        "COL": ("AISC", "W12X26"),           # unico perfil IR
        "TM": ("PRIS", PAR_MEDIA),           # tensores de muros laterales: 2 redondos de 1/2" por diagonal
        "PE": ("UPT", 10, "PTR4-14"),        # postes de puerta de emergencia (como H5-H6)
    },
}
COMMENT = [
    'NOSE DOCK H1 (ND1) - SUPERESTRUCTURA.  R1.2',
    'PLANTA 15.00 X 16.00 M, EJES A-B-C (X) Y 3-2-1 (Z), FRENTE ABIERTO EN EJE 1',
    'N.S.E. = 11.66 M (EJE 3), PENDIENTE 5.1 %, CUERDA INFERIOR EN N.I.E. = 9.36 M',
    'FORMA TIPO ND23 (ARMADURAS), CARGAS TIPO H5-H6 (ONEWAY POR GRUPOS Y MASA',
    'SISMICA EN PUNTA DE COLUMNAS).  NTDS / NTDV / RESESCO EL SALVADOR',
    'COLUMNAS: UN SOLO PERFIL IR (W12X26, A572 GR.50)',
    'EJE 3 SIN TENSORES: ARMADURA EN EL PLANO DEL MURO (VIGA SUPERIOR - CAJON)',
    'MONTEN CAJON (MCC) DONDE REMATAN CONTRAFLAMBEOS DE MURO Y POSTES DE PUERTAS',
    'EL TENSOR JUNTO A LA PUERTA DE EMERGENCIA ARRANCA EN EL CAJON DE +3.00',
    'R1.2: VIENTO SOBRE LA CORTINA Y LA PUERTA DE EMERGENCIA APLICADO EN SUS',
    'POSTES.  TODOS LOS TENSORES SON REDONDO DE 1/2 IN: UNO POR DIAGONAL EN',
    'CUBIERTA Y DOS POR DIAGONAL EN MUROS LATERALES (PRIS YD 1.7961 = DIAMETRO',
    'EQUIVALENTE A 2 REDONDOS DE 1/2 IN)',
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
    S['proy'] = c['TITLE'].split(' (')[0]
    S['nie'] = c['NIE'] / 100.0
    S['faldon_lv'] = list(g.faldon_lv)
    S['back_top'] = g.back_top
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
         "SEC": {"COL": ("AISC", "W14X22"), "TM": ("PRIS", PAR_MEDIA)}},
        ['NOSE DOCK H1 (ND1) - SUPERESTRUCTURA.  R1.2 - ALTERNATIVA CON W14X22',
         'MISMA GEOMETRIA Y CARGAS QUE EL MODELO PRINCIPAL (W12X26); SOLO CAMBIA LA',
         'COLUMNA.  ES MAS LIGERA PERO SUS MODOS EN Z SALEN REPARTIDOS (MODOS',
         'LOCALES DE MUROS POR EL EJE DEBIL DE LA COLUMNA) Y EL FACTOR DE ESCALA',
         'DEL ESPECTRO EN Z RESULTA ALTO'],
    ),
    # ------------------------------------------------------------------ NOSE DOCK H4
    'H4': (
        {"TITLE": "NOSE DOCK H4 (ND4)", "DATE": "12/11/2026",
         "Y_TOP": 1160.0, "NIE": 930.0,                      # N.S.E. 11.60 y N.I.E. 9.30 (DXF)
         "GIRTS": [48.0 + 120.0 * i for i in range(9)],      # largueros de muro a los niveles del DXF
         "MAX_GAP": 120.0, "TOP_DROP": 100.0, "SNAP": 15.0, "FALDON_GIRT": True,
         "STUB_MIN": 0.0,                                    # tambien los largueros cortos entre columna y poste
         "CF_BELOW_TOP": True,                               # PIPS de muro hasta +10.08, no al larguero superior (R1.2)
         "FALDON_STRIP": True,                               # faldon completo: franja de 10.4 cm abajo de la cuerda (R1.3)
         "DOOR_X": (952.0, 1462.0), "DOOR_H": 607.0,         # cortina 5.00 x 6.00 en el claro B-C, dintel a +6.07
         "EDOOR_WALL": "3", "EDOOR_X": (766.0, 897.0), "EDOOR_H": 227.0, "EDOOR_TOP": 288.0,
         "ROD_DOOR": False,                                  # los muros laterales no tienen puertas
         "DIAE_PANELS_L": 3, "DIAE_PANELS": 0,
         "BACK_TRUSS": False, "BACK_BRACE": True,            # R1.4: sin armadura en el eje 3, cruz de tensores en A-B
         "SEC": {"COL": ("AISC", "W12X26"), "TM": ("PRIS", 1.27), "PE": ("UPT", 10, "PTR4-14"),
                 "PC": ("AISC", "HSST6X6X0.25"),              # postes de cortina HSS 6x6x1/4 (R1.1)
                 "TMF": ("PRIS", PAR_MEDIA),                  # tensores del muro de fondo: 2 redondos de 1/2"
                 "LST": ("UPT", 4, "MCC10-14")}},             # larguero de cubierta del eje 3 sin armadura: cajon
        ['NOSE DOCK H4 (ND4) - SUPERESTRUCTURA.  R1.2',
         'PLANTA 15.00 X 16.00 M, EJES A-B-C (X) Y 3-2-1 (Z), FRENTE ABIERTO EN EJE 1',
         'ALTURAS DEL DXF: N.S.E. = 11.60 M (EJE 3) Y N.I.E. = 9.30 M.  PENDIENTE 5.1 %',
         'FORMA TIPO ND23 (ARMADURAS), CARGAS TIPO H5-H6 (ONEWAY POR GRUPOS Y MASA',
         'SISMICA EN PUNTA DE COLUMNAS).  NTDS / NTDV / RESESCO EL SALVADOR',
         'COLUMNAS: UN SOLO PERFIL IR (W12X26, A572 GR.50)',
         'LARGUEROS DE MURO A LOS NIVELES DEL DXF (+0.48 Y A CADA 1.20 M).  NINGUNA',
         'SEPARACION MAYOR A 1.20 M: LARGUERO SUPERIOR A +10.60 EN EL EJE 3 Y EN LOS',
         'CLAROS 3-2 DE LOS EJES A Y C, Y LARGUERO INTERMEDIO EN EL FALDON DEL EJE 1',
         'CONTRAFLAMBEOS DE MURO (PIPS) DEL PISO AL LARGUERO DE +10.08 (MONTEN CAJON',
         'MCC): NO SUBEN AL LARGUERO DE CUBIERTA DE +10.60.  ESTE VA EN MCE10-14 EN',
         'EL EJE 3 Y EN CAJON MCC10-14 EN LOS CLAROS 3-2 DE A Y C (SALVA 8 M SIN',
         'PIPS: CON MCE SU KL/R SERIA 214 > 200)',
         'CORTINA 5.00 X 6.00 M (DINTEL A +6.07, POSTES HSS 6X6X1/4) Y PUERTA DE',
         'EMERGENCIA EN EL EJE 3, CLARO B-C, CON SU VIENTO APLICADO EN SUS POSTES.',
         'MONTEN CAJON (MCC) DONDE REMATAN LOS CONTRAFLAMBEOS DE MURO Y LOS POSTES',
         'DE PUERTAS',
         'EJE 3 SIN TENSORES: ARMADURA EN EL PLANO DEL MURO ENTRE LA VIGA SUPERIOR Y',
         'EL LARGUERO SUPERIOR',
         'TENSORES: REDONDO DE 1/2 IN, UNO POR DIAGONAL, EN MUROS A Y C Y CUBIERTA;',
         'NINGUNO CRUZA PUERTAS',
         'R1.1: POSTES DE CORTINA HSS 6X6X1/4 (ANTES HSS 4X4X1/4)',
         'R1.2: LOS PIPS DE MURO REMATAN EN EL LARGUERO DE +10.08 (CAJON), UNO ANTES',
         'DEL LARGUERO DE CUBIERTA DE +10.60; YA NO SUBEN HASTA ARRIBA'],
    ),
}

if __name__ == '__main__':
    if len(sys.argv) > 3:
        cfg, com = ALT[sys.argv[3]]
        main(sys.argv[1], sys.argv[2], cfg, com)
    else:
        main(sys.argv[1], sys.argv[2])
