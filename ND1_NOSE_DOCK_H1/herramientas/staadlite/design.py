"""Revision AISC 360-16 LRFD imitando lo que hace STAAD.Pro (calibrado contra los
.ANL de los nose docks H5-H6 y H2-H3).  Unidades kg, cm."""
import math
import numpy as np

PHI = 0.9


def _e3(fy, E, klr):
    if klr <= 0:
        return fy
    fe = math.pi**2 * E / klr**2
    return 0.658**(fy / fe) * fy if fy / fe <= 2.25 else 0.877 * fe


def _ae_stiffened(b, t, lam_r, fy, fcr, c1=0.18, c2=1.31):
    """Ancho efectivo E7 (2016)."""
    lam = b / t
    if lam <= lam_r * math.sqrt(fy / fcr):
        return b
    fel = (c2 * lam_r / lam)**2 * fy
    return b * (1 - c1 * math.sqrt(fel / fcr)) * math.sqrt(fel / fcr)


class Cap:
    """Capacidades de diseño (ya con phi) de un miembro."""
    __slots__ = ('Pt', 'Pc', 'Pcx', 'Pcy', 'Mcx', 'Mcx_y', 'Mcy', 'Vcy', 'Vcz', 'kind', 'notes', 'klr', 'compact_h13')


def cap_I(s, fy, E, Lb, ly, lz, rolled, general, cb=1.0):
    """Seccion I (laminada W) o GENERAL tratada como I via D,TD,B,TB."""
    c = Cap()
    c.kind = 'W' if rolled else 'GEN'
    A = s.A
    d, tw, bf, tf = s.d, s.tw, s.bf, s.tf
    Sx, Zx, Sy, Zy, Iy, J, Cw = s.Sz, s.Zz, s.Sy, s.Zy, s.Iy, s.J, s.Cw
    rE = math.sqrt(E / fy)
    if rolled:
        h = d - 2 * s.k
        hF = h
    else:
        h = d - 2 * tf
        hF = h
    ho = d - tf
    rx, ry = s.rz, s.ry
    c.Pt = PHI * fy * A
    # ---- compresion E3 + E7
    def pc(klr):
        fcr = _e3(fy, E, klr)
        Ae = A
        he = _ae_stiffened(h, tw, 1.49 * rE, fy, fcr)
        Ae -= (h - he) * tw
        b = bf / 2
        be = _ae_stiffened(b, tf, 0.56 * rE, fy, fcr, c1=0.22, c2=1.49)
        Ae -= 4 * (b - be) * tf
        return PHI * fcr * Ae
    klx, kly = lz / rx, ly / ry
    c.Pcx = pc(klx)
    c.Pcy = pc(kly)
    c.Pc = min(c.Pcx, c.Pcy)
    c.klr = max(klx, kly)
    # ---- flexion eje mayor
    lw = hF / tw
    lf = bf / (2 * tf)
    lpw, lrw = 3.76 * rE, 5.70 * rE
    lpf, lrf = 0.38 * rE, 1.0 * rE
    Mp = fy * Zx
    Myc = fy * Sx
    kc = min(max(4 / math.sqrt(hF / tw), 0.35), 0.76)
    if lw <= lpw:
        if Cw > 0:
            rts = math.sqrt(math.sqrt(Iy * Cw) / Sx)
        else:
            rts = bf / math.sqrt(12 * (1 + hF * tw / (6 * bf * tf)))
        Lp = 1.76 * ry * rE
        jc = J / (Sx * ho)
        Lr = 1.95 * rts * E / (0.7 * fy) * math.sqrt(jc + math.sqrt(jc**2 + 6.76 * (0.7 * fy / E)**2))
        if Lb <= Lp:
            Mn = Mp
        elif Lb <= Lr:
            Mn = min(Mp, cb * (Mp - (Mp - 0.7 * fy * Sx) * (Lb - Lp) / (Lr - Lp)))
        else:
            Fcr = cb * math.pi**2 * E / (Lb / rts)**2 * math.sqrt(1 + 0.078 * jc * (Lb / rts)**2)
            Mn = min(Mp, Fcr * Sx)
        My_only = Mp
        if lf > lpf:
            if lf <= lrf:
                flb = Mp - (Mp - 0.7 * fy * Sx) * (lf - lpf) / (lrf - lpf)
            else:
                flb = 0.9 * E * kc * Sx / lf**2
            Mn = min(Mn, flb)
            My_only = min(My_only, flb)
    else:
        aw = hF * tw / (bf * tf)
        rt = bf / math.sqrt(12 * (1 + aw / 6))
        Lp = 1.1 * rt * rE
        if lw <= lrw:
            ratio = min(Mp / Myc, 1.6)
            Rpc = min(ratio, ratio - (ratio - 1) * (lw - lpw) / (lrw - lpw))
            FL = 0.7 * fy
            jj = J / (Sx * ho)
            Lr = 1.95 * rt * E / FL * math.sqrt(jj + math.sqrt(jj**2 + 6.76 * (FL / E)**2))
            top = Rpc * Myc
            if Lb <= Lp:
                Mn = top
            elif Lb <= Lr:
                Mn = min(top, cb * (top - (top - FL * Sx) * (Lb - Lp) / (Lr - Lp)))
            else:
                Fcr = cb * math.pi**2 * E / (Lb / rt)**2 * math.sqrt(1 + 0.078 * jj * (Lb / rt)**2)
                Mn = min(Fcr * Sx, top)
            My_only = top
            if lf > lpf:
                if lf <= lrf:
                    flb = top - (top - FL * Sx) * (lf - lpf) / (lrf - lpf)
                else:
                    flb = 0.9 * E * kc * Sx / lf**2
                Mn = min(Mn, flb)
                My_only = min(My_only, flb)
        else:
            aw_ = min(aw, 10)
            Rpg = min(1.0, 1 - aw_ / (1200 + 300 * aw_) * (lw - lrw))
            Lr = math.pi * rt * math.sqrt(E / (0.7 * fy))
            if Lb <= Lp:
                Fcr = fy
            elif Lb <= Lr:
                Fcr = min(fy, cb * (fy - 0.3 * fy * (Lb - Lp) / (Lr - Lp)))
            else:
                Fcr = min(fy, cb * math.pi**2 * E / (Lb / rt)**2)
            Mn = Rpg * Fcr * Sx
            My_only = Rpg * fy * Sx
            if lf > lpf:
                if lf <= lrf:
                    flb = Rpg * Sx * (fy - 0.3 * fy * (lf - lpf) / (lrf - lpf))
                else:
                    flb = Rpg * Sx * 0.9 * E * kc / lf**2
                Mn = min(Mn, flb)
                My_only = min(My_only, flb)
    c.Mcx = PHI * Mn
    c.Mcx_y = PHI * My_only
    # ---- flexion eje menor F6
    Mpy = min(fy * Zy, 1.6 * fy * Sy)
    Mny = Mpy
    if lf > lpf:
        if lf <= lrf:
            Mny = Mpy - (Mpy - 0.7 * fy * Sy) * (lf - lpf) / (lrf - lpf)
        else:
            Mny = 0.69 * E / lf**2 * Sy
    c.Mcy = PHI * Mny
    # ---- cortante
    hv = h
    lam = hv / tw
    if rolled:
        Aw = d * tw
    else:
        Aw = s.Ay
    if lam <= 2.24 * rE and (rolled or True):
        c.Vcy = 1.0 * 0.6 * fy * Aw
    else:
        kv = 5.34
        lim = 1.10 * math.sqrt(kv * E / fy)
        cv1 = 1.0 if lam <= lim else lim / lam
        c.Vcy = PHI * 0.6 * fy * Aw * cv1
    # eje menor (G6): kv = 1.2
    if rolled:
        Awz = 2 * bf * tf
    else:
        Awz = s.Az
    lamz = bf / (2 * tf)
    kv = 1.2
    lim = 1.10 * math.sqrt(kv * E / fy)
    if lamz <= lim:
        cv2 = 1.0
    elif lamz <= 1.37 * math.sqrt(kv * E / fy):
        cv2 = lim / lamz
    else:
        cv2 = 1.51 * kv * E / (lamz**2 * fy)
    c.Vcz = PHI * 0.6 * fy * Awz * cv2
    c.compact_h13 = rolled and lw <= lpw and lf <= lpf
    c.notes = ''
    return c


def cap_box(s, fy, E, Lb, ly, lz):
    """HSS rectangular / cuadrado (tabla AISC, TUBE TH WT DT o tabla de usuario TUBE)."""
    c = Cap()
    c.kind = 'HSS'
    A = s.A
    H, B, t = s.d, s.bf, s.t
    rE = math.sqrt(E / fy)
    c.Pt = PHI * fy * A
    h = H - 3 * t
    b = B - 3 * t
    def pc(klr):
        fcr = _e3(fy, E, klr)
        Ae = A
        for w in (h, h, b, b):
            we = _ae_stiffened(w, t, 1.40 * rE, fy, fcr, c1=0.20, c2=1.38)
            Ae -= (w - we) * t
        return PHI * fcr * Ae
    klx, kly = lz / s.rz, ly / s.ry
    c.Pcx = pc(klx)
    c.Pcy = pc(kly)
    c.Pc = min(c.Pcx, c.Pcy)
    c.klr = max(klx, kly)
    def mn(Z, S, bflange, hweb, I_):
        Mp = fy * Z
        M = Mp
        lf = bflange / t
        lpf, lrf = 1.12 * rE, 1.40 * rE
        if lf > lpf:
            if lf <= lrf:
                M = min(M, Mp - (Mp - fy * S) * (3.57 * lf / rE - 4.0))
            else:
                be = min(bflange, 1.92 * t * rE * (1 - 0.38 / lf * rE))
                # modulo efectivo: se descuenta el ancho no efectivo en ambos patines
                depth = 2 * S and (2 * I_ / S)
                rem = max((bflange + t) - be, 0.0)
                yy = depth / 2 - t / 2
                Ie = I_ - 2 * rem * t * yy**2
                M = min(M, fy * Ie / (depth / 2))
        lw = hweb / t
        lpw, lrw = 2.42 * rE, 5.70 * rE
        if lw > lpw:
            M = min(M, Mp - (Mp - fy * S) * (0.305 * lw / rE - 0.738))
        return M
    c.Mcx = PHI * mn(s.Zz, s.Sz, b, h, s.Iz)
    c.Mcx_y = c.Mcx
    c.Mcy = PHI * mn(s.Zy, s.Sy, h, b, s.Iy)
    def vn(hh):
        lam = hh / t
        kv = 5.0
        lim = 1.10 * math.sqrt(kv * E / fy)
        if lam <= lim:
            cv = 1.0
        elif lam <= 1.37 * math.sqrt(kv * E / fy):
            cv = lim / lam
        else:
            cv = 1.51 * kv * E / (lam**2 * fy)
        return PHI * 0.6 * fy * 2 * hh * t * cv
    c.Vcy = vn(h)
    c.Vcz = vn(b)
    c.compact_h13 = False
    c.notes = ''
    return c


def cap_pipe(s, fy, E, Lb, ly, lz):
    c = Cap()
    c.kind = 'PIPE'
    A = s.A
    D, t = s.d, s.t
    c.Pt = PHI * fy * A
    def pc(klr):
        fcr = _e3(fy, E, klr)
        Ae = A
        dt = D / t
        if dt > 0.11 * E / fy:
            Ae = A * (0.038 * E / (fy * dt) + 2.0 / 3.0)
        return PHI * fcr * Ae
    klx, kly = lz / s.rz, ly / s.ry
    c.Pcx = pc(klx)
    c.Pcy = pc(kly)
    c.Pc = min(c.Pcx, c.Pcy)
    c.klr = max(klx, kly)
    dt = D / t
    Mp = fy * s.Zz
    M = Mp
    if dt > 0.07 * E / fy:
        if dt <= 0.31 * E / fy:
            M = (0.021 * E / dt + fy) * s.Sz
        else:
            M = 0.33 * E / dt * s.Sz
    c.Mcx = c.Mcx_y = c.Mcy = PHI * M
    fcrv = 0.6 * fy
    c.Vcy = c.Vcz = PHI * fcrv * A / 2
    c.compact_h13 = False
    c.notes = ''
    return c


def cap_rod(s, fy, E):
    c = Cap()
    c.kind = 'ROD'
    c.Pt = PHI * fy * s.A
    c.Pc = c.Pcx = c.Pcy = 1e-9
    c.Mcx = c.Mcx_y = c.Mcy = PHI * fy * s.Zz
    c.Vcy = c.Vcz = PHI * 0.6 * fy * s.A * 0.75
    c.klr = 0
    c.compact_h13 = False
    c.notes = ''
    return c


def capacities(run, e):
    m = run.m
    el = run.st.elems[e]
    s = el.sec
    P = m.params
    fy = P.get('FYLD', {}).get(e, el.fy)
    E = el.E
    L = el.L
    ky = P.get('KY', {}).get(e, 1.0)
    kz = P.get('KZ', {}).get(e, 1.0)
    ly = ky * P.get('LY', {}).get(e, L)
    lz = kz * P.get('LZ', {}).get(e, L)
    unl = P.get('UNL', {}).get(e, L)
    lb = max(P.get('UNT', {}).get(e, unl), P.get('UNB', {}).get(e, unl))
    cb = P.get('CB', {}).get(e, 1.0) or 1.0
    if s.shape == 'W':
        return cap_I(s, fy, E, lb, ly, lz, rolled=True, general=False, cb=cb)
    if s.shape == 'GEN':
        return cap_I(s, fy, E, lb, ly, lz, rolled=False, general=True, cb=cb)
    if s.shape == 'HSSR':
        return cap_box(s, fy, E, lb, ly, lz)
    if s.shape == 'PIPE':
        return cap_pipe(s, fy, E, lb, ly, lz)
    if s.shape == 'ROD':
        return cap_rod(s, fy, E)
    raise ValueError(s.shape)


def check_member(run, e, lcs, cap=None, nsec=13):
    """Devuelve dict con relacion maxima, combinacion, posicion y clausula."""
    c = cap or capacities(run, e)
    el = run.st.elems[e]
    best = dict(ratio=-1.0, lc=None, loc=0.0, ref='', forces=None)
    for lc in lcs:
        sf = run.section_forces(lc, e, nsec)
        x = sf[:, 0]
        P = sf[:, 1]
        Vy = np.abs(sf[:, 2])
        Vz = np.abs(sf[:, 3])
        My = np.abs(sf[:, 5])
        Mz = np.abs(sf[:, 6])
        tens = P >= 0
        Pa = np.abs(P)
        pr_t = Pa / c.Pt
        pr_c = Pa / c.Pc
        pr = np.where(tens, pr_t, pr_c)
        mx = Mz / c.Mcx
        my = My / c.Mcy
        inter = np.where(pr >= 0.2, pr + 8.0 / 9.0 * (mx + my), pr / 2 + mx + my)
        ref_i = np.where(pr >= 0.2, 0, 1)
        if c.compact_h13:
            # H1.3: pandeo en el plano y fuera del plano por separado (solo My pequeño)
            use = (my < 0.05) & (~tens) & (Mz > 0)
            prx = Pa / c.Pcx
            mxy = Mz / c.Mcx_y
            inpl = np.where(prx >= 0.2, prx + 8.0 / 9.0 * mxy, prx / 2 + mxy)
            pry = Pa / c.Pcy
            outp = pry * (1.5 - 0.5 * pry) + mx**2
            h13 = np.maximum(inpl, outp)
            inter = np.where(use, h13, inter)
            ref_i = np.where(use, np.where(inpl >= outp, 2, 3), ref_i)
        vy = Vy / c.Vcy
        vz = Vz / c.Vcz
        allr = np.vstack([inter, pr, mx, my, vy, vz])
        k = np.unravel_index(np.argmax(allr), allr.shape)
        val = allr[k]
        if val > best['ratio']:
            i = k[1]
            names = {0: None, 1: 'Cl.E3' if not tens[i] else 'Cl.D2', 2: 'Cl.F', 3: 'Cl.F(y)', 4: 'Cl.G1', 5: 'Cl.G(z)'}
            if k[0] == 0:
                ref = ['Eq.H1-1a', 'Eq.H1-1b', 'Eq.H1-3a', 'Eq.H1-3b'][int(ref_i[i])]
            else:
                ref = names[k[0]]
            best = dict(ratio=float(val), lc=lc, loc=float(x[i]), ref=ref,
                        forces=dict(P=float(P[i]), Vy=float(sf[i, 2]), Vz=float(sf[i, 3]), My=float(sf[i, 5]), Mz=float(sf[i, 6])),
                        parts=dict(pr=float(pr[i]), mx=float(mx[i]), my=float(my[i]), vy=float(vy[i]), vz=float(vz[i])))
    best['cap'] = c
    best['slender'] = c.klr
    return best


def check_all(run, members, lcs):
    out = {}
    for e in members:
        if e not in run.st.elems:
            continue
        el = run.st.elems[e]
        if el.sec.shape == 'ROD':
            continue
        out[e] = check_member(run, e, lcs)
    return out
