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
    EDOOR_Z=(830.0, 970.0), EDOOR_H=230.0, EDOOR_TOP=300.0,
    # ----- secciones
    SEC=dict(
        COL=('AISC', 'W16X26'),
        VR=('UPT', 3, 'MCE10-14'),      # vigas de borde (rafters) ejes A y C
        VT=('UPT', 3, 'MCE6-14'),       # viga superior muro eje 3
        LC=('UPT', 2, 'MC10-14'),       # largueros de cubierta
        LM=('UPT', 2, 'MC10-14'),       # largueros de muro
        LMT=('UPT', 4, 'MCC10-14'),     # larguero de remate en cajon (donde terminan los contraflambeos de muro)
        DIN=('UPT', 4, 'MCC10-14'),     # dintel cortina
        DINE=('UPT', 4, 'MCC10-14'),    # larguero-dintel sobre puerta de emergencia
        CS=('UPT', 3, 'MCE6-14'),       # cuerdas superiores armaduras transversales
        CI=('UPT', 3, 'MCE6-14'),
        CSL=('UPT', 3, 'MCE4-14'),      # cuerdas armadura longitudinal
        CIL=('UPT', 3, 'MCE4-14'),
        MON=('UPT', 1, 'C-14'),         # montantes
        DIA=('UPT', 1, 'C-14'),         # diagonales
        DIAE=('UPT', 1, '2-14'),        # diagonales extremas (si se usan)
        CF=('AISC', 'PIPS7'),           # flambeos de muro
        CFC=('AISC', 'PIPS7'),          # contraflambeos de cubierta
        PC=('AISC', 'HSST4X4X0.25'),    # postes cortina
        PE=('AISC', 'HSST4X4X0.125'),   # postes puerta de emergencia
        DE=('UPT', 2, 'MC4-14'),        # dintel puerta de emergencia
        TM=('PRIS', 1.5875),            # tensores de muros laterales (5/8")
        TMF=('PRIS', 1.905),            # tensores del muro de fondo (3/4")
        TC=('PRIS', 1.27),              # tensores de cubierta (1/2")
    ),
    DIAE_PANELS=0,          # tableros extremos con diagonal reforzada en armaduras transversales (por lado)
    DIAE_PANELS_L=1,        # idem en cada claro de la armadura longitudinal
    RAFTER_PINNED=True,
    VT_PINNED=True,         # viga superior del eje 3 articulada en columnas
    TOP_BOX=True,           # larguero superior de muros en cajon (remate de contraflambeos, como ND23 / H5-H6)
    ROD_DOOR=True,          # el tensor del claro de la puerta de emergencia arranca sobre su cajon (no cruza la puerta)
    BACK_BRACE=False,       # sin tensores en el muro de fondo (peticion del cliente)
    BACK_TRUSS=False,       # armadura en el plano del muro de fondo (viga superior - cajon de remate)
    # ----- cargas
    CM_ROOF=19.32, CM_WALL=5.85, CV_ROOF=20.0,
    W_CORTINA=11.82, W_EDOOR=31.0, EDOOR_LINE=0.8,
    VMAX=120.0, GUST=1.3, ZONE_K=1.0, ZONE_A=4.5,
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

    def ybot(self, z, at_column=False):
        """Nivel de la cuerda inferior en la posicion z.  En columna se ajusta al
        larguero de muro mas cercano si queda a menos de SNAP (evita tramos cortos)."""
        y = self.yroof(z) - self.c['D_TRUSS']
        if at_column:
            for g in self.c['GIRTS']:
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
        # ---------------- columnas
        cols = [('A-1', XA, Z1), ('C-1', XC, Z1), ('A-2', XA, Z2), ('C-2', XC, Z2),
                ('A-3', XA, Z3), ('B-3', XB, Z3), ('C-3', XC, Z3)]
        for name, x, z in cols:
            top = yr(z)
            ys = [0.0] + [g for g in G if g < top - 1e-6]
            if name in ('A-1', 'C-1', 'A-2', 'C-2', 'B-3'):
                ys.append(self.ybot(z, at_column=True))
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
            yb = G[-1]
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
            for i, x in enumerate(xt[1:-1], start=1):
                self.mb('MON', self.nd(x, yb, z), self.nd(x, yt, z), truss=tn)
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
            yb = lambda z: self.ybot(z, at_column=(abs(z - Z3) < 1e-6))
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
        ed = c['EDOOR_Z']
        for x, side in ((XA, 'A'), (XC, 'C')):
            for g in G:
                zs = sorted(set([Z3, Z2, Z1] + c['SAG_WALL_Z']))
                if side == 'A' and g <= c['EDOOR_TOP'] + 1e-6:
                    zs = sorted(set(zs + list(ed)))
                pts = [(x, g, z) for z in zs]
                keys = [self.nd(*p) for p in pts]
                for (a, b, z0, z1) in zip(keys[:-1], keys[1:], zs[:-1], zs[1:]):
                    if side == 'A' and g < c['EDOOR_TOP'] - 1e-6 and abs(z0 - ed[0]) < 1e-6 and abs(z1 - ed[1]) < 1e-6:
                        continue     # hueco de puerta de emergencia
                    rel = []
                    cols_z = (Z3, Z2, Z1)
                    posts = ed if (side == 'A' and g < c['EDOOR_TOP'] - 1e-6) else ()
                    if any(abs(z0 - q) < 1e-6 for q in cols_z) or any(abs(z0 - q) < 1e-6 for q in posts):
                        rel.append('START')
                    if any(abs(z1 - q) < 1e-6 for q in cols_z) or any(abs(z1 - q) < 1e-6 for q in posts):
                        rel.append('END')
                    tag = 'LM'
                    if c['TOP_BOX'] and abs(g - G[-1]) < 1e-6:
                        tag = 'LMT'
                    if side == 'A' and abs(g - c['EDOOR_TOP']) < 1e-6 and z0 >= Z2 - 1e-6:
                        tag = 'DINE'
                    self.mb(tag, a, b, rel=rel, wall=side, lvl=g)
            # flambeos
            for z in c['SAG_WALL_Z']:
                ys = [0.0] + G
                self.nd(x, 0.0, z, prio=2)
                self.chain('CF', [(x, y, z) for y in ys], wall=side)
        # puerta de emergencia (muro eje A)
        for z in ed:
            ys = [0.0] + [g for g in G if g < c['EDOOR_TOP'] - 1e-6] + [c['EDOOR_H'], c['EDOOR_TOP']]
            ys = sorted(set(ys))
            self.nd(XA, 0.0, z, prio=1)
            keys = [self.nd(XA, y, z) for y in ys]
            for i, (a, b) in enumerate(zip(keys[:-1], keys[1:])):
                self.mb('PE', a, b, wall='A', rel=(['END'] if i == len(keys) - 2 else []))
        self.mb('DE', self.nd(XA, c['EDOOR_H'], ed[0]), self.nd(XA, c['EDOOR_H'], ed[1]), rel=['START', 'END'], wall='A')
        # ---------------- muro eje 3 (fondo)
        dx = c['DOOR_X']
        dh = c['DOOR_H']
        for g in G:
            if g < dh - 1e-6:
                runs = [[XA, dx[0]], [dx[1], XB], [XB] + [s for s in c['SAG_BACK_X'] if s > XB] + [XC]]
            elif abs(g - dh) < 1e-6:
                runs = [sorted(set([XA, dx[0]] + [s for s in c['SAG_BACK_X'] if s < XB] + [dx[1], XB])),
                        [XB] + [s for s in c['SAG_BACK_X'] if s > XB] + [XC]]
            else:
                runs = [[XA] + [s for s in c['SAG_BACK_X'] if s < XB] + [XB],
                        [XB] + [s for s in c['SAG_BACK_X'] if s > XB] + [XC]]
            if c['BACK_TRUSS'] and abs(g - G[-1]) < 1e-6:
                runs = [[x for x in self.xs_top if x <= XB + 1e-6], [x for x in self.xs_top if x >= XB - 1e-6]]
            for run in runs:
                keys = [self.nd(x, g, Z3) for x in run]
                for (a, b, x0, x1) in zip(keys[:-1], keys[1:], run[:-1], run[1:]):
                    rel = []
                    ends = [XA, XB, XC] + ([dx[0], dx[1]] if g <= dh + 1e-6 else [])
                    if any(abs(x0 - q) < 1e-6 for q in ends):
                        rel.append('START')
                    if any(abs(x1 - q) < 1e-6 for q in ends):
                        rel.append('END')
                    tag = 'LM'
                    if c['TOP_BOX'] and abs(g - G[-1]) < 1e-6:
                        tag = 'LMT'
                    if abs(g - dh) < 1e-6 and x1 <= XB + 1e-6:
                        # dintel de cortina: cajon continuo de columna A a columna B
                        tag = 'DIN'
                        rel = []
                        if abs(x0 - XA) < 1e-6:
                            rel.append('START')
                        if abs(x1 - XB) < 1e-6:
                            rel.append('END')
                    self.mb(tag, a, b, rel=rel, wall='3', lvl=g)
        for x in c['SAG_BACK_X']:
            if x > XB:
                ys = [0.0] + G
                self.nd(x, 0.0, Z3, prio=2)
            else:
                ys = [g for g in G if g >= dh - 1e-6]
            self.chain('CF', [(x, y, Z3) for y in ys], wall='3')
        for x in dx:
            ys = [0.0] + [g for g in G if g <= dh + 1e-6]
            self.nd(x, 0.0, Z3, prio=1)
            keys = [self.nd(x, y, Z3) for y in ys]
            for i, (a, b) in enumerate(zip(keys[:-1], keys[1:])):
                self.mb('PC', a, b, wall='3', rel=(['END'] if i == len(keys) - 2 else []))
        # ---------------- tensores
        t = self.tips
        base = lambda n: self.key(*{'A-1': (XA, 0, Z1), 'C-1': (XC, 0, Z1), 'A-2': (XA, 0, Z2), 'C-2': (XC, 0, Z2),
                                    'A-3': (XA, 0, Z3), 'B-3': (XB, 0, Z3), 'C-3': (XC, 0, Z3)}[n])
        for s in ('A', 'C'):
            self.mb('TM', base(s + '-3'), t[s + '-2'], wall=s)
            self.mb('TM', base(s + '-2'), t[s + '-3'], wall=s)
            low2 = base(s + '-2')
            if s == 'A' and c['ROD_DOOR']:
                # la puerta de emergencia queda junto a la columna A-2: el tensor arranca en
                # el cajon de +3.00 (criterio H5-H6) para no atravesar el vano
                low2 = self.key(XA, c['EDOOR_TOP'], Z2)
                if low2 not in self._nodes:
                    raise ValueError('no existe el nudo de arranque del tensor sobre la puerta')
            self.mb('TM', low2, t[s + '-1'], wall=s, door=(s == 'A' and c['ROD_DOOR']))
            self.mb('TM', base(s + '-1'), t[s + '-2'], wall=s)
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
    ORDER = ['COL', 'VR', 'VT', 'CS', 'CI', 'CSL', 'CIL', 'MON', 'DIA', 'DIAE', 'LC', 'CFC', 'LM', 'LMT', 'DIN', 'DINE',
             'CF', 'PC', 'PE', 'DE', 'TM', 'TMF', 'TC']

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
