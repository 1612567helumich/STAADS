"""Escribe el archivo .STD del ND1 a partir del generador de geometria."""
import math
from nd1_gen import Gen, fnum, fmt_list, wrap

MATERIALS = """DEFINE MATERIAL START
ISOTROPIC STEEL
E 2.09042e+06
POISSON 0.3
DENSITY 0.00783341
ALPHA 1.2e-05
DAMP 0.03
TYPE STEEL
STRENGTH FY 2581.92 FU 4158.4 RY 1.5 RT 1.2
ISOTROPIC CONCRETE
E 221467
POISSON 0.17
DENSITY 0.00240262
ALPHA 1e-05
DAMP 0.05
TYPE CONCRETE
STRENGTH FCU 281.228
END DEFINE MATERIAL"""

COMBOS = [
    ('*COMBINACIONES DE SERVICIO', None),
    (16, 'CM+CVR+SX+30%SZ', '1 1.0 3 1.0 4 1.0 5 0.3'),
    (17, 'CM+CVR+SX-30%SZ', '1 1.0 3 1.0 4 1.0 7 0.3'),
    (18, 'CM+CVR-SX+30%SZ', '1 1.0 3 1.0 6 1.0 5 0.3'),
    (19, 'CM+CVR-SX-30%SZ', '1 1.0 3 1.0 6 1.0 7 0.3'),
    (20, 'CM+CVR+30%SX+SZ', '1 1.0 3 1.0 4 0.3 5 1.0'),
    (21, 'CM+CVR+30%SX-SZ', '1 1.0 3 1.0 4 0.3 7 1.0'),
    (22, 'CM+CVR-30%SX+SZ', '1 1.0 3 1.0 6 0.3 5 1.0'),
    (23, 'CM+CVR-30%SX-SZ', '1 1.0 3 1.0 6 0.3 7 1.0'),
    (24, 'CM+VX', '1 1.0 8 1.0'),
    (25, 'CM-VX', '1 1.0 9 1.0'),
    (26, 'CM+VZ', '1 1.0 10 1.0'),
    (27, 'CM-VZ', '1 1.0 11 1.0'),
    (28, 'CM+VX(PA)', '1 1.0 12 1.0'),
    (29, 'CM-VX(PA)', '1 1.0 13 1.0'),
    (30, 'CM+VZ(PA)', '1 1.0 14 1.0'),
    (31, 'CM-VZ(PA)', '1 1.0 15 1.0'),
    (32, 'CM+CV', '1 1.0 2 1.0'),
    ('*COMBINACIONES DE DISENO (RESESCO, ART. 21)', None),
    (33, '1.4CM+1.7CV', '1 1.4 2 1.7'),
    (34, '1.05CM+1.4025SX+0.4207SZ+1.275CVR', '1 1.05 4 1.4025 5 0.4207 3 1.275'),
    (35, '1.05CM+1.4025SX-0.4207SZ+1.275CVR', '1 1.05 4 1.4025 7 0.4207 3 1.275'),
    (36, '1.05CM-1.4025SX+0.4207SZ+1.275CVR', '1 1.05 6 1.4025 5 0.4207 3 1.275'),
    (37, '1.05CM-1.4025SX-0.4207SZ+1.275CVR', '1 1.05 6 1.4025 7 0.4207 3 1.275'),
    (38, '1.05CM+0.4207SX+1.4025SZ+1.275CVR', '1 1.05 4 0.4207 5 1.4025 3 1.275'),
    (39, '1.05CM+0.4207SX-1.4025SZ+1.275CVR', '1 1.05 4 0.4207 7 1.4025 3 1.275'),
    (40, '1.05CM-0.4207SX+1.4025SZ+1.275CVR', '1 1.05 6 0.4207 5 1.4025 3 1.275'),
    (41, '1.05CM-0.4207SX-1.4025SZ+1.275CVR', '1 1.05 6 0.4207 7 1.4025 3 1.275'),
    (42, '0.9CM+1.43SX+0.429SZ', '1 0.9 4 1.43 5 0.429'),
    (43, '0.9CM+1.43SX-0.429SZ', '1 0.9 4 1.43 7 0.429'),
    (44, '0.9CM-1.43SX+0.429SZ', '1 0.9 6 1.43 5 0.429'),
    (45, '0.9CM-1.43SX-0.429SZ', '1 0.9 6 1.43 7 0.429'),
    (46, '0.9CM+0.429SX+1.43SZ', '1 0.9 4 0.429 5 1.43'),
    (47, '0.9CM+0.429SX-1.43SZ', '1 0.9 4 0.429 7 1.43'),
    (48, '0.9CM-0.429SX+1.43SZ', '1 0.9 6 0.429 5 1.43'),
    (49, '0.9CM-0.429SX-1.43SZ', '1 0.9 6 0.429 7 1.43'),
    (50, '1.05CM+1.2762VX+1.275CVR', '1 1.05 8 1.276 3 1.275'),
    (51, '0.9CM+1.3013VX', '1 0.9 8 1.3013'),
    (52, '1.05CM+1.2762V-X+1.275CVR', '1 1.05 9 1.276 3 1.275'),
    (53, '0.9CM+1.3013V-X', '1 0.9 9 1.3013'),
    (54, '1.05CM+1.2762VZ+1.275CVR', '1 1.05 10 1.276 3 1.275'),
    (55, '0.9CM+1.3013VZ', '1 0.9 10 1.3013'),
    (56, '1.05CM+1.2762V-Z+1.275CVR', '1 1.05 11 1.276 3 1.275'),
    (57, '0.9CM+1.3013V-Z', '1 0.9 11 1.3013'),
    (58, '1.05CM+1.2762VX(PA)+1.275CVR', '1 1.05 12 1.276 3 1.275'),
    (59, '0.9CM+1.3013VX(PA)', '1 0.9 12 1.3013'),
    (60, '1.05CM+1.2762V-X(PA)+1.275CVR', '1 1.05 13 1.276 3 1.275'),
    (61, '0.9CM+1.3013V-X(PA)', '1 0.9 13 1.3013'),
    (62, '1.05CM+1.2762VZ(PA)+1.275CVR', '1 1.05 14 1.276 3 1.275'),
    (63, '0.9CM+1.3013VZ(PA)', '1 0.9 14 1.3013'),
    (64, '1.05CM+1.2762V-Z(PA)+1.275CVR', '1 1.05 15 1.276 3 1.275'),
    (65, '0.9CM+1.3013V-Z(PA)', '1 0.9 15 1.3013'),
    (66, '1.2CM+1.2CV', '1 1.2 2 1.2'),
]


def roundup4(x):
    """ROUNDUP(ROUND(x,6),4) de la hoja de viento, conservando el signo."""
    x = round(x, 6)
    s = -1.0 if x < 0 else 1.0
    return s * math.ceil(abs(x) * 1e4 - 1e-9) / 1e4


def spectrum_table(c):
    pts = []
    for i in range(1, 301):
        T = i / 100.0
        base = c['I'] * c['A'] / c['R']
        if T < c['TO'] / 3:
            v = base * (1 + 3 * (c['CO'] - 1) * T / c['TO'])
        elif T <= c['TO']:
            v = base * c['CO']
        else:
            v = base * c['CO'] * (c['TO'] / T) ** (2.0 / 3.0)
        pts.append((T, round(v + 1e-12, 3)))
    return pts


def wind_q(c, g):
    """Presion estatica de diseño q (kg/m2) con la altura media de cubierta."""
    v = c['VMAX'] / c['GUST']
    p0 = 0.0048 * v * v
    z = 0.5 * (g.yroof(c['Z3']) + g.yroof(c['Z1'])) / 100.0
    cz = 1.0 if z < 10 else (z / 10.0) ** (2.0 / c['ZONE_A'])
    return cz * c['ZONE_K'] * p0, dict(v=v, p0=p0, z=z, cz=cz)


# caras: (grupo, signo de empuje (+), direccion STAAD, cerrada)
FACES = [('_OESTE', 1, 'GX INCLINED'), ('_ESTE', -1, 'GX INCLINED'), ('_NORTE', 1, 'GZ'),
         ('_SUR', -1, 'GZ INCLINED'), ('_CUBIERTA', -1, 'GY INCLINED')]
CPE = {'BARLO': 0.8, 'SOTA': -0.5, 'LAT': -0.7, 'TECHO': -0.7}
# condicion de cada cara por caso de viento
COND = {
    8: {'_OESTE': 'BARLO', '_ESTE': 'SOTA', '_NORTE': 'LAT', '_SUR': 'LAT', '_CUBIERTA': 'TECHO'},
    9: {'_OESTE': 'SOTA', '_ESTE': 'BARLO', '_NORTE': 'LAT', '_SUR': 'LAT', '_CUBIERTA': 'TECHO'},
    10: {'_OESTE': 'LAT', '_ESTE': 'LAT', '_NORTE': 'BARLO', '_SUR': 'SOTA', '_CUBIERTA': 'TECHO'},
    11: {'_OESTE': 'LAT', '_ESTE': 'LAT', '_NORTE': 'SOTA', '_SUR': 'BARLO', '_CUBIERTA': 'TECHO'},
}
# presion interior (frente eje 1 abierto, Z = 1600): paralela / sotavento / barlovento
CPI = {12: -0.5, 13: -0.5, 14: -0.6, 15: 0.75}
BASE = {12: 8, 13: 9, 14: 10, 15: 11}
WTITLE = {8: 'VIENTO X', 9: 'VIENTO -X', 10: 'VIENTO Z', 11: 'VIENTO -Z',
          12: 'VIENTO X PA', 13: 'VIENTO -X PA', 14: 'VIENTO Z PA', 15: 'VIENTO -Z PA'}


def wind_cases(c, g):
    q, info = wind_q(c, g)
    out = {}
    for lc in range(8, 16):
        b = BASE.get(lc, lc)
        vals = {}
        for grp, sgn, d in FACES:
            cpe = CPE[COND[b][grp]]
            cp = cpe - CPI[lc] if lc in CPI else cpe
            p = q * cp
            vals[grp] = dict(cp=cp, cpe=cpe, cpi=CPI.get(lc), p=p, staad=roundup4(sgn * p / 1e4), dir=d)
        out[lc] = vals
    return q, info, out


def build_std(g, extra_comment=None):
    c = g.c
    L = []
    A = L.append
    A('STAAD SPACE ' + c['TITLE'])
    A('START JOB INFORMATION')
    A('ENGINEER DATE ' + c['DATE'])
    A('END JOB INFORMATION')
    A('INPUT WIDTH 79')
    A('*')
    for ln in (extra_comment or []):
        A('* ' + ln)
    A('*')
    A('UNIT CM KG')
    A('SET FLOOR LOAD TOLERANCE 0.1')
    A('JOINT COORDINATES')
    toks = []
    for n in sorted(g.nodes):
        x, y, z = g.nodes[n]
        toks.append('%d %s %s %s;' % (n, fnum(x), fnum(y), fnum(z)))
    cur = ''
    for t in toks:
        if len(cur) + len(t) + 1 > 79:
            A(cur)
            cur = t
        else:
            cur = (cur + ' ' + t) if cur else t
    A(cur)
    A('MEMBER INCIDENCES')
    cur = ''
    for e in sorted(g.members):
        a, b = g.members[e]
        t = '%d %d %d;' % (e, a, b)
        if len(cur) + len(t) + 1 > 79:
            A(cur)
            cur = t
        else:
            cur = (cur + ' ' + t) if cur else t
    A(cur)
    # ------------------------------------------------------------ grupos
    XA, XB, XC, Z3, Z2, Z1 = c['XA'], c['XB'], c['XC'], c['Z3'], c['Z2'], c['Z1']
    bt = g.bytag
    mg = [
        ('_COLUMNAS', bt['COL']),
        ('_VIGAS_BORDE', bt['VR'] + bt['VT']),
        ('_CUERDAS_ARM_T', bt['CS'] + bt['CI']),
        ('_CUERDAS_ARM_L', bt['CSL'] + bt['CIL']),
        ('_MONTANTES', bt['MON'] + bt['MONF']),
        ('_DIAGONALES', bt['DIA'] + bt['DIAE']),
        ('_LARGUEROS_CUB', bt['LC']),
        ('_CONTRAFLAMBEOS', bt['CFC']),
        ('_LARGUEROS_MURO', bt['LM']),
        ('_LARGUEROS_CAJON', bt['LMT'] + bt['LS']),
        ('_LARGUEROS_FALDON', bt['LF']),
        ('_DINTELES', bt['DIN'] + bt['DINE']),
        ('_FLAMBEOS_MUROS', bt['CF']),
        ('_POSTES_CORTINA', bt['PC']),
        ('_PUERTA_EMERG', bt['PE'] + bt['DE']),
        ('_TENSORES_MURO', bt['TM'] + bt['TMF']),
        ('_TENSORES_CUB', bt['TC']),
    ]

    def inplane(e, axis, val):
        a, b = g.members[e]
        return abs(g.nodes[a][axis] - val) < 1e-6 and abs(g.nodes[b][axis] - val) < 1e-6
    cub = bt['VR'] + bt['VT'] + bt['CS'] + bt['CSL'] + bt['LC'] + bt['CFC']
    wall_tags = ('COL', 'LM', 'LMT', 'LS', 'DIN', 'DINE', 'CF', 'PC', 'PE', 'DE')
    oeste = [e for e in g.members if (g.minfo[e]['tag'] in wall_tags or g.minfo[e]['tag'] == 'VR') and inplane(e, 0, XA)]
    este = [e for e in g.members if (g.minfo[e]['tag'] in wall_tags or g.minfo[e]['tag'] == 'VR') and inplane(e, 0, XC)]
    norte = [e for e in g.members if (g.minfo[e]['tag'] in wall_tags or g.minfo[e]['tag'] == 'VT') and inplane(e, 2, Z3)]
    yb1 = g.ybot(Z1, at_column=True)
    sur = [e for e in g.members if g.minfo[e]['tag'] in ('CS', 'CI', 'MON', 'MONF', 'LF') and g.minfo[e].get('truss') == 'T1']
    for e in bt['COL']:
        a, b = g.members[e]
        if inplane(e, 2, Z1) and min(g.nodes[a][1], g.nodes[b][1]) >= yb1 - 1e-6:
            sur.append(e)
    fg = [('_CUBIERTA', cub), ('_OESTE', oeste), ('_ESTE', este), ('_NORTE', norte), ('_SUR', sur)]
    g.floor = dict(fg)
    g.mgroups = dict(mg)
    tips = [g.nid[g.tips[k]] for k in ('A-1', 'C-1', 'A-2', 'C-2', 'A-3', 'B-3', 'C-3')]
    g.tipnodes = {k: g.nid[g.tips[k]] for k in g.tips}
    A('START GROUP DEFINITION')
    A('MEMBER')
    for name, ids in mg:
        if ids:
            L.extend(wrap([name] + fmt_list(ids)))
    A('FLOOR')
    for name, ids in fg:
        L.extend(wrap([name] + fmt_list(ids)))
    A('JOINT')
    L.extend(wrap(['_PUNTA_COLUMNAS'] + fmt_list(tips)))
    A('END GROUP DEFINITION')
    # ------------------------------------------------------------ tablas de usuario
    A(open(c['USER_TABLES'], 'r', encoding='latin-1').read().rstrip('\n'))
    A(MATERIALS)
    # ------------------------------------------------------------ propiedades
    byspec = {}
    for tag in g.ORDER:
        if not bt[tag]:
            continue
        byspec.setdefault(c['SEC'][tag], []).extend(bt[tag])
    upt = [(s, ids) for s, ids in byspec.items() if s[0] == 'UPT']
    aisc = [(s, ids) for s, ids in byspec.items() if s[0] == 'AISC']
    pris = [(s, ids) for s, ids in byspec.items() if s[0] == 'PRIS']
    if upt:
        A('MEMBER PROPERTY')
        for s, ids in upt:
            L.extend(wrap(fmt_list(ids) + ['UPTABLE', str(s[1]), s[2]]))
    if aisc:
        A('MEMBER PROPERTY AMERICAN')
        for s, ids in aisc:
            L.extend(wrap(fmt_list(ids) + ['TABLE', 'ST', s[1]]))
    if pris:
        A('MEMBER PROPERTY')
        for s, ids in pris:
            L.extend(wrap(fmt_list(ids) + ['PRIS', 'YD', fnum(s[1], 4)]))
    A('CONSTANTS')
    beta90 = [e for e in g.members if g.minfo[e]['tag'] in ('LM', 'LMT', 'LS', 'LF', 'DIN', 'DINE', 'DE') or g.minfo[e].get('beta') == 90.0]
    L.extend(wrap(['BETA', '90', 'MEMB'] + fmt_list(beta90)))
    A('MATERIAL STEEL ALL')
    # ------------------------------------------------------------ apoyos
    A('SUPPORTS')
    base_fixed = [g.nid[g.col_nodes[k][0]] for k in g.col_nodes]
    posts = []
    sag = []
    for e in bt['PC'] + bt['PE']:
        for n in g.members[e]:
            if abs(g.nodes[n][1]) < 1e-9:
                posts.append(n)
    for e in bt['CF']:
        for n in g.members[e]:
            if abs(g.nodes[n][1]) < 1e-9:
                sag.append(n)
    L.extend(wrap(fmt_list(base_fixed) + ['FIXED']))
    L.extend(wrap(fmt_list(posts) + ['PINNED']))
    L.extend(wrap(fmt_list(sag) + ['ENFORCED', 'BUT', 'FX', 'FZ', 'MX', 'MY', 'MZ']))
    g.supports = dict(fixed=sorted(set(base_fixed)), pinned=sorted(set(posts)), vert=sorted(set(sag)))
    # ------------------------------------------------------------ liberaciones
    rs, re_ = [], []
    for e, inf in g.minfo.items():
        for r in inf.get('rel', []) or []:
            (rs if r == 'START' else re_).append(e)

    def chain_ends(ids, startcond, endcond):
        for e in ids:
            a, b = g.members[e]
            if startcond(g.nodes[a]):
                rs.append(e)
            if endcond(g.nodes[b]):
                re_.append(e)
    isx = lambda v: (lambda p: abs(p[0] - v) < 1e-6)
    isz = lambda v: (lambda p: abs(p[2] - v) < 1e-6)
    chain_ends(bt['CS'] + bt['CI'], isx(XA), isx(XC))
    chain_ends([e for e in bt['CSL'] + bt['CIL'] if g.minfo[e]['truss'] == 'TL1'], isz(Z3), isz(Z2))
    chain_ends([e for e in bt['CSL'] + bt['CIL'] if g.minfo[e]['truss'] == 'TL2'], isz(Z2), isz(Z1))
    if c['RAFTER_PINNED']:
        chain_ends(bt['VR'], lambda p: isz(Z3)(p) or isz(Z2)(p), lambda p: isz(Z2)(p) or isz(Z1)(p))
    if c['VT_PINNED']:
        chain_ends(bt['VT'], lambda p: isx(XA)(p) or isx(XB)(p), lambda p: isx(XB)(p) or isx(XC)(p))
    A('MEMBER RELEASE')
    L.extend(wrap(fmt_list(rs) + ['START', 'MY', 'MZ']))
    L.extend(wrap(fmt_list(re_) + ['END', 'MY', 'MZ']))
    g.rel = dict(start=sorted(set(rs)), end=sorted(set(re_)))
    A('MEMBER TRUSS')
    L.extend(wrap(fmt_list(bt['MON'] + bt['DIA'] + bt['DIAE'] + bt['CF'] + bt['CFC'])))
    A('MEMBER TENSION')
    L.extend(wrap(fmt_list(bt['TM'] + bt['TMF'] + bt['TC'])))
    A('CUT OFF MODE SHAPE %d' % c['NMODES'])
    # ------------------------------------------------------------ cargas
    q, qinfo, wc = wind_cases(c, g)
    g.wind = dict(q=q, info=qinfo, cases=wc)
    t1mon = [e for e in bt['MON'] if g.minfo[e]['truss'] == 'T1']
    tow = t1mon[0] if t1mon else None      # con larguero de faldon la lamina va a los miembros horizontales
    g.towards = tow
    tow_txt = (' TOWARDS %d' % tow) if tow else ''
    cm_r = c['CM_ROOF'] / 1e4
    cm_w = c['CM_WALL'] / 1e4
    cv = c['CV_ROOF'] / 1e4
    dx, dh = c['DOOR_X'], c['DOOR_H']
    ed = c['EDOOR_X'] if c['EDOOR_WALL'] == '3' else c['EDOOR_Z']      # postes de la puerta de emergencia
    pc_nodes_top = [g.nid[g.key(x, dh, Z3)] for x in dx]
    w_cort = c['W_CORTINA'] * ((dx[1] - dx[0] - 10.16) / 100.0) * 6.0
    g.w_cortina = w_cort
    pe_low = [e for e in bt['PE'] if max(g.nodes[g.members[e][0]][1], g.nodes[g.members[e][1]][1]) <= c['EDOOR_H'] + 1e-6]
    A('LOAD 1 LOADTYPE Dead  TITLE CARGA MUERTA')
    A('SELFWEIGHT Y -1')
    A('* CUBIERTA: PANEL GLAMET 1.5 in (9.32) + INSTALACIONES (10.00) = %s KG/M2' % fnum(c['CM_ROOF'], 2))
    A('* MUROS Y FALDON: LAMINA KR-18 CAL. 24 = %s KG/M2' % fnum(c['CM_WALL'], 2))
    A('ONEWAY LOAD')
    A('_CUBIERTA ONE -%s GY INCLINED' % fnum(cm_r, 6))
    A('_ESTE ONE -%s GY INCLINED' % fnum(cm_w, 6))
    A('_OESTE ONE -%s GY INCLINED' % fnum(cm_w, 6))
    A('_NORTE ONE -%s GY INCLINED' % fnum(cm_w, 6))
    A('_SUR ONE -%s GY INCLINED%s' % (fnum(cm_w, 6), tow_txt))
    A('* PUERTA DE EMERGENCIA (CARGA LINEAL EN POSTES, IGUAL QUE H5-H6)')
    A('MEMBER LOAD')
    L.extend(wrap(fmt_list(pe_low) + ['UNI', 'GY', '-' + fnum(c['EDOOR_LINE'], 3)]))
    A('* CORTINA METALICA 5.00 X 6.00 M (%s KG/M2): DOS CARGAS EN SUS APOYOS' % fnum(c['W_CORTINA'], 2))
    A('JOINT LOAD')
    L.extend(wrap(fmt_list(pc_nodes_top) + ['FY', '-' + fnum(w_cort / 2.0, 2)]))
    A('LOAD 2 LOADTYPE Live  TITLE CARGA VIVA')
    A('* CV MAXIMA, CUBIERTA CON PENDIENTE > 5 %% (RESESCO, INCISO i) = %s KG/M2' % fnum(c['CV_ROOF'], 2))
    A('ONEWAY LOAD')
    A('_CUBIERTA ONE -%s GY INCLINED' % fnum(cv, 6))
    A('LOAD 3 LOADTYPE Live REDUCIBLE TITLE CARGA VIVA REDUCIDA')
    A('* CV INSTANTANEA DE CUBIERTA CON PENDIENTE MAYOR DE 5 % = 0 KG/M2 (SIN CARGA)')
    # ---- sismo
    spec = spectrum_table(c)
    sp_lines = []
    cur = ''
    for T, v in spec:
        t = '%s %s;' % (fnum(T, 2), fnum(v, 3))
        if len(cur) + len(t) + 1 > 79:
            sp_lines.append(cur)
            cur = t
        else:
            cur = (cur + ' ' + t) if cur else t
    sp_lines.append(cur)
    masses = g.masses
    A('LOAD 4 LOADTYPE Seismic-H  TITLE SISMO X')
    A('* MASA SISMICA CONCENTRADA EN PUNTA DE COLUMNAS (CRITERIO H5-H6): CM DE')
    A('* CUBIERTA, MUROS, FALDON Y PUERTAS POR AREA TRIBUTARIA + PESO PROPIO')
    A('JOINT LOAD')
    byval = {}
    for k in ('A-1', 'C-1', 'A-2', 'C-2', 'A-3', 'B-3', 'C-3'):
        byval.setdefault(round(masses[k], 2), []).append(g.tipnodes[k])
    for v, ns in byval.items():
        L.extend(wrap(fmt_list(ns) + ['FX', fnum(v, 2), 'FZ', fnum(v, 2)]))
    A('SELFWEIGHT X 1')
    A('SELFWEIGHT Z 1')
    for lc, d, f, dom, title in ((4, 'X', c['FX'], c['DOM_X'], None), (5, 'Z', c['FZ'], c['DOM_Z'], 'SISMO Z'),
                                 (6, 'X', -c['FX'], c['DOM_X'], 'SISMO -X'), (7, 'Z', -c['FZ'], c['DOM_Z'], 'SISMO -Z')):
        if title:
            A('LOAD %d LOADTYPE Seismic-H  TITLE %s' % (lc, title))
        A('SPECTRUM SRSS %s %s ACC SCALE 981 DAMP 0.05 LIN DOMINANT %d' % (d, fnum(f, 4), dom))
        L.extend(sp_lines)
    # ---- viento
    low = {}
    for wall, axis, val in (('_OESTE', 0, XA), ('_ESTE', 0, XC), ('_NORTE', 2, Z3)):
        low[wall] = [e for e in bt['LM'] if abs(g.minfo[e]['lvl'] - c['GIRTS'][0]) < 1e-6 and inplane(e, axis, val)]
    strip = c['GIRTS'][0] / 2.0
    door_w = (dx[1] - dx[0]) / 2.0
    edoor_w = (ed[1] - ed[0]) / 2.0
    g.wind_extra = dict(low=low, strip=strip, door_w=door_w, edoor_w=edoor_w, pc=bt['PC'], pe=pe_low)
    for lc in range(8, 16):
        A('LOAD %d LOADTYPE Wind  TITLE %s' % (lc, WTITLE[lc]))
        A('ONEWAY LOAD')
        v = wc[lc]
        for grp, sgn, d in FACES:
            p = v[grp]['staad']
            if abs(p) < 1e-9:
                continue
            if grp == '_SUR':
                A('%s ONE %s %s%s' % (grp, fnum(p, 4), d, tow_txt))
            else:
                A('%s ONE %s %s' % (grp, fnum(p, 4), d))
        ml = []
        if c['WIND_STRIP']:
            for wall, dirn in (('_OESTE', 'GX'), ('_ESTE', 'GX'), ('_NORTE', 'GZ')):
                p = v[wall]['staad']
                if abs(p) < 1e-9:
                    continue
                ml.append((low[wall], dirn, p * strip))
        p = v['_NORTE']['staad']
        if c['WIND_CORTINA'] and abs(p) > 1e-9:
            ml.append((bt['PC'], 'GZ', p * door_w))
        egrp, edir = {'A': ('_OESTE', 'GX'), 'C': ('_ESTE', 'GX'), '3': ('_NORTE', 'GZ')}[c['EDOOR_WALL']]
        p = v[egrp]['staad']
        if c['WIND_EDOOR'] and abs(p) > 1e-9:
            ml.append((pe_low, edir, p * edoor_w))
        if ml:
            if c['WIND_STRIP']:
                A('* VIENTO COMO CARGA LINEAL: FRANJA INFERIOR DE MUROS Y PUERTAS')
            else:
                A('* VIENTO SOBRE PUERTAS, EN SUS POSTES (PRESION DEL MURO X MEDIO ANCHO):')
                parts = []
                if c['WIND_CORTINA']:
                    parts.append('CORTINA = MURO 3 X %s CM' % fnum(door_w, 1))
                if c['WIND_EDOOR']:
                    parts.append('PUERTA DE EMERGENCIA = MURO %s X %s CM' % (c['EDOOR_WALL'], fnum(edoor_w, 1)))
                A('* ' + '; '.join(parts))
            A('MEMBER LOAD')
            for ids, dirn, w in ml:
                L.extend(wrap(fmt_list(ids) + ['UNI', dirn, fnum(w, 4)]))
    # ---- combinaciones
    for item in COMBOS:
        if item[1] is None:
            A(item[0])
        else:
            A('LOAD COMB %d %s' % (item[0], item[1]))
            A(item[2])
    A('PERFORM ANALYSIS')
    nonrod = [e for e in g.members if g.minfo[e]['tag'] not in ('TM', 'TMF', 'TC')]
    centers = [g.nid[g.center['T2']], g.nid[g.center['T1']]]
    A('LOAD LIST 4 TO 7 16 TO 32')
    L.extend(wrap(['PRINT', 'JOINT', 'DISPLACEMENTS', 'LIST'] + fmt_list(tips + centers)))
    A('LOAD LIST 1 3 TO 66')
    A('PRINT SUPPORT REACTION')
    L.extend(wrap(['PRINT', 'MEMBER', 'FORCES', 'LIST'] + fmt_list(bt['COL'] + bt['TM'] + bt['TMF'] + bt['TC'])))
    A('LOAD LIST 33 TO 66')
    A('PARAMETER 1')
    A('CODE AISC UNIFIED 2016')
    A('FYLD %s MEMB _COLUMNAS' % fnum(c['FY_COL'], 0))
    A('* COLUMNAS: LY = SEP. DE LARGUEROS DE MURO, LZ = ALTURA AL APOYO DE ARMADURA')
    L.extend(wrap(['LY', '120', 'MEMB'] + fmt_list(bt['COL'])))
    D = c['D_TRUSS']
    lzmap = {}
    for name, keys in g.col_nodes.items():
        top = g.yroof(keys[0][2])
        if name in ('A-1', 'C-1', 'A-2', 'C-2', 'B-3'):
            hk = g.ybot(keys[0][2], at_column=True)
        elif c['BACK_TRUSS']:
            hk = g.back_top
        else:
            hk = top
        for e in bt['COL']:
            if g.minfo[e]['col'] != name:
                continue
            a, b = g.members[e]
            ymax = max(g.nodes[a][1], g.nodes[b][1])
            lz = hk if ymax <= hk + 1e-6 else (top - hk)
            lzmap.setdefault(round(lz, 2), []).append(e)
    for lz, ids in sorted(lzmap.items()):
        L.extend(wrap(['LZ', fnum(lz, 2), 'MEMB'] + fmt_list(ids)))
    g.lz_cols = lzmap
    A('* ARMADURAS: LY = FUERA DEL PLANO (CONTRAFLAMBEOS / LARGUEROS), LZ = TABLERO')
    # con armadura en el eje 3 la viga superior VT trabaja como su cuerda superior
    chords = bt['CS'] + bt['CI'] + (bt['VT'] if c['BACK_TRUSS'] else [])
    L.extend(wrap(['LY', '250', 'MEMB'] + fmt_list(chords)))
    L.extend(wrap(['LZ', fnum(c['PANEL_T'], 2), 'MEMB'] + fmt_list(chords)))
    lpan = max(g.L(e) for e in bt['CSL'])
    L.extend(wrap(['LY', fnum(c['PURLIN'], 2), 'MEMB'] + fmt_list(bt['CSL'] + bt['CIL'])))
    L.extend(wrap(['LZ', fnum(lpan, 2), 'MEMB'] + fmt_list(bt['CSL'] + bt['CIL'])))
    A('* VIGAS DE BORDE Y LARGUEROS: LY = ARRIOSTRAMIENTO, LZ = CLARO')
    L.extend(wrap(['LY', fnum(c['PURLIN'], 2), 'MEMB'] + fmt_list(bt['VR'])))
    L.extend(wrap(['LZ', '800', 'MEMB'] + fmt_list(bt['VR'])))
    lm_side = [e for e in bt['LM'] + bt['LMT'] + bt['DINE'] if g.minfo[e]['wall'] in ('A', 'C')]
    lm_back = [e for e in bt['LM'] + bt['LMT'] + bt['DIN'] + bt['DINE'] if g.minfo[e]['wall'] == '3']
    ls_side = [e for e in bt['LS'] if g.minfo[e]['wall'] in ('A', 'C')]
    vt_beam = [] if c['BACK_TRUSS'] else bt['VT']
    L.extend(wrap(['LY', '250', 'MEMB'] + fmt_list(vt_beam + bt['LC'] + lm_back)))
    L.extend(wrap(['LZ', '750', 'MEMB'] + fmt_list(vt_beam + bt['LC'] + lm_back)))
    L.extend(wrap(['LY', '266.67', 'MEMB'] + fmt_list(lm_side)))
    L.extend(wrap(['LZ', '800', 'MEMB'] + fmt_list(lm_side)))
    if ls_side:
        A('* LARGUERO SUPERIOR DE MUROS LATERALES SIN CONTRAFLAMBEOS: LY = LZ = CLARO')
        L.extend(wrap(['LY', '800', 'MEMB'] + fmt_list(ls_side)))
        L.extend(wrap(['LZ', '800', 'MEMB'] + fmt_list(ls_side)))
    L.extend(wrap(['LY', fnum(dh, 2), 'MEMB'] + fmt_list(bt['PC'])))
    if bt['MONF']:
        L.extend(wrap(['LY', fnum(c['D_TRUSS'], 2), 'MEMB'] + fmt_list(bt['MONF'])))
        L.extend(wrap(['LZ', fnum(c['D_TRUSS'], 2), 'MEMB'] + fmt_list(bt['MONF'])))
    pe_posts = bt['PE']
    L.extend(wrap(['LY', fnum(c['EDOOR_TOP'], 2), 'MEMB'] + fmt_list(pe_posts)))
    L.extend(wrap(['CHECK', 'CODE', 'MEMB'] + fmt_list(nonrod)))
    A('STEEL MEMBER TAKE OFF ALL')
    A('FINISH')
    return '\n'.join(L) + '\n'


def tributary_masses(g):
    """Peso (kg) de CM de cubierta, muros, faldon y puertas llevado a la punta de
    cada columna por area tributaria.  Devuelve dict y tabla de detalle."""
    c = g.c
    XA, XB, XC, Z3, Z2, Z1 = c['XA'], c['XB'], c['XC'], c['Z3'], c['Z2'], c['Z1']
    inc = math.sqrt(1 + c['SLOPE'] ** 2)
    yr = g.yroof
    det = {k: {} for k in ('A-1', 'C-1', 'A-2', 'C-2', 'A-3', 'B-3', 'C-3')}
    hx = (XC - XA) / 4.0          # 3.75 m
    zq1 = 0.5 * (Z3 + Z2)
    zq2 = 0.5 * (Z2 + Z1)
    # --- cubierta (m2 en planta x factor de inclinacion)
    roof = {
        'A-3': hx * (zq1 - Z3), 'C-3': hx * (zq1 - Z3), 'B-3': 2 * hx * (zq1 - Z3),
        'A-2': hx * (zq2 - zq1) + hx * (zq2 - zq1), 'C-2': hx * (zq2 - zq1) + hx * (zq2 - zq1),
        'A-1': hx * (Z1 - zq2) + hx * (Z1 - zq2), 'C-1': hx * (Z1 - zq2) + hx * (Z1 - zq2),
    }
    for k, a in roof.items():
        det[k]['area_cub'] = a / 1e4 * inc
        det[k]['w_cub'] = det[k]['area_cub'] * c['CM_ROOF']
    # --- muros laterales (trapecio bajo la cubierta)
    def trap(za, zb):
        return (zb - za) * 0.5 * (yr(za) + yr(zb)) / 1e4
    for s in ('A', 'C'):
        det[s + '-3']['area_lat'] = trap(Z3, zq1)
        det[s + '-2']['area_lat'] = trap(zq1, zq2)
        det[s + '-1']['area_lat'] = trap(zq2, Z1)
    # --- muro de fondo
    H3 = yr(Z3) / 100.0
    det['A-3']['area_fondo'] = (XB - XA) / 2 / 100.0 * H3
    det['B-3']['area_fondo'] = (XC - XA) / 2 / 100.0 * H3
    det['C-3']['area_fondo'] = (XC - XB) / 2 / 100.0 * H3
    # --- faldon del frente (de N.I.E. a cubierta)
    hf = (yr(Z1) - c['NIE']) / 100.0
    det['A-1']['area_faldon'] = (XC - XA) / 2 / 100.0 * hf
    det['C-1']['area_faldon'] = (XC - XA) / 2 / 100.0 * hf
    # --- puertas: se descuenta la lamina y se suma el peso de la puerta, repartidos a las dos
    #     columnas del claro segun la posicion del centro de la puerta
    def back_bay(xm):
        return ('A-3', XA, 'B-3', XB) if xm < XB else ('B-3', XB, 'C-3', XC)

    def add(col, key, val):
        det[col][key] = det[col].get(key, 0.0) + val
    dx = c['DOOR_X']
    a_cort = 5.0 * 6.0
    xc = 0.5 * (dx[0] + dx[1])
    n0, x0, n1, x1 = back_bay(xc)
    f0 = (x1 - xc) / (x1 - x0)
    w_cort = c['W_CORTINA'] * a_cort
    add(n0, 'area_cortina', -a_cort * f0)
    add(n1, 'area_cortina', -a_cort * (1 - f0))
    add(n0, 'w_cortina', w_cort * f0)
    add(n1, 'w_cortina', w_cort * (1 - f0))
    ew = c['EDOOR_WALL']
    if ew == '3':
        ed = c['EDOOR_X']
        xm = 0.5 * (ed[0] + ed[1])
        n0, x0, n1, x1 = back_bay(xm)
        f0 = (x1 - xm) / (x1 - x0)
    else:
        ed = c['EDOOR_Z']
        zc = 0.5 * (ed[0] + ed[1])
        if zc > Z2:
            n0, n1, f0 = ew + '-2', ew + '-1', (Z1 - zc) / (Z1 - Z2)
        else:
            n0, n1, f0 = ew + '-3', ew + '-2', (Z2 - zc) / (Z2 - Z3)
    a_ed = (ed[1] - ed[0]) / 100.0 * c['EDOOR_H'] / 100.0
    w_ed = c['W_EDOOR'] * a_ed
    add(n0, 'area_pemerg', -a_ed * f0)
    add(n1, 'area_pemerg', -a_ed * (1 - f0))
    add(n0, 'w_pemerg', w_ed * f0)
    add(n1, 'w_pemerg', w_ed * (1 - f0))
    out = {}
    for k, d in det.items():
        aw = sum(v for kk, v in d.items() if kk.startswith('area_') and kk != 'area_cub')
        d['area_muros'] = aw
        d['w_muros'] = aw * c['CM_WALL']
        d['total'] = d.get('w_cub', 0) + d['w_muros'] + d.get('w_cortina', 0) + d.get('w_pemerg', 0)
        out[k] = d['total']
    return out, det


def make(cfg=None, comment=None):
    g = Gen(cfg)
    g.masses, g.mass_detail = tributary_masses(g)
    txt = build_std(g, comment)
    return g, txt
