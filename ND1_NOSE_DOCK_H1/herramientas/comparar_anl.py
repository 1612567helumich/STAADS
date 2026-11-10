"""Compara los resultados del emulador (staadlite) contra un .ANL de STAAD.Pro.

Uso:
    python3 comparar_anl.py MODELO.STD RESULTADOS.ANL [33-66 | all]

Si no se da MODELO.STD (se pasa '-'), el modelo se reconstruye del eco de entrada
que trae el propio ANL.  Reporta periodos, participacion modal, sumas de
reacciones, desplazamientos y relaciones de diseño miembro por miembro."""
import sys, os, re, json, collections, tempfile
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from staadlite import parser, anlread, design
from staadlite.run import Run


def extract_input(anl, dst):
    pat = re.compile(r'^\s{0,6}(\d+)\. (.*)$')
    out = []; last = 0
    with open(anl, 'r', encoding='latin-1') as f:
        for line in f:
            m = pat.match(line.rstrip('\r\n'))
            if m and int(m.group(1)) == last + 1:
                out.append(m.group(2)); last += 1
    open(dst, 'w', encoding='latin-1').write('\n'.join(out) + '\n')
    return dst


def design_rows(anl):
    L = open(anl, 'r', encoding='latin-1').read().splitlines()
    res = []
    for i, l in enumerate(L):
        m = re.match(r'\|\s+Member No:\s+(\d+)\s+Profile:\s+(\S+)\s+(.*?)\s+\((.*?)\)\s*\|', l)
        if not m:
            continue
        m2 = re.search(r'Status:\s+(\S+)\s+Ratio:\s+(\S+)\s+Loadcase:\s+(\d+)', L[i + 1])
        m3 = re.search(r'Location:\s+(\S+)\s+Ref:\s+(.*?)\s*\|', L[i + 2])
        if m2 and m3:
            res.append(dict(mem=int(m.group(1)), prof=m.group(3).strip(), status=m2.group(1), ratio=float(m2.group(2)),
                            lc=int(m2.group(3)), loc=float(m3.group(1)), ref=m3.group(2).strip()))
    return res


def main():
    std, anl = sys.argv[1], sys.argv[2]
    lcspec = sys.argv[3] if len(sys.argv) > 3 else '33-66'
    if std == '-':
        std = extract_input(anl, os.path.join(tempfile.mkdtemp(), 'eco.std'))
    m = parser.read(std)
    R = Run(m)
    print('modelo: %d nudos, %d miembros.  Estado de tensores usado en los modos: %s' % (len(m.nodes), len(m.members), sorted(R.tc_modal)))
    fr = anlread.frequencies(anl); pa = anlread.participation(anl)
    if fr and R.modal is not None:
        mr = R.modal
        print('\nMODOS      T STAAD    T emul.   dif%   | %X STAAD/emul | %Z STAAD/emul')
        for k in range(1, min(len(mr.T), 15) + 1):
            if k not in fr: break
            p = pa.get(k, [0] * 9)
            print('  %3d    %.5f   %.5f  %6.2f  | %6.2f %6.2f | %6.2f %6.2f' % (k, fr[k][1], mr.T[k - 1], (mr.T[k - 1] / fr[k][1] - 1) * 100,
                                                                              p[0], mr.part['X'][k - 1], p[2], mr.part['Z'][k - 1]))
        n = min(len(fr), len(mr.T))
        err = max(abs(mr.T[k - 1] / fr[k][1] - 1) for k in range(1, n + 1)) * 100
        print('  dif. maxima de periodo en %d modos: %.3f%%' % (n, err))
        if pa:
            last = max(pa)
            print('  participacion acumulada STAAD (%d modos): X=%.2f Z=%.2f ; emulador: X=%.2f Z=%.2f' % (last, pa[last][3], pa[last][5], mr.part['X'][:last].sum(), mr.part['Z'][:last].sum()))
    RA = anlread.reactions(anl)
    if RA:
        print('\nSUMA DE REACCIONES POR CASO (STAAD | emulador)')
        for lc in sorted({k[1] for k in RA}):
            if lc not in m.loads or m.loads[lc].spectrum: continue
            a = sum((v for k, v in RA.items() if k[1] == lc), np.zeros(6))
            b = sum(R.reac[lc].values())
            print('  LC%2d  FX %10.1f %10.1f   FY %10.1f %10.1f   FZ %10.1f %10.1f' % (lc, a[0], b[0], a[1], b[1], a[2], b[2]))
    DA = anlread.displacements(anl)
    if DA:
        pairs = [(v[c], R.node_disp(l, n)[c]) for (n, l), v in DA.items() if n in R.st.nidx and (l in m.loads or l in m.combos) for c in (0, 2)]
        a = np.array([p[0] for p in pairs]); b = np.array([p[1] for p in pairs])
        print('\nDESPLAZAMIENTOS X/Z: n=%d  max|STAAD|=%.3f cm  dif. abs. max=%.4f cm (%.2f%% del maximo)' % (len(a), np.abs(a).max(), np.abs(a - b).max(), np.abs(a - b).max() / np.abs(a).max() * 100))
    D = design_rows(anl)
    if D:
        if lcspec == 'all':
            lcs = sorted(list(m.loads) + list(m.combos))
        else:
            a, b = lcspec.split('-'); lcs = list(range(int(a), int(b) + 1))
        byp = collections.defaultdict(list)
        for r in D:
            if r['mem'] in R.st.elems and R.st.elems[r['mem']].sec.shape != 'ROD':
                byp[r['prof']].append((r, design.check_member(R, r['mem'], lcs)))
        print('\nDISENO (combinaciones %s)   perfil, n, max STAAD, max emul., dif. rms, dif. max' % lcspec)
        allerr = []
        for pf, lst in byp.items():
            d = np.array([res['ratio'] - r['ratio'] for r, res in lst]); allerr.extend(d)
            print('  %-22s %4d  %6.3f  %6.3f  %7.4f %7.4f' % (pf, len(lst), max(r['ratio'] for r, _ in lst), max(res['ratio'] for _, res in lst), np.sqrt((d**2).mean()), np.abs(d).max()))
        allerr = np.array(allerr)
        fails = [(r['mem'], r['ratio']) for lst in byp.values() for r, _ in lst if r['status'] != 'PASS']
        print('  TOTAL %d miembros: dif. rms %.4f, max %.4f.  No pasan en STAAD: %s' % (len(allerr), np.sqrt((allerr**2).mean()), np.abs(allerr).max(), fails or 'ninguno'))


if __name__ == '__main__':
    main()
