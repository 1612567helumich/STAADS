"""Generador del modelo STAAD del Nose Dock H1 (ND1).
Forma tipo ND23 (armaduras), cargas al estilo H5-H6 (ONEWAY por grupos, masa
sismica en punta de columnas).  Unidades: cm, kg.  X: ejes A-B-C, Z: eje 3 (0) a
eje 1 (1600, frente abierto), Y vertical desde N.P.T."""
import math
import json

DEFAULT = dict(
    # ----- geometria
    XA=0.0, XB=750.0, XC=1500.0,
    Z3=0.0, Z2=800.0, Z1=1600.0,
    Y_TOP=1166.0,            # N.S.E. (eje 3)
    SLOPE=0.051,             # 5.1 %
    D_TRUSS=138.0,           # peralte de armaduras (c/c): cuerda inferior en N.I.E.
    SNAP=12.0,               # ajuste de la cuerda inferior al larguero de muro en columna
    PANEL_T=125.0,           # tablero de armaduras transversales
    PURLIN=160.0,            # separacion de largueros de cubierta
    GIRTS=[60.0 + 120.0 * i for i in range(9)],   # 60 .. 1020
    SAG_ROOF=[250.0, 500.0, 1000.0, 1250.0],
    SAG_WALL_Z=[800.0 / 3, 1600.0 / 3, 800 + 800.0 / 3, 800 + 1600.0 / 3],
    SAG_BACK_X=[250.0, 500.0, 1000.0, 1250.0],
    DOOR_X=(33.0, 543.0), DOOR_H=660.0,           # cortina 5.00 x 6.00 (dintel en larguero 660)
    EDOOR_WALL='A',                               # muro de la puerta de emergencia: 'A', 'C' o '3'
    EDOOR_Z=(830.0, 970.0), EDOOR_H=230.0, EDOOR_TOP=300.0,
    EDOOR_X=None,                                 # postes de la puerta de emergencia si esta en el muro del eje 3
    NIE=936.0,                                    # nivel inferior de estructura (borde del faldon)
    STUB_MIN=20.0,                                # no se generan largueros mas cortos que esto entre columna y poste
    MAX_GAP=None,                                 # separacion maxima de largueros de muro; None = sin revisar (ND1 R1.x)
    FALDON_GIRT=False,                            # larguero intermedio en el faldon si el peralte de la armadura
                                                  # del eje 1 excede MAX_GAP
    TOP_DROP=100.0,                               # si la franja superior excede MAX_GAP: cajon de remate a esta distancia
                                                  # bajo la cubierta (en el punto alto del muro), como ND23 / H5-H6
    # ----- secciones
    SEC=dict(
        COL=('AISC', 'W16X26'),
        VR=('UPT', 3, 'MCE10-14'),      # vigas de borde (rafters) ejes A y C
        VT=('UPT', 3, 'MCE6-14'),       # viga superior muro eje 3
        LC=('UPT', 2, 'MC10-14'),       # largueros de cubierta
        LM=('UPT', 2, 'MC10-14'),       # largueros de muro
        LMT=('UPT', 4, 'MCC10-14'),     # larguero de remate en cajon (donde terminan los contraflambeos de muro)
        LS=('UPT', 4, 'MCC10-14'),      # larguero superior de muros laterales sin contraflambeos (CF_BELOW_TOP):
                                        # salva el claro de columna a columna sin apoyos intermedios -> cajon
        DIN=('UPT', 4, 'MCC10-14'),     # dintel cortina
        DINE=('UPT', 4, 'MCC10-14'),    # larguero-dintel sobre puerta de emergencia
        CS=('UPT', 3, 'MCE6-14'),       # cuerdas superiores armaduras transversales
        CI=('UPT', 3, 'MCE6-14'),
        CSL=('UPT', 3, 'MCE4-14'),      # cuerdas armadura longitudinal
        CIL=('UPT', 3, 'MCE4-14'),
        MON=('UPT', 1, 'C-14'),         # montantes
        MONF=('UPT', 1, 'C-14'),        # montantes de la armadura del frente cuando llevan larguero de faldon
        DIA=('UPT', 1, 'C-14'),         # diagonales
        DIAE=('UPT', 1, '2-14'),        # diagonales extremas (si se usan)
        CF=('AISC', 'PIPS7'),           # flambeos de muro
        CFC=('AISC', 'PIPS7'),          # contraflambeos de cubierta
        PC=('AISC', 'HSST4X4X0.25'),    # postes cortina
        PE=('AISC', 'HSST4X4X0.125'),   # postes puerta de emergencia
        DE=('UPT', 2, 'MC4-14'),        # dintel puerta de emergencia
        LF=('UPT', 2, 'MC4-14'),        # larguero intermedio del faldon (entre cuerdas de la armadura del eje 1)
        TM=('PRIS', 1.5875),            # tensores de muros laterales (5/8")
        TMF=('PRIS', 1.905),            # tensores del muro de fondo (3/4")
        TC=('PRIS', 1.27),              # tensores de cubierta (1/2")
    ),
    DIAE_PANELS=0,          # tableros extremos con diagonal reforzada en armaduras transversales (por lado)
    DIAE_PANELS_L=1,        # idem en cada claro de la armadura longitudinal
    RAFTER_PINNED=True,
    VT_PINNED=True,         # viga superior del eje 3 articulada en columnas
    TOP_BOX=True,           # larguero superior de muros en cajon (remate de contraflambeos, como ND23 / H5-H6)
    CF_BELOW_TOP=False,     # con larguero extra junto a la cubierta (MAX_GAP): los contraflambeos rematan en el
                            # larguero anterior (cajon) y el de arriba queda sin contraflambeo (tag LS)
    ROD_DOOR=True,          # el tensor del claro de la puerta de emergencia arranca sobre su cajon (no cruza la puerta)
    BACK_BRACE=False,       # sin tensores en el muro de fondo (peticion del cliente)
    BACK_TRUSS=False,       # armadura en el plano del muro de fondo (viga superior - cajon de remate)
    # ----- cargas
    CM_ROOF=19.32, CM_WALL=5.85, CV_ROOF=20.0,
    W_CORTINA=11.82, W_EDOOR=31.0, EDOOR_LINE=0.8,
    VMAX=120.0, GUST=1.3, ZONE_K=1.0, ZONE_A=4.5,
    # viento como carga lineal en barras (no lo genera el ONEWAY por grupos):
    WIND_CORTINA=True,      # sobre la cortina: presion del muro 3 x medio ancho de puerta en cada poste
    WIND_EDOOR=True,        # sobre la puerta de emergencia: presion del muro A x medio ancho en cada poste
    WIND_STRIP=False,       # franja de lamina bajo el primer larguero
    ROD_DOOR_TIE=False,     # tensor A-3 base -> A-2 en +3.00 (hace trabajar al tensor de la puerta)
    A=0.4, CO=3.0, TO=0.6, I=1.0, R=7.0, CD=6.0,
    FX=1.0, FZ=1.0, DOM_X=1, DOM_Z=2, NMODES=80,
    FY_COL=3515.0,
    TITLE='NOSE DOCK H1 (ND1)',
    DATE='10/11/2026',
)


def fnum(v, nd=3):
    s = ('%.' + str(nd) + 'f') % v
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    if s in ('-0', ''):
        s = '0'
    return s


def fmt_list(ids):
    ids = sorted(set(ids))
    out = []
    i = 0
    while i < len(ids):
        j = i
        while j + 1 < len(ids) and ids[j + 1] == ids[j] + 1:
            j += 1
        if j - i >= 2:
            out += [str(ids[i]), 'TO', str(ids[j])]
        elif j - i == 1:
            out += [str(ids[i]), str(ids[j])]
        else:
            out.append(str(ids[i]))
        i = j + 1
    return out


def wrap(tokens, width=79):
    """Une tokens en lineas <= width con continuacion ' -'.  No separa 'a TO b' ni
    la cola de palabras clave (lo que sigue al ultimo numero/TO/grupo de la lista)."""
    import re as _re
    n = len(tokens)
    # cola: desde el primer token no numerico (distinto de TO/BY/_GRUPO) hasta el final
    k = n
    for i, t in enumerate(tokens):
        if i == 0:
            continue
        if not (_re.fullmatch(r'-?\d+', t) or t in ('TO', 'BY')):
            k = i
            break
    head = tokens[:k] if k > 1 else tokens[:1]
    tail = tokens[len(head):]
    chunks = []
    i = 0
    while i < len(head):
        if i + 2 < len(head) and head[i + 1] == 'TO':
            chunks.append(' '.join(head[i:i + 3]))
            i += 3
        else:
            chunks.append(head[i])
            i += 1
    if tail:
        chunks.append(' '.join(tail))
    lines = []
    cur = ''
    for ch in chunks:
        test = (cur + ' ' + ch) if cur else ch
        if len(test) > width - 2 and cur:
            lines.append(cur + ' -')
            cur = ch
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


class Gen:
    def __init__(self, cfg=None):
        self.c = dict(DEFAULT)
        if cfg:
            for k, v in cfg.items():
                if k == 'SEC':
                    s = dict(self.c['SEC'])
                    s.update({kk: tuple(vv) for kk, vv in v.items()})
                    self.c['SEC'] = s
                else:
                    self.c[k] = v
        self._nodes = {}          # key -> (x,y,z)
        self._order = []
        self.mem = []             # (tag, key1, key2, attrs)
        self.build()
        self.number()

    # ------------------------------------------------------------ geometria base
    def yroof(self, z):
        return self.c['Y_TOP'] - self.c['SLOPE'] * z

    def zone_levels(self, zhigh):
        """Niveles de largueros de una zona de muro cuya cubierta mas alta esta en zhigh
        y nivel de su cajon de remate.  Si del ultimo larguero a la cubierta hay mas de
        MAX_GAP se agrega un cajon TOP_DROP abajo de la cubierta."""
        c = self.c
        lv = list(c['GIRTS'])
        top = lv[-1]
        if c['MAX_GAP'] is not None and self.yroof(zhigh) - lv[-1] > c['MAX_GAP'] + 1e-6:
            top = round(self.yroof(zhigh) - c['TOP_DROP'], 1)
            lv.append(top)
        return lv, top

    def ybot(self, z, at_column=False, levels=None):
        """Nivel de la cuerda inferior en la posicion z.  En columna se ajusta al
        larguero de muro mas cercano si queda a menos de SNAP (evita tramos cortos)."""
        y = self.yroof(z) - self.c['D_TRUSS']
        if at_column:
            for g in (levels if levels is not None else self.c['GIRTS']):
                if abs(g - y) <= self.c['SNAP'] + 1e-9:
                    return g
        return y

    def key(self, x, y, z):
        return (round(x, 3), round(y, 3), round(z, 3))

    def nd(self, x, y, z, prio=5):
        k = self.key(x, y, z)
        if k not in self._nodes:
            self._nodes[k] = prio
            self._order.append(k)
        else:
            self._nodes[k] = min(self._nodes[k], prio)
        return k

    def mb(self, tag, a, b, **attrs):
        if a == b:
            raise ValueError('miembro de longitud cero ' + tag)
        self.mem.append((tag, a, b, attrs))

    def chain(self, tag, pts, **attrs):
        """Crea miembros consecutivos entre la lista de puntos (x,y,z)."""
        keys = [self.nd(*p) for p in pts]
        for a, b in zip(keys[:-1], keys[1:]):
            self.mb(tag, a, b, **attrs)
        return keys

    def build(self):
        c = self.c
        XA, XB, XC = c['XA'], c['XB'], c['XC']
        Z3, Z2, Z1 = c['Z3'], c['Z2'], c['Z1']
        D = c['D_TRUSS']
        G = c['GIRTS']
        yr = self.yroof
        self.tips = {}
        self.col_nodes = {}
        # ---------------- niveles de largueros por zona de muro
        dh = c['DOOR_H']
        lv_back, self.back_top = self.zone_levels(Z3)          # muro del eje 3
        lv_s32, top_s32 = self.zone_levels(Z3)                 # muros laterales, claro 3-2
        lv_s21, top_s21 = self.zone_levels(Z2)                 # muros laterales, claro 2-1
        self.lv_back, self.side_zones = lv_back, ((Z3, Z2, lv_s32, top_s32), (Z2, Z1, lv_s21, top_s21))

        def box_level(lv, top):
            # nivel donde rematan los contraflambeos (cajon): el larguero superior, o el anterior
            # si el superior es el extra junto a la cubierta y CF_BELOW_TOP
            extra = not any(abs(top - q) < 1e-6 for q in G)
            return lv[-2] if (c['CF_BELOW_TOP'] and extra) else top
        self.back_box = box_level(lv_back, self.back_top)
        self.side_box = {Z3: box_level(lv_s32, top_s32), Z2: box_level(lv_s21, top_s21)}
        cbay = (XA, XB) if 0.5 * (c['DOOR_X'][0] + c['DOOR_X'][1]) < XB else (XB, XC)      # claro de la cortina
        col_lv = {'A-3': set(lv_back) | set(lv_s32), 'C-3': set(lv_back) | set(lv_s32), 'B-3': set(lv_back),
                  'A-2': set(lv_s32) | set(lv_s21), 'C-2': set(lv_s32) | set(lv_s21),
                  'A-1': set(lv_s21), 'C-1': set(lv_s21)}
        for name, xcol in (('A-3', XA), ('B-3', XB), ('C-3', XC)):
            if abs(xcol - cbay[0]) < 1e-6 or abs(xcol - cbay[1]) < 1e-6:
                col_lv[name].add(dh)                           # el dintel de la cortina llega a sus dos columnas
        self.faldon_lv = []
        if c['FALDON_GIRT'] and c['MAX_GAP'] is not None and D > c['MAX_GAP'] + 1e-6:
            nfg = int(math.ceil(D / c['MAX_GAP'] - 1e-9)) - 1
            self.faldon_lv = [round(yr(Z1) - D + D * k / (nfg + 1), 3) for k in range(1, nfg + 1)]
            # si queda junto a un larguero del muro lateral se lleva a ese nivel (evita tramos cortos de columna)
            self.faldon_lv = [next((q for q in sorted(col_lv['A-1']) if abs(q - v) <= c['SNAP'] + 1e-9), v) for v in self.faldon_lv]
            for name in ('A-1', 'C-1'):
                col_lv[name] |= set(self.faldon_lv)
        self.col_lv = col_lv
        # ---------------- columnas
        cols = [('A-1', XA, Z1), ('C-1', XC, Z1), ('A-2', XA, Z2), ('C-2', XC, Z2),
                ('A-3', XA, Z3), ('B-3', XB, Z3), ('C-3', XC, Z3)]
        for name, x, z in cols:
            top = yr(z)
            ys = [0.0] + [g for g in sorted(col_lv[name]) if g < top - 1e-6]
            if name in ('A-1', 'C-1', 'A-2', 'C-2', 'B-3'):
                ys.append(self.ybot(z, at_column=True, levels=sorted(col_lv[name])))
            ys.append(top)
            ys = sorted(set(round(v, 3) for v in ys))
            self.nd(x, 0.0, z, prio=0)
            beta = 90.0 if name == 'B-3' else 0.0
            keys = self.chain('COL', [(x, y, z) for y in ys], col=name, beta=beta)
            self.tips[name] = keys[-1]
            self.col_nodes[name] = keys
        # ---------------- vigas de borde (rafters) y viga superior del muro eje 3
        zp = [Z3 + c['PURLIN'] * i for i in range(int(round((Z1 - Z3) / c['PURLIN'])) + 1)]
        self.zp = zp
        for x, side in ((XA, 'A'), (XC, 'C')):
            keys = self.chain('VR', [(x, yr(z), z) for z in zp], side=side)
        xs_top = sorted(set([XA, XB, XC] + c['SAG_ROOF']))
        if c['BACK_TRUSS']:
            npb = int(round((XC - XA) / c['PANEL_T']))
            xs_top = [XA + c['PANEL_T'] * i for i in range(npb + 1)]
        self.xs_top = xs_top
        self.chain('VT', [(x, yr(Z3), Z3) for x in xs_top])
        if c['BACK_TRUSS']:
            # cuerda superior = viga VT, cuerda inferior = cajon de remate (larguero superior del muro)
            yt = yr(Z3)
            yb = self.back_top
            for x in xs_top[1:-1]:
                if abs(x - XB) < 1e-6:
                    continue
                self.mb('MON', self.nd(x, yb, Z3), self.nd(x, yt, Z3), truss='T3')
            for i in range(npb):
                xm = 0.5 * (xs_top[i] + xs_top[i + 1])
                # diagonales bajando hacia el centro de cada claro (A-B y B-C)
                left = (xm < 0.5 * (XA + XB)) or (XB < xm < 0.5 * (XB + XC))
                if left:
                    self.mb('DIA', self.nd(xs_top[i], yt, Z3), self.nd(xs_top[i + 1], yb, Z3), truss='T3')
                else:
                    self.mb('DIA', self.nd(xs_top[i + 1], yt, Z3), self.nd(xs_top[i], yb, Z3), truss='T3')
        # ---------------- armaduras transversales (eje 2 y eje 1)
        np_ = int(round((XC - XA) / c['PANEL_T']))
        xt = [XA + c['PANEL_T'] * i for i in range(np_ + 1)]
        self.xt = xt
        for z, tn in ((Z2, 'T2'), (Z1, 'T1')):
            yt = yr(z)
            yb = yt - D
            self.chain('CS', [(x, yt, z) for x in xt], truss=tn)
            self.chain('CI', [(x, yb, z) for x in xt], truss=tn)
            flv = self.faldon_lv if tn == 'T1' else []
            for i, x in enumerate(xt[1:-1], start=1):
                if flv:
                    # montante continuo (viga articulada en las cuerdas) que recibe el larguero del faldon
                    ks = [self.nd(x, y, z) for y in [yb] + flv + [yt]]
                    for j, (a, b) in enumerate(zip(ks[:-1], ks[1:])):
                        rel = (['START'] if j == 0 else []) + (['END'] if j == len(ks) - 2 else [])
                        self.mb('MONF', a, b, truss=tn, rel=rel)
                else:
                    self.mb('MON', self.nd(x, yb, z), self.nd(x, yt, z), truss=tn)
            for yg in flv:
                ks = [self.nd(x, yg, z) for x in xt]
                for a, b in zip(ks[:-1], ks[1:]):
                    self.mb('LF', a, b, truss=tn, rel=['START', 'END'], lvl=yg)
            mid = np_ // 2
            for i in range(np_):
                ext = (i < c['DIAE_PANELS']) or (i >= np_ - c['DIAE_PANELS'])
                tag = 'DIAE' if ext else 'DIA'
                if i < mid:
                    self.mb(tag, self.nd(xt[i], yt, z), self.nd(xt[i + 1], yb, z), truss=tn)
                else:
                    self.mb(tag, self.nd(xt[i + 1], yt, z), self.nd(xt[i], yb, z), truss=tn)
        # ---------------- armadura longitudinal (eje B)
        for (za, zb, span) in ((Z3, Z2, 'TL1'), (Z2, Z1, 'TL2')):
            zs = [z for z in zp if za - 1e-6 <= z <= zb + 1e-6]
            yb = lambda z: self.ybot(z, at_column=(abs(z - Z3) < 1e-6), levels=sorted(col_lv['B-3']))
            self.chain('CSL', [(XB, yr(z), z) for z in zs], truss=span)
            self.chain('CIL', [(XB, yb(z), z) for z in zs], truss=span)
            for z in zs[1:-1]:
                self.mb('MON', self.nd(XB, yb(z), z), self.nd(XB, yr(z), z), truss=span)
            n = len(zs) - 1
            for i in range(n):
                zm = 0.5 * (za + zb)
                ext = (i < c['DIAE_PANELS_L']) or (i >= n - c['DIAE_PANELS_L'])
                tag = 'DIAE' if ext else 'DIA'
                if 0.5 * (zs[i] + zs[i + 1]) < zm:
                    self.mb(tag, self.nd(XB, yr(zs[i]), zs[i]), self.nd(XB, yb(zs[i + 1]), zs[i + 1]), truss=span)
                else:
                    self.mb(tag, self.nd(XB, yr(zs[i + 1]), zs[i + 1]), self.nd(XB, yb(zs[i]), zs[i]), truss=span)
        # ---------------- largueros de cubierta
        xs_p = sorted(set([XA, XB, XC] + c['SAG_ROOF']))
        self.xs_p = xs_p
        for z in zp:
            if abs(z - Z3) < 1e-6 or abs(z - Z2) < 1e-6 or abs(z - Z1) < 1e-6:
                continue
            for half in (0, 1):
                seg = [x for x in xs_p if (x <= XB + 1e-6 if half == 0 else x >= XB - 1e-6)]
                keys = [self.nd(x, yr(z), z) for x in seg]
                for i, (a, b) in enumerate(zip(keys[:-1], keys[1:])):
                    rel = []
                    if i == 0:
                        rel.append('START')
                    if i == len(keys) - 2:
                        rel.append('END')
                    self.mb('LC', a, b, rel=rel, z=z)
        # ---------------- contraflambeos de cubierta
        for x in c['SAG_ROOF']:
            self.chain('CFC', [(x, yr(z), z) for z in zp])
        # ---------------- muros laterales (ejes A y C)
        ew = c['EDOOR_WALL']
        ed = c['EDOOR_Z'] if ew in ('A', 'C') else None
        et = c['EDOOR_TOP']
        for x, side in ((XA, 'A'), (XC, 'C')):
            door = (ed is not None and side == ew)
            for g in sorted(set(lv_s32) | set(lv_s21)):
                for (za, zb, lv, ztop) in self.side_zones:
                    if not any(abs(g - q) < 1e-6 for q in lv):
                        continue
                    dbay = door and za - 1e-6 <= ed[0] and ed[1] <= zb + 1e-6      # la puerta esta en este claro
                    zbox = self.side_box[za]
                    is_ls = g > zbox + 1e-6               # larguero superior sin contraflambeo
                    zs = [za] + [sz for sz in c['SAG_WALL_Z'] if za + 1e-6 < sz < zb - 1e-6 and not is_ls] + [zb]
                    if dbay and g <= et + 1e-6:
                        zs = sorted(set(zs + list(ed)))
                    keys = [self.nd(x, g, z) for z in zs]
                    for (a, b, z0, z1) in zip(keys[:-1], keys[1:], zs[:-1], zs[1:]):
                        if dbay and g < et - 1e-6 and abs(z0 - ed[0]) < 1e-6 and abs(z1 - ed[1]) < 1e-6:
                            continue     # hueco de puerta de emergencia
                        rel = []
                        ends = [za, zb] + (list(ed) if (dbay and g < et - 1e-6) else [])
                        if any(abs(z0 - q) < 1e-6 for q in ends):
                            rel.append('START')
                        if any(abs(z1 - q) < 1e-6 for q in ends):
                            rel.append('END')
                        tag = 'LM'
                        if c['TOP_BOX'] and abs(g - zbox) < 1e-6:
                            tag = 'LMT'
                        if is_ls:
                            tag = 'LS'
                        if dbay and abs(g - et) < 1e-6:
                            tag = 'DINE'
                        self.mb(tag, a, b, rel=rel, wall=side, lvl=g)
            # flambeos
            for z in c['SAG_WALL_Z']:
                zn = next(zn for zn in self.side_zones if zn[0] - 1e-6 <= z <= zn[1] + 1e-6)
                ys = [0.0] + [q for q in zn[2] if q <= self.side_box[zn[0]] + 1e-6]
                self.nd(x, 0.0, z, prio=2)
                self.chain('CF', [(x, y, z) for y in ys], wall=side)
        # puerta de emergencia en un muro lateral
        if ed is not None:
            xw = XA if ew == 'A' else XC
            for z in ed:
                ys = [0.0] + [g for g in G if g < et - 1e-6] + [c['EDOOR_H'], et]
                ys = sorted(set(ys))
                self.nd(xw, 0.0, z, prio=1)
                keys = [self.nd(xw, y, z) for y in ys]
                for i, (a, b) in enumerate(zip(keys[:-1], keys[1:])):
                    self.mb('PE', a, b, wall=ew, rel=(['END'] if i == len(keys) - 2 else []))
            self.mb('DE', self.nd(xw, c['EDOOR_H'], ed[0]), self.nd(xw, c['EDOOR_H'], ed[1]), rel=['START', 'END'], wall=ew)
        # ---------------- muro eje 3 (fondo): cortina y, en su caso, puerta de emergencia
        dx = c['DOOR_X']
        ex = c['EDOOR_X'] if ew == '3' else None
        cols_x = (XA, XB, XC)
        G3 = lv_back
        dh_reg = any(abs(dh - q) < 1e-6 for q in G3)       # el dintel de la cortina coincide con un larguero

        def inside(xv, rng):
            return rng is not None and rng[0] + 1e-6 < xv < rng[1] - 1e-6

        def cf_from(xv):
            """Nivel desde el que existe la linea de contraflambeo en xv (0 = desde el piso)."""
            if inside(xv, dx):
                return dh
            if inside(xv, ex):
                return et
            return 0.0
        # tramo del cajon donde rematan los postes de la puerta de emergencia: entre los
        # apoyos (columna o poste de cortina) que la flanquean
        espan = None
        if ex is not None:
            sup = sorted(set(list(cols_x) + (list(dx) if et < dh + 1e-6 else [])))
            espan = (max(v for v in sup if v <= ex[0] + 1e-6), min(v for v in sup if v >= ex[1] - 1e-6))
        for g in sorted(set(G3) | {dh}):
            only_din = (abs(g - dh) < 1e-6 and not dh_reg)   # nivel exclusivo del dintel: solo en el claro de la cortina
            xs = set(cols_x)
            xs |= {sx for sx in c['SAG_BACK_X'] if cf_from(sx) - 1e-6 <= g <= self.back_box + 1e-6}
            if g <= dh + 1e-6:
                xs |= set(dx)
            if ex is not None and g <= et + 1e-6:
                xs |= set(ex)
            if c['BACK_TRUSS'] and abs(g - self.back_top) < 1e-6:
                xs |= set(self.xs_top)
            if only_din:
                xs = {xv for xv in xs if cbay[0] - 1e-6 <= xv <= cbay[1] + 1e-6}
            xs = sorted(xs)
            # postes en los que termina un larguero de este nivel (queda articulado ahi)
            ends = list(cols_x)
            if g < dh - 1e-6:
                ends += list(dx)
            if ex is not None and g < et - 1e-6:
                ends += list(ex)
            for x0, x1 in zip(xs[:-1], xs[1:]):
                if g < dh - 1e-6 and x0 >= dx[0] - 1e-6 and x1 <= dx[1] + 1e-6:
                    continue        # vano de la cortina
                if ex is not None and g < et - 1e-6 and x0 >= ex[0] - 1e-6 and x1 <= ex[1] + 1e-6:
                    continue        # vano de la puerta de emergencia
                rel = []
                if any(abs(x0 - q) < 1e-6 for q in ends):
                    rel.append('START')
                if any(abs(x1 - q) < 1e-6 for q in ends):
                    rel.append('END')
                tag = 'LM'
                if c['TOP_BOX'] and abs(g - self.back_box) < 1e-6:
                    tag = 'LMT'
                # arriba del cajon (CF_BELOW_TOP) queda un larguero normal: con armadura T3 es su cuerda
                # inferior y se apoya en sus montantes a cada tablero
                if abs(g - dh) < 1e-6 and x0 >= cbay[0] - 1e-6 and x1 <= cbay[1] + 1e-6:
                    # dintel de cortina: cajon continuo de columna a columna
                    tag = 'DIN'
                    rel = []
                    if abs(x0 - cbay[0]) < 1e-6:
                        rel.append('START')
                    if abs(x1 - cbay[1]) < 1e-6:
                        rel.append('END')
                if espan is not None and abs(g - et) < 1e-6 and x0 >= espan[0] - 1e-6 and x1 <= espan[1] + 1e-6:
                    # cajon donde rematan los postes de la puerta de emergencia
                    tag = 'DINE'
                    rel = []
                    if abs(x0 - espan[0]) < 1e-6:
                        rel.append('START')
                    if abs(x1 - espan[1]) < 1e-6:
                        rel.append('END')
                iscol0 = any(abs(x0 - q) < 1e-6 for q in cols_x)
                iscol1 = any(abs(x1 - q) < 1e-6 for q in cols_x)
                if tag == 'LM' and (x1 - x0) < c['STUB_MIN'] - 1e-6 and (iscol0 != iscol1):
                    continue        # larguero muy corto entre columna y poste: no se modela
                self.mb(tag, self.nd(x0, g, Z3), self.nd(x1, g, Z3), rel=rel, wall='3', lvl=g)
        for sx in c['SAG_BACK_X']:
            y0 = cf_from(sx)
            if y0 <= 1e-6:
                ys = [0.0] + [g for g in G3 if g <= self.back_box + 1e-6]
                self.nd(sx, 0.0, Z3, prio=2)
            else:
                lvs = sorted(set(G3) | ({dh} if inside(sx, dx) else set()))
                ys = [g for g in lvs if y0 - 1e-6 <= g <= self.back_box + 1e-6]
            self.chain('CF', [(sx, y, Z3) for y in ys], wall='3')
        for xp in dx:
            ys = sorted(set([0.0] + [g for g in G3 if g < dh - 1e-6] + [dh]))
            self.nd(xp, 0.0, Z3, prio=1)
            keys = [self.nd(xp, y, Z3) for y in ys]
            for i, (a, b) in enumerate(zip(keys[:-1], keys[1:])):
                self.mb('PC', a, b, wall='3', rel=(['END'] if i == len(keys) - 2 else []))
        if ex is not None:
            for xp in ex:
                ys = [0.0] + [g for g in G if g < et - 1e-6] + [c['EDOOR_H'], et]
                ys = sorted(set(ys))
                self.nd(xp, 0.0, Z3, prio=1)
                keys = [self.nd(xp, y, Z3) for y in ys]
                for i, (a, b) in enumerate(zip(keys[:-1], keys[1:])):
                    self.mb('PE', a, b, wall='3', rel=(['END'] if i == len(keys) - 2 else []))
            self.mb('DE', self.nd(ex[0], c['EDOOR_H'], Z3), self.nd(ex[1], c['EDOOR_H'], Z3), rel=['START', 'END'], wall='3')
        # ---------------- tensores
        t = self.tips
        base = lambda n: self.key(*{'A-1': (XA, 0, Z1), 'C-1': (XC, 0, Z1), 'A-2': (XA, 0, Z2), 'C-2': (XC, 0, Z2),
                                    'A-3': (XA, 0, Z3), 'B-3': (XB, 0, Z3), 'C-3': (XC, 0, Z3)}[n])
        for s in ('A', 'C'):
            self.mb('TM', base(s + '-3'), t[s + '-2'], wall=s)
            self.mb('TM', base(s + '-2'), t[s + '-3'], wall=s)
            low2 = base(s + '-2')
            rod_door = (c['ROD_DOOR'] and c['EDOOR_WALL'] == s)
            if rod_door:
                # la puerta de emergencia queda junto a la columna A-2: el tensor arranca en
                # el cajon de +3.00 (criterio H5-H6) para no atravesar el vano
                low2 = self.key(XA if s == 'A' else XC, c['EDOOR_TOP'], Z2)
                if low2 not in self._nodes:
                    raise ValueError('no existe el nudo de arranque del tensor sobre la puerta')
            self.mb('TM', low2, t[s + '-1'], wall=s, door=rod_door)
            self.mb('TM', base(s + '-1'), t[s + '-2'], wall=s)
        if c['ROD_DOOR_TIE'] and c['ROD_DOOR'] and c['EDOOR_WALL'] == 'A':
            self.mb('TM', base('A-3'), self.key(XA, c['EDOOR_TOP'], Z2), wall='A', tie=True)
        if c['BACK_BRACE']:
            self.mb('TMF', base('B-3'), t['C-3'], wall='3')
            self.mb('TMF', base('C-3'), t['B-3'], wall='3')
        cT2 = self.nd(XB, yr(Z2), Z2)
        cT1 = self.nd(XB, yr(Z1), Z1)
        self.center = {'T2': cT2, 'T1': cT1}
        self.mb('TC', t['A-3'], cT2)
        self.mb('TC', t['A-2'], t['B-3'])
        self.mb('TC', t['B-3'], t['C-2'])
        self.mb('TC', cT2, t['C-3'])
        self.mb('TC', t['A-1'], cT2)
        self.mb('TC', t['A-2'], cT1)
        self.mb('TC', cT1, t['C-2'])
        self.mb('TC', cT2, t['C-1'])

    # ------------------------------------------------------------ numeracion
    ORDER = ['COL', 'VR', 'VT', 'CS', 'CI', 'CSL', 'CIL', 'MON', 'MONF', 'DIA', 'DIAE', 'LC', 'CFC', 'LM', 'LMT', 'LS', 'LF', 'DIN',
             'DINE', 'CF', 'PC', 'PE', 'DE', 'TM', 'TMF', 'TC']

    def number(self):
        keys = list(self._nodes)
        keys.sort(key=lambda k: (0 if k[1] == 0 else 1, self._nodes[k] if k[1] == 0 else 0, k[1], k[2], k[0]))
        self.nid = {k: i + 1 for i, k in enumerate(keys)}
        self.nodes = {self.nid[k]: k for k in keys}
        self.members = {}
        self.minfo = {}
        self.bytag = {t: [] for t in self.ORDER}
        n = 0
        for tag in self.ORDER:
            for (tg, a, b, attrs) in self.mem:
                if tg != tag:
                    continue
                n += 1
                self.members[n] = (self.nid[a], self.nid[b])
                self.minfo[n] = dict(tag=tag, **attrs)
                self.bytag[tag].append(n)
        # duplicados
        seen = {}
        for e, (a, b) in self.members.items():
            k = (min(a, b), max(a, b))
            if k in seen:
                raise ValueError('miembro duplicado %d y %d' % (seen[k], e))
            seen[k] = e

    def L(self, e):
        a, b = self.members[e]
        return math.dist(self.nodes[a], self.nodes[b])

    def sel(self, **kw):
        out = []
        for e, inf in self.minfo.items():
            ok = True
            for k, v in kw.items():
                if callable(v):
                    if not v(inf.get(k)):
                        ok = False
                        break
                elif inf.get(k) != v:
                    ok = False
                    break
            if ok:
                out.append(e)
        return out
