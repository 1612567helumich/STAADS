"""Evaluacion completa de una variante del ND1 con el emulador validado."""
import sys, os, json, time, math, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nd1_std
from staadlite import parser, design
from staadlite.run import Run

DESIGN_LCS = list(range(33, 67))
SEIS_SERV = list(range(16, 24))
WIND_SERV = list(range(24, 32))


def build(cfg, out_std, comment=None):
    cfg = dict(cfg)
    cfg.setdefault('USER_TABLES', os.path.join(HERE, 'user_tables.txt'))
    g, txt = nd1_std.make(cfg, comment)
    with open(out_std, 'w', encoding='latin-1', newline='\r\n') as f:     # CRLF como los STD de STAAD
        f.write(txt)
    m = parser.read(out_std)
    return g, m


def seismic_factors(g, R):
    """Factores de escala del cortante basal segun la hoja (NTDS 5.4.1)."""
    c = g.c
    mr = R.modal
    out = {}
    hn = 0.5 * (g.yroof(c['Z3']) + g.yroof(c['Z1'])) / 100.0
    Ta = 0.085 * hn ** 0.75
    Ta = min(max(Ta, c['TO']), 6 * c['TO'])
    cs0 = c['A'] * c['I'] * c['CO'] / c['R']
    csA = cs0 * (c['TO'] / Ta) ** (2.0 / 3.0)
    for d, lc in (('X', 4), ('Z', 5)):
        part = mr.part[d]
        dom = int(np.argmax(part))
        Tf = float(mr.T[dom])
        Tfc = min(max(Tf, c['TO']), 6 * c['TO'])
        csF = cs0 * (c['TO'] / Tfc) ** (2.0 / 3.0)
        W = mr.wtot[d]
        # cortante modal con factor 1.0
        sp = R.m.loads[lc].spectrum
        f_now = abs(sp['dir'][d])
        vm = R.base_shear(lc)[d][1] / f_now
        v1 = 0.9 * csF * W
        v2 = 0.8 * csA * W
        vmin = max(v1, v2)
        out[d] = dict(dom=dom + 1, T=Tf, part=float(part[dom]), sum=float(part.sum()), W=W, Vmod=vm, Vest_T=csF * W, Vest_A=csA * W,
                      Vmin=vmin, factor=max(vmin / vm, 1.0), csA=csA, csF=csF, Ta=Ta, hn=hn, f_now=f_now)
    return out


SHEET_MODES = 43      # renglones de la tabla modal de la hoja SISMO_VIENTO


def _xl_round(x, nd):
    """ROUND de Excel (mitad hacia afuera) sobre el valor decimal impreso."""
    from decimal import Decimal, ROUND_HALF_UP
    q = Decimal(1).scaleb(-nd)
    return float(Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP))


def csm_sheet(c, T):
    """Ordenada del espectro de la hoja (columna I de la tabla Tm-Csm)."""
    base = c['I'] * c['A'] / c['R']
    if T < c['TO'] / 3:
        return base * (1 + 3 * (c['CO'] - 1) * T / c['TO'])
    if T <= c['TO']:
        return base * c['CO']
    return base * c['CO'] * (c['TO'] / T) ** (2.0 / 3.0)


def sheet_factors(g, R, nrows=SHEET_MODES):
    """Factores de escala del espectro calculados igual que la hoja de calculo
    'CARGAS Y SISMO F1' (tabla de los primeros 43 modos con los valores como los
    imprime STAAD: f con 3 decimales, T con 5 y participaciones con 2)."""
    c = g.c
    mr = R.modal
    n = min(nrows, len(mr.T))
    W = round(float(mr.wtot['X']), 2)
    rows = []
    for i in range(n):
        T = round(float(mr.T[i]), 5)
        rows.append(dict(mode=i + 1, f=round(float(mr.freq[i]), 3), T=T,
                         px=round(float(mr.part['X'][i]), 2), pz=round(float(mr.part['Z'][i]), 2),
                         csm=csm_sheet(c, _xl_round(T, 2))))
    hn = 0.5 * (g.yroof(c['Z3']) + g.yroof(c['Z1'])) / 100.0
    ta = 0.085 * hn ** 0.75
    Ta = c['TO'] if ta <= c['TO'] else (ta if ta <= 6 * c['TO'] else 6 * c['TO'])
    cs_a = c['A'] * c['I'] * c['CO'] / c['R'] * (c['TO'] / Ta) ** (2.0 / 3.0)
    out = dict(rows=rows, W=W, hn=hn, Ta=Ta, cs_a=cs_a)
    for d, key in (('X', 'px'), ('Z', 'pz')):
        vb = [r['csm'] * W * r[key] / 100.0 for r in rows]
        vmod = math.sqrt(sum(v * v for v in vb))
        pmax = max(r[key] for r in rows)
        dom = next(r for r in rows if r[key] == pmax)
        vest1 = W * dom['csm']
        vest2 = W * cs_a
        vmin = max(0.8 * vest2, 0.9 * vest1)
        out[d] = dict(dom=dom['mode'], T=dom['T'], part=pmax, sum=sum(r[key] for r in rows), Vmod=vmod, Vest1=vest1,
                      Vest2=vest2, Vmin=vmin, factor=max(vmin / vmod, 1.0))
    return out


def evaluate(g, m, verbose=True, R=None, tc_state='last'):
    c = g.c
    t0 = time.time()
    if R is None:
        R = Run(m, tc_state=tc_state)
    st = R.st
    rep = {}
    P = print if verbose else (lambda *a, **k: None)
    P('--- modelo: %d nudos, %d miembros, %d apoyos   (corrida %.1f s)' % (len(m.nodes), len(m.members), len(m.supports), time.time() - t0))
    # nudos sobre el interior de una barra sin estar conectados (error de modelado)
    bad = []
    ids = sorted(m.nodes); P3 = np.array([m.nodes[n] for n in ids])
    for e, (a, b) in m.members.items():
        pa = np.array(m.nodes[a]); pb = np.array(m.nodes[b]); d = pb - pa; L2 = d @ d
        t = ((P3 - pa) @ d) / L2
        proj = pa + np.outer(t, d)
        dist = np.linalg.norm(P3 - proj, axis=1)
        hit = np.where((t > 1e-4) & (t < 1 - 1e-4) & (dist < 0.05))[0]
        for i in hit:
            bad.append((ids[i], e))
    P('  nudos sobre barras sin conectar: %d %s' % (len(bad), bad[:10]))
    Ls = sorted((math.dist(m.nodes[a], m.nodes[b]), e) for e, (a, b) in m.members.items())
    P('  barras mas cortas: %s' % [(round(l, 1), e) for l, e in Ls[:5]])
    rep['bad_nodes'] = bad
    # ---------------- tableros ONEWAY
    exp_area = {'_CUBIERTA': 15 * 16 * math.sqrt(1 + c['SLOPE']**2)}
    for grp, info in getattr(st, '_ow_info', {}).items():
        cnt = collections.Counter(i[2] for i in info)
        P('  ONEWAY %-10s tableros=%3d %s area=%.2f m2' % (grp, len(info), dict(cnt), sum(i[1] for i in info) / 1e4))
    # ---------------- sumas de reacciones
    for k in sorted(R.reac):
        if k in R.spec_cases:
            continue
        tot = sum(R.reac[k].values())
        P('  LC%2d %-22s it=%d inact=%2d  sumR FX=%9.1f FY=%9.1f FZ=%9.1f' % (k, m.loads[k].title[:22], R.iters[k], len(R.inactive[k]), tot[0], tot[1], tot[2]))
    # ---------------- modal
    mr = R.modal
    P('  estado T/C para modos (ultimo caso): inactivos =', sorted(R.tc_modal))
    P('  modo   T(s)    %X     %Z   | acum X  acum Z')
    cx = np.cumsum(mr.part['X']); cz = np.cumsum(mr.part['Z'])
    for i in range(min(12, len(mr.T))):
        P('  %3d  %.4f  %6.2f %6.2f | %6.2f %6.2f' % (i + 1, mr.T[i], mr.part['X'][i], mr.part['Z'][i], cx[i], cz[i]))
    P('  suma con %d modos: X=%.2f%%  Z=%.2f%%   peso sismico X=%.1f kg' % (len(mr.T), cx[-1], cz[-1], mr.wtot['X']))
    n90x = int(np.argmax(cx >= 90) + 1) if cx[-1] >= 90 else None
    n90z = int(np.argmax(cz >= 90) + 1) if cz[-1] >= 90 else None
    P('  modos para 90%%: X=%s Z=%s' % (n90x, n90z))
    sf = seismic_factors(g, R)
    sh = sheet_factors(g, R)
    rep['sheet'] = sh
    for d in 'XZ':
        sf[d]['factor_80modos'] = sf[d]['factor']
        sf[d]['factor'] = sh[d]['factor']
        sf[d]['dom'] = sh[d]['dom']
    for d in 'XZ':
        P('  hoja (43 modos): sismo %s modo %d T=%.5f part=%.2f%% suma=%.2f%% Vmod=%.1f 0.9Vest1=%.1f 0.8Vest2=%.1f -> factor=%.4f' % (
            d, sh[d]['dom'], sh[d]['T'], sh[d]['part'], sh[d]['sum'], sh[d]['Vmod'], 0.9 * sh[d]['Vest1'], 0.8 * sh[d]['Vest2'], sh[d]['factor']))
    for d in 'XZ':
        s = sf[d]
        P('  sismo %s (80 modos, T exacto): modo dominante %d T=%.4f (%.1f%%), W=%.0f, Vmod(f=1)=%.1f, 0.9Vest(T)=%.1f, 0.8Vest(Ta)=%.1f -> factor=%.4f | hoja=%.4f (en archivo %.4f)' % (
            d, s['dom'], s['T'], s['part'], s['W'], s['Vmod'], 0.9 * s['Vest_T'], 0.8 * s['Vest_A'], s['factor_80modos'], s['factor'], s['f_now']))
    rep['sf'] = sf
    rep['part'] = (float(cx[-1]), float(cz[-1]))
    # ---------------- derivas
    tips = g.tipnodes
    cd = c['CD']
    P('  DERIVAS SISMO (Cd*d/H, limite 0.020)  y  VIENTO (d/H, limite 0.005)')
    worst_s = worst_w = 0.0
    for name, n in tips.items():
        H = m.nodes[n][1]
        ds = [0, 0]; dw = [0, 0]
        for lc in SEIS_SERV:
            u = R.node_disp(lc, n)
            ds[0] = max(ds[0], abs(u[0])); ds[1] = max(ds[1], abs(u[2]))
        for lc in WIND_SERV:
            u = R.node_disp(lc, n)
            dw[0] = max(dw[0], abs(u[0])); dw[1] = max(dw[1], abs(u[2]))
        P('    %-4s n%-4d H=%7.1f  sismo: dx=%.3f dz=%.3f -> %.4f / %.4f   viento: dx=%.3f dz=%.3f -> %.4f / %.4f' % (
            name, n, H, ds[0], ds[1], cd * ds[0] / H, cd * ds[1] / H, dw[0], dw[1], dw[0] / H, dw[1] / H))
        worst_s = max(worst_s, cd * ds[0] / H, cd * ds[1] / H)
        worst_w = max(worst_w, dw[0] / H, dw[1] / H)
    for name, key in g.center.items():
        n = g.nid[key]
        H = m.nodes[n][1]
        ds = [0, 0]; dw = [0, 0]
        for lc in SEIS_SERV:
            u = R.node_disp(lc, n); ds[0] = max(ds[0], abs(u[0])); ds[1] = max(ds[1], abs(u[2]))
        for lc in WIND_SERV:
            u = R.node_disp(lc, n); dw[0] = max(dw[0], abs(u[0])); dw[1] = max(dw[1], abs(u[2]))
        P('    centro %s n%-4d H=%7.1f  sismo: %.4f / %.4f   viento: %.4f / %.4f' % (name, n, H, cd * ds[0] / H, cd * ds[1] / H, dw[0] / H, dw[1] / H))
    rep['drift_s'] = worst_s
    rep['drift_w'] = worst_w
    # ---------------- diseño
    res = {}
    for e in m.members:
        if st.elems[e].sec.shape == 'ROD':
            continue
        res[e] = design.check_member(R, e, DESIGN_LCS)
    rep['design'] = res
    bytag = collections.defaultdict(list)
    for e, r in res.items():
        bytag[g.minfo[e]['tag']].append((r['ratio'], e, r))
    P('  DISENO (combinaciones 33-66)')
    P('    %-5s %-14s %4s %7s %7s  %s' % ('grupo', 'perfil', 'n', 'max', 'media', 'miembro critico (comb, ref, x) y esbeltez max'))
    fails = []
    for tag in g.ORDER:
        if tag not in bytag:
            continue
        lst = sorted(bytag[tag], key=lambda t: -t[0])
        rmax, e, r = lst[0]
        sec = st.elems[e].sec.name
        klr = max(t[2]['slender'] for t in lst)
        P('    %-5s %-14s %4d %7.3f %7.3f  m%d (lc%d, %s, x=%.0f)  KL/r max=%.0f' % (tag, sec, len(lst), rmax, np.mean([t[0] for t in lst]), e, r['lc'], r['ref'], r['loc'], klr))
        fails += [(t[1], t[0]) for t in lst if t[0] > 1.0]
    rep['maxratio'] = {tag: max(t[0] for t in lst) for tag, lst in bytag.items()}
    rep['fails'] = fails
    if fails:
        P('    *** NO PASAN: %d miembros: %s' % (len(fails), fails[:12]))
    # ---------------- tensores
    P('  TENSORES (tension maxima en combinaciones 33-66 y capacidad 0.9FyA con Fy=2530)')
    for tag in ('TM', 'TMF', 'TC'):
        if not g.bytag.get(tag):
            continue
        tmax = 0; emax = None; lcmax = None
        for e in g.bytag[tag]:
            for lc in DESIGN_LCS:
                T = R.section_forces(lc, e, 2)[0, 1]
                if T > tmax:
                    tmax, emax, lcmax = T, e, lc
        A = st.elems[g.bytag[tag][0]].sec.A
        cap = 0.9 * 2530 * A
        P('    %s  d=%.4f cm  A=%.3f  Tmax=%.0f kg (m%s lc%s)  cap=%.0f  rel=%.3f' % (tag, st.elems[g.bytag[tag][0]].sec.d, A, tmax, emax, lcmax, cap, tmax / cap))
        rep['rod_' + tag] = tmax / cap
    # ---------------- flechas
    P('  FLECHAS (servicio)')
    def defl(tag_members, lc):
        worst = (0, None)
        for e in tag_members:
            el = st.elems[e]
            u = R.disp(lc)
            i1, i2 = st.nidx[el.n1], st.nidx[el.n2]
            worst = max(worst, (abs(u[6 * i1 + 1]), el.n1), (abs(u[6 * i2 + 1]), el.n2))
        return worst
    for tag, span in (('LC', 750.0), ('CS', 1500.0), ('CSL', 800.0), ('VR', 800.0)):
        d, n = defl(g.bytag[tag], 32)
        P('    %-4s CM+CV: dy max=%.2f cm en nudo %s  (L/%.0f respecto a claro %.0f)' % (tag, d, n, span / d if d else 0, span))
    # ---------------- peso
    wt = collections.defaultdict(float)
    ln = collections.defaultdict(float)
    for e, el in st.elems.items():
        wt[el.sec.name] += el.sec.A * el.rho * el.L
        ln[el.sec.name] += el.L
    tot = sum(wt.values())
    P('  PESO: total %.0f kg  (%.1f kg/m2 sobre 240 m2)' % (tot, tot / 240.0))
    for k in sorted(wt, key=lambda k: -wt[k]):
        P('    %-16s %9.1f cm %9.1f kg' % (k, ln[k], wt[k]))
    rep['weight'] = tot
    rep['wt'] = dict(wt)
    rep['R'] = R
    return rep


if __name__ == '__main__':
    out = sys.argv[1]
    cfg = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    g, m = build(cfg, out)
    evaluate(g, m)
