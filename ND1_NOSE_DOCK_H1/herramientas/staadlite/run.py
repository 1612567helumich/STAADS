"""Corrida completa al estilo STAAD: casos primarios estaticos (con iteracion de
tensores), casos de espectro (modos con el estado T/C del ultimo caso primario,
SRSS/CQC con signo del modo dominante) y combinaciones lineales."""
import numpy as np
from .analysis import Structure, combine_modal

NSEC = 13


class Run:
    def __init__(self, model, shear=True, massmode='fef_all', tc_state='last', verbose=False):
        self.m = model
        self.st = Structure(model, shear=shear)
        st = self.st
        self.u = {}        # lc -> vector desplazamientos
        self.ef = {}       # lc -> dict e -> 12 fuerzas de extremo (locales)
        self.wl = {}       # lc -> dict e -> carga uniforme local (wx,wy,wz)
        self.reac = {}     # lc -> dict nudo -> 6
        self.inactive = {}
        self.iters = {}
        prim = sorted(model.loads)
        spec = [k for k in prim if model.loads[k].spectrum]
        last_state = frozenset()
        for k in prim:
            lc = model.loads[k]
            r = st.solve_static(lc)
            self.iters[k] = max(r.iters, 1)
            self.inactive[k] = r.inactive
            last_state = r.inactive
            if lc.spectrum:
                continue
            self.u[k] = r.u
            self.ef[k] = r.ef
            self.wl[k] = r.wl
            self.reac[k] = r.reactions()
        self.modal = None
        self.sa = {}
        if spec:
            if tc_state == 'last':
                state = last_state
            elif tc_state == 'all':
                state = frozenset()
            else:
                state = frozenset(tc_state)
            self.tc_modal = state
            masscase = model.loads[spec[0]]
            self.modal = st.modes(masscase, model.cutoff_modes, state, massmode=massmode)
            mr = self.modal
            K = st.assemble(state)
            for k in spec:
                sp = model.loads[k].spectrum
                U, sa = mr.spectrum(sp)
                self.sa[k] = sa
                method = sp['method']
                dom = sp['dominant']
                nm = U.shape[1]
                # desplazamientos
                umax = combine_modal(U, method, mr.w2, sp['damp'])
                if dom:
                    sg = np.sign(U[:, dom - 1])
                    sg[sg == 0] = 1.0
                    umax = umax * sg
                self.u[k] = umax
                # fuerzas de extremo por modo
                efk = {}
                for e, el in st.elems.items():
                    if e in state:
                        efk[e] = np.zeros(12)
                        continue
                    fm = el.k @ (el.T @ U[el.dofs, :])       # 12 x nm
                    f = combine_modal(fm, method, mr.w2, sp['damp'])
                    if dom:
                        sg = np.sign(fm[:, dom - 1])
                        sg[sg == 0] = 1.0
                        f = f * sg
                    efk[e] = f
                self.ef[k] = efk
                self.wl[k] = {}
                # reacciones por modo
                Rm = K @ U
                rk = {}
                for n in model.supports:
                    i = st.nidx[n]
                    rm = Rm[6 * i:6 * i + 6, :]
                    rr = combine_modal(rm, method, mr.w2, sp['damp'])
                    if dom:
                        sg = np.sign(rm[:, dom - 1])
                        sg[sg == 0] = 1.0
                        rr = rr * sg
                    rk[n] = rr
                self.reac[k] = rk
                # cortante basal por modo
        self.spec_cases = spec

    # ---------------------------------------------------------------- acceso
    def factors(self, lc):
        """Devuelve [(primario, factor)] para un caso o combinacion."""
        if lc in self.m.loads:
            return [(lc, 1.0)]
        out = []
        for (k, f) in self.m.combos[lc][1]:
            for (kk, ff) in self.factors(k):
                out.append((kk, f * ff))
        return out

    def disp(self, lc):
        return sum(f * self.u[k] for k, f in self.factors(lc))

    def node_disp(self, lc, n):
        i = self.st.nidx[n]
        return self.disp(lc)[6 * i:6 * i + 6]

    def end_forces(self, lc, e):
        return sum(f * self.ef[k][e] for k, f in self.factors(lc))

    def wlocal(self, lc, e):
        w = np.zeros(3)
        for k, f in self.factors(lc):
            v = self.wl[k].get(e)
            if v is not None:
                w = w + f * v
        return w

    def reaction(self, lc, n):
        return sum(f * self.reac[k][n] for k, f in self.factors(lc))

    def section_forces(self, lc, e, nsec=NSEC):
        """Fuerzas internas en nsec secciones: columnas [x, P(+tension), Vy, Vz, T, My, Mz]."""
        el = self.st.elems[e]
        out = np.zeros((nsec, 7))
        xs = np.linspace(0.0, el.L, nsec)
        out[:, 0] = xs
        for k, f in self.factors(lc):
            f1 = self.ef[k][e]
            w = self.wl[k].get(e)
            if w is None or el.kind == 'truss':
                w = np.zeros(3)
            if el.kind == 'truss':
                # STAAD lleva la carga de barras tipo armadura a los nudos: solo axial constante
                if k in self.spec_cases:
                    ax = -f1[0]
                else:
                    ul = el.T @ self.u[k][el.dofs]
                    ax = 0.0 if e in self.inactive.get(k, ()) else el.E * el.sec.A / el.L * (ul[6] - ul[0])
                out[:, 1] += f * ax
                continue
            if k in self.spec_cases:
                # sin carga en el claro: interpolar entre extremos firmados
                f2 = self.ef[k][e]
                t = xs / el.L
                P = -(f1[0] * (1 - t) + (-f2[6]) * t)
                Vy = f1[1] * (1 - t) + (-f2[7]) * t
                Vz = f1[2] * (1 - t) + (-f2[8]) * t
                T = -(f1[3] * (1 - t) + (-f2[9]) * t)
                My = -(f1[4] * (1 - t) + (-f2[10]) * t)
                Mz = -(f1[5] * (1 - t) + (-f2[11]) * t)
            else:
                P = -(f1[0] + w[0] * xs)
                Vy = f1[1] + w[1] * xs
                Vz = f1[2] + w[2] * xs
                T = -f1[3] * np.ones(nsec)
                My = -(f1[4] + xs * f1[2] + w[2] * xs**2 / 2)
                Mz = -(f1[5] - xs * f1[1] - w[1] * xs**2 / 2)
            out[:, 1] += f * P
            out[:, 2] += f * Vy
            out[:, 3] += f * Vz
            out[:, 4] += f * T
            out[:, 5] += f * My
            out[:, 6] += f * Mz
        return out

    def base_shear(self, k):
        mr = self.modal
        sp = self.m.loads[k].spectrum
        out = {}
        for d, f in sp['dir'].items():
            wm = mr.part[d] / 100.0 * mr.wtot[d]
            vm = wm * self.sa[k] / 981.0 * abs(f)
            out[d] = (vm, float(np.sqrt((vm**2).sum())))
        return out
