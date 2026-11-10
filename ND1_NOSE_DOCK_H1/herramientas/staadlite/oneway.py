"""Emulacion de ONEWAY LOAD por grupo: detecta los tableros (caras cerradas) que
forman las barras del grupo en su plano y reparte la presion a los dos lados
largos de cada tablero (la carga 'viaja' en la direccion corta)."""
import math
import numpy as np


def _plane_basis(P):
    c = P.mean(axis=0)
    u, s, vt = np.linalg.svd(P - c)
    e1, e2, nrm = vt[0], vt[1], vt[2]
    return c, e1, e2, nrm, s


def find_panels(st, members):
    """Devuelve lista de tableros: cada uno = lista ordenada de nudos (ids)."""
    m = st.m
    edges = {}
    for e in members:
        if e not in st.elems:
            continue
        a, b = m.members[e]
        if a == b:
            continue
        edges[(min(a, b), max(a, b))] = e
    nodes = sorted({n for ab in edges for n in ab})
    if len(nodes) < 3:
        return [], edges, None
    P = np.array([m.nodes[n] for n in nodes])
    c, e1, e2, nrm, s = _plane_basis(P)
    xy = {n: ((np.array(m.nodes[n]) - c) @ e1, (np.array(m.nodes[n]) - c) @ e2) for n in nodes}
    adj = {n: set() for n in nodes}
    for (a, b) in edges:
        adj[a].add(b)
        adj[b].add(a)
    # podar colgantes
    changed = True
    while changed:
        changed = False
        for n in list(adj):
            if len(adj[n]) <= 1:
                for o in adj[n]:
                    adj[o].discard(n)
                del adj[n]
                changed = True
    if not adj:
        return [], edges, (c, e1, e2, nrm)
    ang = {}
    for n, nb in adj.items():
        x0, y0 = xy[n]
        ang[n] = sorted(nb, key=lambda o: math.atan2(xy[o][1] - y0, xy[o][0] - x0))
    visited = set()
    faces = []
    for a in adj:
        for b in adj[a]:
            if (a, b) in visited:
                continue
            face = []
            u, v = a, b
            ok = True
            for _ in range(10000):
                visited.add((u, v))
                face.append(u)
                lst = ang[v]
                i = lst.index(u)
                w = lst[(i - 1) % len(lst)]      # siguiente en sentido horario => cara a la izquierda
                u, v = v, w
                if (u, v) == (a, b):
                    break
            else:
                ok = False
            if not ok:
                continue
            area = 0.0
            for i in range(len(face)):
                x1, y1 = xy[face[i]]
                x2, y2 = xy[face[(i + 1) % len(face)]]
                area += x1 * y2 - x2 * y1
            area *= 0.5
            if area > 1e-6:
                faces.append((face, area))
    return faces, edges, (c, e1, e2, nrm, xy)


def _sides(face, xy, tol_deg=2.0):
    n = len(face)
    # vertices "reales": donde cambia la direccion
    corner = []
    for i in range(n):
        p0 = np.array(xy[face[i - 1]])
        p1 = np.array(xy[face[i]])
        p2 = np.array(xy[face[(i + 1) % n]])
        a = p1 - p0
        b = p2 - p1
        cr = a[0] * b[1] - a[1] * b[0]
        dt = a @ b
        angle = abs(math.degrees(math.atan2(cr, dt)))
        if angle > tol_deg:
            corner.append(i)
    if len(corner) < 3:
        return []
    sides = []
    for k in range(len(corner)):
        i0 = corner[k]
        i1 = corner[(k + 1) % len(corner)]
        chain = []
        i = i0
        while True:
            j = (i + 1) % n
            chain.append((face[i], face[j]))
            i = j
            if i == i1:
                break
        sides.append(chain)
    return sides


def distribute(st, group, towards=None):
    """dict miembro -> ancho tributario equivalente (cm2 de tablero por cm de barra)."""
    m = st.m
    members = m.groups[group][1]
    faces, edges, geo = find_panels(st, members)
    out = {}
    info = []
    if not faces:
        st._ow_info = getattr(st, '_ow_info', {})
        st._ow_info[group] = info
        return out
    xy = geo[4]

    def elen(a, b):
        return float(np.linalg.norm(np.array(m.nodes[a]) - np.array(m.nodes[b])))

    def eid(a, b):
        return edges[(min(a, b), max(a, b))]
    for face, area2d in faces:
        # area real (el plano de ajuste es el del grupo, asi que area2d ya es real)
        area = area2d
        sides = _sides(face, xy)
        slen = [sum(elen(a, b) for a, b in ch) for ch in sides]
        chosen = None
        if len(sides) == 4:
            p02 = slen[0] + slen[2]
            p13 = slen[1] + slen[3]
            if towards is not None:
                for k, ch in enumerate(sides):
                    if any(eid(a, b) == towards for a, b in ch):
                        chosen = (k, (k + 2) % 4)
                if chosen is None and towards in st.elems:
                    # lado paralelo a la barra indicada
                    tdir = st.elems[towards].R[0]
                    best = None
                    for k, ch in enumerate(sides):
                        a, b = ch[0][0], ch[-1][1]
                        v = np.array(m.nodes[b]) - np.array(m.nodes[a])
                        v /= np.linalg.norm(v)
                        cs = abs(v @ tdir)
                        if best is None or cs > best[0]:
                            best = (cs, k)
                    chosen = (best[1], (best[1] + 2) % 4)
            if chosen is None:
                chosen = (0, 2) if p02 >= p13 else (1, 3)
            for k in chosen:
                L = slen[k]
                for a, b in sides[k]:
                    e = eid(a, b)
                    out[e] = out.get(e, 0.0) + (area / 2.0) / L
            info.append((face, area, 'oneway', [slen[k] for k in chosen]))
        elif len(sides) >= 3:
            tot = sum(slen)
            for k, ch in enumerate(sides):
                for a, b in ch:
                    e = eid(a, b)
                    out[e] = out.get(e, 0.0) + area / tot
            info.append((face, area, 'perimetro', slen))
    st._ow_info = getattr(st, '_ow_info', {})
    st._ow_info[group] = info
    return out
