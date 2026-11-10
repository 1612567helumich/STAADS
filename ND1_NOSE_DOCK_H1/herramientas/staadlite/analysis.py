"""Analisis matricial 3D (rigidez directa) que imita lo esencial de STAAD:
barras con liberaciones, MEMBER TRUSS, MEMBER TENSION (iterativo), cargas
SELFWEIGHT / MEMBER LOAD UNI / JOINT LOAD / ONEWAY LOAD, modos con masa
concentrada y espectro de respuesta (SRSS/CQC) con signo del modo dominante."""
import math
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from scipy.linalg import eigh

from .sections import section_for

G_ACC = 981.0  # cm/s2 (lo que usa el modelo: SCALE 981)


def local_axes(p1, p2, beta_deg):
    x = np.array(p2, float) - np.array(p1, float)
    L = np.linalg.norm(x)
    x = x / L
    if abs(x[0]) < 1e-9 and abs(x[2]) < 1e-9:      # vertical
        z = np.array([0.0, 0.0, 1.0])
        y = np.cross(z, x)
    else:
        z = np.cross(x, np.array([0.0, 1.0, 0.0]))
        z /= np.linalg.norm(z)
        y = np.cross(z, x)
    if beta_deg:
        b = math.radians(beta_deg)
        y, z = y * math.cos(b) + z * math.sin(b), -y * math.sin(b) + z * math.cos(b)
    return L, np.array([x, y, z])


def k_local(E, G, A, Iy, Iz, J, L, Ay=0.0, Az=0.0, shear=True):
    k = np.zeros((12, 12))
    ea = E * A / L
    gj = G * J / L
    k[0, 0] = k[6, 6] = ea
    k[0, 6] = k[6, 0] = -ea
    k[3, 3] = k[9, 9] = gj
    k[3, 9] = k[9, 3] = -gj
    fy = 12 * E * Iz / (G * Ay * L * L) if (shear and Ay > 0) else 0.0
    fz = 12 * E * Iy / (G * Az * L * L) if (shear and Az > 0) else 0.0
    # flexion alrededor de z (v, thz): dofs 1,5,7,11
    c = E * Iz / (L**3 * (1 + fy))
    a = np.array([[12, 6 * L, -12, 6 * L],
                  [6 * L, (4 + fy) * L * L, -6 * L, (2 - fy) * L * L],
                  [-12, -6 * L, 12, -6 * L],
                  [6 * L, (2 - fy) * L * L, -6 * L, (4 + fy) * L * L]]) * c
    idx = [1, 5, 7, 11]
    for i in range(4):
        for j in range(4):
            k[idx[i], idx[j]] += a[i, j]
    # flexion alrededor de y (w, thy): dofs 2,4,8,10
    c = E * Iy / (L**3 * (1 + fz))
    a = np.array([[12, -6 * L, -12, -6 * L],
                  [-6 * L, (4 + fz) * L * L, 6 * L, (2 - fz) * L * L],
                  [-12, 6 * L, 12, 6 * L],
                  [-6 * L, (2 - fz) * L * L, 6 * L, (4 + fz) * L * L]]) * c
    idx = [2, 4, 8, 10]
    for i in range(4):
        for j in range(4):
            k[idx[i], idx[j]] += a[i, j]
    return k


def fef_uniform(w, L):
    """Fuerzas de empotramiento (acciones del nudo sobre la barra) para carga
    uniforme local w=(wx,wy,wz) en toda la longitud."""
    wx, wy, wz = w
    f = np.zeros(12)
    f[0] = f[6] = -wx * L / 2
    f[1] = f[7] = -wy * L / 2
    f[5] = -wy * L * L / 12
    f[11] = wy * L * L / 12
    f[2] = f[8] = -wz * L / 2
    f[4] = wz * L * L / 12
    f[10] = -wz * L * L / 12
    return f


class Element:
    __slots__ = ('id', 'n1', 'n2', 'L', 'R', 'sec', 'E', 'G', 'rho', 'kind', 'rel', 'k', 'T', 'dofs', 'Kc', 'Tc',
                 'kfull', 'ret', 'con', 'fy')


class Structure:
    def __init__(self, model, shear=True):
        self.m = model
        self.shear = shear
        self.node_ids = sorted(model.nodes)
        self.nidx = {n: i for i, n in enumerate(self.node_ids)}
        self.ndof = 6 * len(self.node_ids)
        self.xyz = np.array([model.nodes[n] for n in self.node_ids])
        self.elems = {}
        for e, (a, b) in model.members.items():
            if e not in model.prop:
                continue
            el = Element()
            el.id = e
            el.n1, el.n2 = a, b
            el.L, el.R = local_axes(model.nodes[a], model.nodes[b], model.beta.get(e, 0.0))
            el.sec = section_for(model, e)
            mat = model.materials.get(model.matname.get(e, 'STEEL'), {})
            el.E = mat.get('E', 2.09042e6)
            nu = mat.get('POISSON', 0.3)
            el.G = mat.get('G', el.E / (2 * (1 + nu)))
            el.rho = mat.get('DENSITY', 0.00783341)
            el.fy = mat.get('FY', 2531.0)
            el.kind = 'truss' if (e in model.truss or e in model.tension) else 'beam'
            el.rel = model.release.get(e)
            T = np.zeros((12, 12))
            for i in range(4):
                T[3 * i:3 * i + 3, 3 * i:3 * i + 3] = el.R
            el.T = T
            i1, i2 = self.nidx[a], self.nidx[b]
            el.dofs = np.array(list(range(6 * i1, 6 * i1 + 6)) + list(range(6 * i2, 6 * i2 + 6)))
            s = el.sec
            if el.kind == 'truss':
                k = np.zeros((12, 12))
                ea = el.E * s.A / el.L
                k[0, 0] = k[6, 6] = ea
                k[0, 6] = k[6, 0] = -ea
                el.kfull = k
                el.ret = [0, 6]
                el.con = [i for i in range(12) if i not in (0, 6)]
                el.k = k
            else:
                kf = k_local(el.E, el.G, s.A, s.Iy, s.Iz, s.J, el.L, s.Ay, s.Az, shear)
                el.kfull = kf
                con = []
                if el.rel:
                    con = sorted(list(el.rel['START']) + [6 + d for d in el.rel['END']])
                el.con = con
                el.ret = [i for i in range(12) if i not in con]
                if con:
                    krr = kf[np.ix_(el.ret, el.ret)]
                    krc = kf[np.ix_(el.ret, con)]
                    kcc = kf[np.ix_(con, con)]
                    kc = krr - krc @ np.linalg.solve(kcc, krc.T)
                    k = np.zeros((12, 12))
                    k[np.ix_(el.ret, el.ret)] = kc
                    el.k = k
                else:
                    el.k = kf
            self.elems[e] = el
        # restricciones
        self.fixed = np.zeros(self.ndof, bool)
        for n, r in model.supports.items():
            i = self.nidx[n]
            for d in range(6):
                if r[d]:
                    self.fixed[6 * i + d] = True
        self._lu_cache = {}
        self.zero_dofs = None

    # ------------------------------------------------------------------ rigidez
    def assemble(self, inactive=frozenset()):
        rows, cols, vals = [], [], []
        for e, el in self.elems.items():
            if e in inactive:
                continue
            kg = el.T.T @ el.k @ el.T
            d = el.dofs
            rr = np.repeat(d, 12)
            cc = np.tile(d, 12)
            rows.append(rr)
            cols.append(cc)
            vals.append(kg.ravel())
        K = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(self.ndof, self.ndof)).tocsc()
        return K

    def factor(self, inactive=frozenset()):
        key = frozenset(inactive)
        if key in self._lu_cache:
            return self._lu_cache[key]
        K = self.assemble(inactive)
        diag = K.diagonal()
        scale = np.abs(diag).max()
        zero = (np.abs(diag) < 1e-9 * scale) & (~self.fixed)
        free = ~(self.fixed | zero)
        idx = np.where(free)[0]
        Kff = K[idx][:, idx].tocsc()
        lu = splu(Kff)
        res = (K, idx, lu, zero)
        if len(self._lu_cache) > 40:
            self._lu_cache.clear()
        self._lu_cache[key] = res
        return res

    # ------------------------------------------------------------------ cargas
    def member_w_global(self, lc):
        """dict e -> vector global (wX,wY,wZ) kg/cm de carga uniforme equivalente del caso."""
        m = self.m
        w = {}

        def add(e, v):
            if e in self.elems:
                w[e] = w.get(e, np.zeros(3)) + np.array(v, float)
        for (d, f) in lc.selfweight:
            ax = 'XYZ'.index(d)
            for e, el in self.elems.items():
                v = np.zeros(3)
                v[ax] = f * el.sec.A * el.rho
                add(e, v)
        for (ids, kind, d, vals) in lc.member:
            if kind != 'UNI':
                raise ValueError('solo UNI soportado')
            for e in ids:
                if e not in self.elems:
                    continue
                el = self.elems[e]
                if d in ('GX', 'GY', 'GZ'):
                    v = np.zeros(3)
                    v['XYZ'.index(d[1])] = vals[0]
                elif d in ('X', 'Y', 'Z'):
                    v = el.R['XYZ'.index(d)] * vals[0]
                else:
                    raise ValueError('direccion ' + d)
                add(e, v)
        for ow in lc.oneway:
            for e, v in self.oneway_loads(ow).items():
                add(e, v)
        return w

    def oneway_loads(self, ow):
        from .oneway import distribute
        key = (ow['group'], ow['towards'])
        if not hasattr(self, '_ow_cache'):
            self._ow_cache = {}
        if key not in self._ow_cache:
            self._ow_cache[key] = distribute(self, ow['group'], ow['towards'])
        unit = self._ow_cache[key]          # e -> ancho tributario (cm2/cm)
        ax = 'XYZ'.index(ow['dir'][1])
        out = {}
        for e, wd in unit.items():
            v = np.zeros(3)
            v[ax] = ow['p'] * wd
            out[e] = v
        return out

    def load_vector(self, lc):
        F = np.zeros(self.ndof)
        w = self.member_w_global(lc)
        fefs = {}
        for e, wg in w.items():
            el = self.elems[e]
            wl = el.R @ wg
            if el.kind == 'truss':
                # STAAD reparte la carga de barras tipo armadura a los nudos
                f = np.zeros(12)
                f[0:3] = -wl * el.L / 2
                f[6:9] = -wl * el.L / 2
                fe = f
            else:
                f = fef_uniform(wl, el.L)
                if el.con:
                    kf = el.kfull
                    krc = kf[np.ix_(el.ret, el.con)]
                    kcc = kf[np.ix_(el.con, el.con)]
                    fr = f[el.ret] - krc @ np.linalg.solve(kcc, f[el.con])
                    fe = np.zeros(12)
                    fe[el.ret] = fr
                else:
                    fe = f
            fefs[e] = (fe, wl)
            F[el.dofs] -= el.T.T @ fe
        for (ids, d) in lc.joint:
            for n in ids:
                i = self.nidx[n]
                for k, v in d.items():
                    F[6 * i + ['FX', 'FY', 'FZ', 'MX', 'MY', 'MZ'].index(k)] += v
        return F, fefs

    # ------------------------------------------------------------------ estatica
    def solve_static(self, lc, tension_iter=True, maxit=20, start_inactive=None, reactivate=True):
        F, fefs = self.load_vector(lc)
        inactive = set(start_inactive) if start_inactive else set()
        tens = [e for e in self.m.tension if e in self.elems]
        it = 0
        while True:
            K, idx, lu, zero = self.factor(frozenset(inactive))
            u = np.zeros(self.ndof)
            u[idx] = lu.solve(F[idx])
            if not tension_iter or not tens:
                break
            new_inactive = set()
            for e in tens:
                el = self.elems[e]
                ul = el.T @ u[el.dofs]
                axial = el.E * el.sec.A / el.L * (ul[6] - ul[0])   # + tension (aunque este inactivo, por deformacion)
                if axial < -1e-9:
                    new_inactive.add(e)
                elif (not reactivate) and e in inactive:
                    new_inactive.add(e)
                elif e in inactive and abs(axial) <= 1e-9:
                    new_inactive.add(e)          # sin deformacion: se queda como estaba
            it += 1
            if new_inactive == inactive or it >= maxit:
                break
            inactive = new_inactive
        res = StaticResult(self, lc.num, u, fefs, frozenset(inactive), F, K)
        res.iters = it
        return res

    def end_forces(self, u, fefs=None, inactive=frozenset()):
        out = {}
        for e, el in self.elems.items():
            if e in inactive:
                out[e] = np.zeros(12)
                continue
            f = el.k @ (el.T @ u[el.dofs])
            if fefs and e in fefs:
                f = f + fefs[e][0]
            out[e] = f
        return out

    # ------------------------------------------------------------------ masas y modos
    def mass_vector(self, lc, mode='fef'):
        """Peso concentrado por gdl a partir de las cargas del caso (STAAD arma la
        matriz de masa con las cargas del caso de espectro).
        mode='half': todo 50/50 a cada extremo.
        mode='fef' : peso propio 50/50; cargas de barra / ONEWAY segun las reacciones
                     de empotramiento de la barra (considera liberaciones)."""
        W = np.zeros(self.ndof)
        from .parser import LoadCase
        if mode == 'fef_all':
            lall = LoadCase(lc.num)
            lall.selfweight = lc.selfweight
            lall.member = lc.member
            lall.oneway = lc.oneway
            F, _ = self.load_vector(lall)
            for ax in range(3):
                W[ax::6] += np.abs(F[ax::6])
            for (ids, d) in lc.joint:
                for n in ids:
                    i = self.nidx[n]
                    for k, v in d.items():
                        j = ['FX', 'FY', 'FZ', 'MX', 'MY', 'MZ'].index(k)
                        if j < 3:
                            W[6 * i + j] += abs(v)
            return W
        # peso propio
        lsw = LoadCase(lc.num)
        lsw.selfweight = lc.selfweight
        w = self.member_w_global(lsw)
        for e, wg in w.items():
            el = self.elems[e]
            i1, i2 = self.nidx[el.n1], self.nidx[el.n2]
            for ax in range(3):
                val = abs(wg[ax]) * el.L / 2
                W[6 * i1 + ax] += val
                W[6 * i2 + ax] += val
        # cargas de barra y de tablero
        lml = LoadCase(lc.num)
        lml.member = lc.member
        lml.oneway = lc.oneway
        if mode == 'half':
            w = self.member_w_global(lml)
            for e, wg in w.items():
                el = self.elems[e]
                i1, i2 = self.nidx[el.n1], self.nidx[el.n2]
                for ax in range(3):
                    val = abs(wg[ax]) * el.L / 2
                    W[6 * i1 + ax] += val
                    W[6 * i2 + ax] += val
        else:
            F, _ = self.load_vector(lml)
            for ax in range(3):
                W[ax::6] += np.abs(F[ax::6])
        for (ids, d) in lc.joint:
            for n in ids:
                i = self.nidx[n]
                for k, v in d.items():
                    j = ['FX', 'FY', 'FZ', 'MX', 'MY', 'MZ'].index(k)
                    if j < 3:
                        W[6 * i + j] += abs(v)
        return W

    def modes(self, lc, nmodes, inactive=frozenset(), massmode='fef'):
        W = self.mass_vector(lc, massmode)
        K, idx, lu, zero = self.factor(frozenset(inactive))
        Wf = W[idx]
        md = np.where(Wf > 1e-12)[0]              # gdl con masa (en numeracion libre)
        n = len(idx)
        # flexibilidad condensada: F = S^T K^-1 S
        B = np.zeros((n, len(md)))
        B[md, np.arange(len(md))] = 1.0
        X = lu.solve(B)
        Fm = X[md, :]
        Fm = 0.5 * (Fm + Fm.T)
        Mm = Wf[md] / G_ACC
        # K phi = w2 M phi  ->  (M^1/2 F M^1/2) y = (1/w2) y
        sq = np.sqrt(Mm)
        Asym = (sq[:, None] * Fm) * sq[None, :]
        lam, Y = eigh(Asym)
        order = np.argsort(-lam)
        lam = lam[order]
        Y = Y[:, order]
        nm = min(nmodes, len(md))
        lam = lam[:nm]
        Y = Y[:, :nm]
        w2 = 1.0 / lam
        phi_m = Y / sq[:, None]                    # normalizado a masa
        # expandir a todos los gdl: u = K^-1 (w2 M phi)
        Fin = np.zeros((n, nm))
        Fin[md, :] = (Mm[:, None] * phi_m) * w2[None, :]
        Uf = lu.solve(Fin)
        Phi = np.zeros((self.ndof, nm))
        Phi[idx, :] = Uf
        Mfull = W / G_ACC
        return ModalResult(self, w2, Phi, Mfull, W, frozenset(inactive))


class StaticResult:
    def __init__(self, st, num, u, fefs, inactive, F, K):
        self.st = st
        self.num = num
        self.u = u
        self.fefs = fefs
        self.inactive = inactive
        self.F = F
        self.K = K
        self.ef = st.end_forces(u, fefs, inactive)
        self.wl = {e: v[1] for e, v in fefs.items()}

    def reactions(self):
        st = self.st
        R = self.K @ self.u - self.F
        out = {}
        for n in st.m.supports:
            i = st.nidx[n]
            out[n] = R[6 * i:6 * i + 6].copy()
        return out


class ModalResult:
    def __init__(self, st, w2, Phi, M, W, inactive):
        self.st = st
        self.w2 = w2
        self.Phi = Phi
        self.M = M
        self.W = W
        self.inactive = inactive
        self.T = 2 * math.pi / np.sqrt(w2)
        self.freq = 1.0 / self.T
        # factores de participacion por direccion
        self.gamma = {}
        self.part = {}
        self.wtot = {}
        for ax, d in enumerate('XYZ'):
            r = np.zeros(st.ndof)
            r[ax::6] = 1.0
            Lr = Phi.T @ (M * r)
            gm = np.einsum('ij,i,ij->j', Phi, M, Phi)
            self.gamma[d] = Lr / gm
            # masa total en direccion d que NO esta en apoyos
            free_mass = M.copy()
            free_mass[st.fixed] = 0.0
            mt = (free_mass * r).sum()
            self.wtot[d] = mt * G_ACC
            self.part[d] = (Lr**2 / gm) / mt * 100.0 if mt > 0 else np.zeros(len(w2))

    def spectrum(self, sp):
        """Devuelve por modo el vector de desplazamientos modales maximos para el caso de espectro."""
        pts = np.array(sp['pts'])
        Tp, Sp = pts[:, 0], pts[:, 1]
        sa = np.interp(self.T, Tp, Sp) * sp['scale']      # cm/s2
        nm = len(self.w2)
        U = np.zeros((self.st.ndof, nm))
        coef = np.zeros(nm)
        for d, f in sp['dir'].items():
            coef += self.gamma[d] * f
        amp = coef * sa / self.w2
        U = self.Phi * amp[None, :]
        return U, sa


def combine_modal(vals, method='SRSS', w=None, damp=0.05):
    """vals: (..., nmodos)."""
    if method == 'SRSS':
        return np.sqrt((vals**2).sum(axis=-1))
    if method == 'CQC':
        nm = vals.shape[-1]
        wn = np.sqrt(w)
        r = wn[None, :] / wn[:, None]
        rho = 8 * damp**2 * (1 + r) * r**1.5 / ((1 - r**2)**2 + 4 * damp**2 * r * (1 + r)**2)
        return np.sqrt(np.abs(np.einsum('...i,ij,...j->...', vals, rho, vals)))
    raise ValueError(method)
