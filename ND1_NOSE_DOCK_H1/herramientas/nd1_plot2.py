import sys, os
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from staadlite import parser
std, out = sys.argv[1], sys.argv[2]
m = parser.read(std)
YTOP = max(p[1] for p in m.nodes.values())      # cumbrera (eje 3); cubierta y = YTOP - 0.051 z
COL = {'W': '#c0392b', 'MCE10': '#8e44ad', 'MCE6': '#1f618d', 'MCE4': '#2980b9', 'MCE8': '#1f618d', 'MC10': '#27ae60', 'MCC10': '#d35400', 'C-14': '#555555',
       '2-14': '#000000', 'PIPS7': '#c9a400', 'HSST': '#e67e22', 'MC4': '#e67e22', 'ROD': '#e84393'}
def color(e):
    sp = m.prop[e]; nm = sp.get('name') or 'ROD'
    for k, v in COL.items():
        if nm.startswith(k): return v
    return 'k'
def lw(e):
    sp = m.prop[e]; nm = sp.get('name') or 'ROD'
    return 2.6 if nm.startswith('W') else (0.7 if nm == 'ROD' else (0.8 if nm.startswith('PIPS') else 1.3))
fig, axs = plt.subplots(2, 3, figsize=(24, 14))
# vistas: (titulo, filtro de plano, ejes)
views = [('Eje 1 (Z=1600) frente abierto', lambda p: abs(p[2] - 1600) < 1, (0, 1)), ('Eje 2 (Z=800)', lambda p: abs(p[2] - 800) < 1, (0, 1)),
         ('Eje 3 (Z=0) muro de fondo', lambda p: abs(p[2]) < 1, (0, 1)), ('Eje A (X=0)', lambda p: abs(p[0]) < 1, (2, 1)),
         ('Eje B (X=750) armadura longitudinal', lambda p: abs(p[0] - 750) < 1, (2, 1)), ('Cubierta (planta)', None, (0, 2))]
for ax, (title, flt, (i, j)) in zip(axs.ravel(), views):
    for e, (a, b) in m.members.items():
        p, q = m.nodes[a], m.nodes[b]
        if flt is None:
            if not (abs((YTOP - 0.051 * p[2]) - p[1]) < 1 and abs((YTOP - 0.051 * q[2]) - q[1]) < 1): continue
        elif not (flt(p) and flt(q)): continue
        ax.plot([p[i], q[i]], [p[j], q[j]], color=color(e), lw=lw(e))
        if title.startswith('Eje 3') or title.startswith('Eje A'):
            pass
    for n in m.supports:
        p = m.nodes[n]
        if flt is not None and flt(p):
            ax.plot([p[i]], [p[j]], marker='s' if all(m.supports[n]) else ('^' if m.supports[n][0] else 'o'), color='k', ms=7)
    ax.set_title(title); ax.set_aspect('equal'); ax.grid(alpha=0.3)
    if flt is None: ax.invert_yaxis()
fig.tight_layout(); fig.savefig(out, dpi=62); print('ok')
