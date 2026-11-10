"""Lector de un subconjunto del lenguaje de entrada de STAAD.Pro (el que usan
los modelos de los nose docks).  No ejecuta nada del archivo: solo lo interpreta
como texto."""
import re
from dataclasses import dataclass, field


@dataclass
class LoadCase:
    num: int
    title: str = ''
    ltype: str = ''
    selfweight: list = field(default_factory=list)     # (dir, factor)
    joint: list = field(default_factory=list)          # (nodes, {FX:..})
    member: list = field(default_factory=list)         # (members, kind, dir, vals)
    oneway: list = field(default_factory=list)         # (group, p, dir, inclined, towards, kind)
    spectrum: dict = None                              # {method, dir:{X:f..}, scale, damp, dominant, pts:[(T,Sa)]}


@dataclass
class Model:
    title: str = ''
    nodes: dict = field(default_factory=dict)
    members: dict = field(default_factory=dict)
    groups: dict = field(default_factory=dict)         # name -> (kind, [ids])
    tables: dict = field(default_factory=dict)         # tabno -> {name: (type, [vals])}
    materials: dict = field(default_factory=dict)
    prop: dict = field(default_factory=dict)           # member -> spec dict
    beta: dict = field(default_factory=dict)
    matname: dict = field(default_factory=dict)
    supports: dict = field(default_factory=dict)       # node -> [6 bool]
    release: dict = field(default_factory=dict)        # member -> {'START': set, 'END': set}
    truss: set = field(default_factory=set)
    tension: set = field(default_factory=set)
    cutoff_modes: int = 6
    loads: dict = field(default_factory=dict)
    combos: dict = field(default_factory=dict)         # num -> (title, [(lc, f)])
    params: dict = field(default_factory=dict)         # name -> {member: value}
    check_members: list = field(default_factory=list)
    raw_order: list = field(default_factory=list)


DOFS = ['FX', 'FY', 'FZ', 'MX', 'MY', 'MZ']


def _logical_lines(text):
    """Une continuaciones ('-' al final) y parte por ';'.  Devuelve lineas no vacias."""
    out = []
    buf = ''
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith('*'):
            continue
        if line.rstrip().endswith(' -') or line.rstrip() == '-':
            buf += line.rstrip()[:-1] + ' '
            continue
        buf += line
        out.append(buf.strip())
        buf = ''
    if buf.strip():
        out.append(buf.strip())
    return out


def parse_list(tokens, model, kind='member'):
    """Convierte tokens tipo '1 TO 10 12 _GRUPO ALL' en lista de enteros."""
    ids = []
    i = 0
    while i < len(tokens):
        t = tokens[i].upper()
        if t == 'TO':
            a = ids.pop()
            b = int(tokens[i + 1])
            step = 1
            if i + 3 < len(tokens) and tokens[i + 2].upper() == 'BY':
                step = int(tokens[i + 3])
                i += 2
            ids.extend(range(a, b + 1, step))
            i += 2
            continue
        if t == 'ALL':
            src = model.members if kind == 'member' else model.nodes
            ids.extend(sorted(src))
            i += 1
            continue
        if t.startswith('_'):
            g = model.groups.get(t)
            if g is None:
                raise ValueError('grupo desconocido ' + t)
            ids.extend(g[1])
            i += 1
            continue
        ids.append(int(t))
        i += 1
    return ids


def _split_list_tail(tokens):
    """Separa el prefijo que es lista (numeros, TO, BY, _GRUPO, ALL) del resto."""
    i = 0
    while i < len(tokens):
        t = tokens[i].upper()
        if re.fullmatch(r'\d+', t) or t in ('TO', 'BY', 'ALL') or t.startswith('_'):
            i += 1
        else:
            break
    return tokens[:i], tokens[i:]


def parse(text):
    m = Model()
    lines = _logical_lines(text)
    mode = None
    sub = None
    cur_load = None
    cur_tab = None
    tab_type = None
    tab_pending_name = None
    group_kind = None
    in_material = None
    spec_pts = None
    combo_cur = None
    param_mode = False
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        up = line.upper()
        tok = line.split()
        utok = up.split()
        # ---------------- encabezados de bloque
        if up.startswith('STAAD '):
            m.title = line
            mode = None
            continue
        if up.startswith(('START JOB', 'ENGINEER', 'END JOB', 'INPUT WIDTH', 'SET ', 'UNIT ')) and mode not in ('table',):
            if up.startswith('UNIT ') and 'CM' not in utok and 'KG' not in utok:
                raise ValueError('solo UNIT CM KG soportado: ' + line)
            continue
        if up.startswith('JOINT COORD'):
            mode = 'joints'
            continue
        if up.startswith('MEMBER INCID'):
            mode = 'members'
            continue
        if up.startswith('START GROUP'):
            mode = 'groups'
            group_kind = None
            continue
        if up.startswith('END GROUP'):
            mode = None
            continue
        if up.startswith('START USER TABLE'):
            mode = 'table'
            continue
        if mode == 'table':
            if up == 'END':
                mode = None
                continue
            if up.startswith('TABLE '):
                cur_tab = int(utok[1])
                m.tables.setdefault(cur_tab, {})
                tab_type = None
                tab_pending_name = None
                continue
            if up.startswith('UNIT '):
                continue
            if utok[0] in ('GENERAL', 'TUBE', 'WIDE', 'CHANNEL', 'ANGLE', 'PIPE', 'TEE', 'DOUBLE', 'PRISMATIC', 'ISECTION'):
                tab_type = utok[0]
                continue
            # nombre o valores
            try:
                vals = [float(v) for v in tok]
                m.tables[cur_tab][tab_pending_name] = (tab_type, vals)
                tab_pending_name = None
            except ValueError:
                tab_pending_name = tok[0].upper()
            continue
        if up.startswith('DEFINE MATERIAL START'):
            mode = 'material'
            continue
        if mode == 'material':
            if up.startswith('END DEFINE MATERIAL'):
                mode = None
                continue
            if up.startswith('ISOTROPIC'):
                in_material = utok[1]
                m.materials[in_material] = {}
                continue
            if utok[0] == 'STRENGTH':
                for k in range(1, len(utok) - 1, 2):
                    m.materials[in_material][utok[k]] = float(utok[k + 1])
                continue
            if utok[0] == 'TYPE':
                m.materials[in_material]['TYPE'] = utok[1]
                continue
            m.materials[in_material][utok[0]] = float(utok[1])
            continue
        if up.startswith('MEMBER PROPERTY'):
            mode = 'prop'
            continue
        if up.startswith('CONSTANTS'):
            mode = 'const'
            continue
        if up.startswith('SUPPORTS'):
            mode = 'supp'
            continue
        if up.startswith('MEMBER RELEASE'):
            mode = 'rel'
            continue
        if up.startswith('MEMBER TRUSS'):
            mode = 'truss'
            continue
        if up.startswith('MEMBER TENSION'):
            mode = 'tens'
            continue
        if up.startswith('CUT OFF MODE SHAPE'):
            m.cutoff_modes = int(utok[-1])
            continue
        if up.startswith('LOAD COMB'):
            num = int(utok[2])
            combo_cur = num
            m.combos[num] = (' '.join(tok[3:]), [])
            mode = 'combo'
            continue
        if re.match(r'LOAD \d+', up):
            num = int(utok[1])
            lc = LoadCase(num)
            mt = re.search(r'LOADTYPE\s+(.*?)\s+TITLE\s+(.*)$', line, re.I)
            if mt:
                lc.ltype = mt.group(1).strip()
                lc.title = mt.group(2).strip()
            else:
                lc.title = ' '.join(tok[2:])
            m.loads[num] = lc
            cur_load = lc
            mode = 'load'
            sub = None
            spec_pts = None
            continue
        if up.startswith('PERFORM ANALYSIS') or up.startswith('PDELTA') :
            mode = 'post'
            continue
        if up.startswith('PARAMETER'):
            mode = 'param'
            continue
        if up.startswith('FINISH'):
            break
        if up.startswith(('DEFINE ENVELOPE', 'END DEFINE ENVELOPE', 'LOAD LIST', 'PRINT', 'STEEL TAKE', 'STEEL MEMBER TAKE')):
            continue
        # ---------------- contenido
        if mode == 'joints':
            for part in line.split(';'):
                p = part.split()
                if len(p) >= 4:
                    m.nodes[int(p[0])] = (float(p[1]), float(p[2]), float(p[3]))
            continue
        if mode == 'members':
            for part in line.split(';'):
                p = part.split()
                if len(p) >= 3:
                    m.members[int(p[0])] = (int(p[1]), int(p[2]))
            continue
        if mode == 'groups':
            if utok[0] in ('MEMBER', 'FLOOR', 'JOINT', 'GEOMETRY', 'ELEMENT') and len(utok) == 1:
                group_kind = utok[0]
                continue
            name = utok[0]
            kind = 'node' if group_kind == 'JOINT' else 'member'
            m.groups[name] = (group_kind, parse_list(tok[1:], m, kind))
            continue
        if mode == 'prop':
            lst, tail = _split_list_tail(tok)
            ids = parse_list(lst, m)
            ut = [t.upper() for t in tail]
            if ut[0] == 'UPTABLE':
                spec = {'kind': 'UPT', 'table': int(ut[1]), 'name': ut[2]}
            elif ut[0] == 'TABLE':
                if ut[2] in ('TUBE', 'PIPE'):
                    d = {ut[k]: float(ut[k + 1]) for k in range(3, len(ut) - 1, 2)}
                    spec = {'kind': ut[2], **d}
                else:
                    spec = {'kind': 'AISC', 'typ': ut[1], 'name': ut[2]}
            elif ut[0].startswith('PRIS'):
                d = {ut[k]: float(ut[k + 1]) for k in range(1, len(ut) - 1, 2)}
                spec = {'kind': 'PRIS', **d}
            else:
                raise ValueError('propiedad no soportada: ' + line)
            for e in ids:
                m.prop[e] = spec
            continue
        if mode == 'const':
            if utok[0] == 'BETA':
                ang = float(utok[1])
                ids = parse_list(tok[3:], m) if utok[2].startswith('MEMB') else parse_list(tok[2:], m)
                for e in ids:
                    m.beta[e] = ang
            elif utok[0] == 'MATERIAL':
                name = utok[1]
                ids = parse_list(tok[3:], m) if (len(utok) > 2 and utok[2].startswith('MEMB')) else parse_list(tok[2:], m)
                for e in ids:
                    m.matname[e] = name
            continue
        if mode == 'supp':
            lst, tail = _split_list_tail(tok)
            ids = parse_list(lst, m, 'node')
            ut = [t.upper() for t in tail]
            if ut[0] == 'FIXED' and len(ut) == 1:
                r = [True] * 6
            elif ut[0] == 'PINNED':
                r = [True, True, True, False, False, False]
            elif ut[0] in ('FIXED', 'ENFORCED') and ut[1] == 'BUT':
                r = [True] * 6
                for t in ut[2:]:
                    if t in DOFS:
                        r[DOFS.index(t)] = False
            else:
                raise ValueError('apoyo no soportado: ' + line)
            for n in ids:
                m.supports[n] = r
            continue
        if mode == 'rel':
            lst, tail = _split_list_tail(tok)
            ids = parse_list(lst, m)
            ut = [t.upper() for t in tail]
            end = ut[0]
            for e in ids:
                d = m.release.setdefault(e, {'START': set(), 'END': set()})
                for t in ut[1:]:
                    d[end].add(DOFS.index(t))
            continue
        if mode == 'truss':
            m.truss.update(parse_list(tok, m))
            continue
        if mode == 'tens':
            m.tension.update(parse_list(tok, m))
            continue
        if mode == 'combo':
            vals = tok
            for k in range(0, len(vals) - 1, 2):
                m.combos[combo_cur][1].append((int(vals[k]), float(vals[k + 1])))
            continue
        if mode == 'load':
            if up.startswith('SELFWEIGHT'):
                cur_load.selfweight.append((utok[1], float(utok[2])))
                continue
            if up.startswith('ONEWAY LOAD'):
                sub = 'oneway'
                continue
            if up.startswith('FLOOR LOAD'):
                sub = 'floor'
                continue
            if up.startswith('MEMBER LOAD'):
                sub = 'member'
                continue
            if up.startswith('JOINT LOAD'):
                sub = 'joint'
                continue
            if up.startswith('SPECTRUM'):
                sp = {'method': utok[1], 'dir': {}, 'scale': 1.0, 'damp': 0.05, 'dominant': None, 'pts': []}
                k = 2
                while k < len(utok):
                    t = utok[k]
                    if t in ('X', 'Y', 'Z'):
                        sp['dir'][t] = float(utok[k + 1]); k += 2
                    elif t == 'ACC':
                        k += 1
                    elif t == 'SCALE':
                        sp['scale'] = float(utok[k + 1]); k += 2
                    elif t == 'DAMP':
                        sp['damp'] = float(utok[k + 1]); k += 2
                    elif t == 'DOMINANT':
                        sp['dominant'] = int(utok[k + 1]); k += 2
                    else:
                        k += 1
                cur_load.spectrum = sp
                sub = 'spectrum'
                continue
            if sub == 'spectrum' and re.match(r'^[\d.]', up):
                for part in line.split(';'):
                    p = part.split()
                    if len(p) == 2:
                        cur_load.spectrum['pts'].append((float(p[0]), float(p[1])))
                continue
            if sub in ('oneway', 'floor'):
                name = utok[0]
                rest = utok[1:]
                d = {'group': name, 'kind': sub, 'inclined': 'INCLINED' in rest, 'towards': None, 'dir': 'GY'}
                k = 0
                while k < len(rest):
                    t = rest[k]
                    if t in ('ONE', 'ONELOAD', 'FLOAD', 'FLO'):
                        d['p'] = float(rest[k + 1]); k += 2
                    elif t in ('GX', 'GY', 'GZ'):
                        d['dir'] = t; k += 1
                    elif t == 'TOWARDS':
                        d['towards'] = int(rest[k + 1]); k += 2
                    else:
                        k += 1
                cur_load.oneway.append(d)
                continue
            if sub == 'member':
                lst, tail = _split_list_tail(tok)
                ids = parse_list(lst, m)
                ut = [t.upper() for t in tail]
                cur_load.member.append((ids, ut[0], ut[1], [float(v) for v in ut[2:]]))
                continue
            if sub == 'joint':
                lst, tail = _split_list_tail(tok)
                ids = parse_list(lst, m, 'node')
                ut = [t.upper() for t in tail]
                d = {ut[k]: float(ut[k + 1]) for k in range(0, len(ut) - 1, 2)}
                cur_load.joint.append((ids, d))
                continue
            continue
        if mode == 'param':
            if up.startswith('CODE'):
                m.params['CODE'] = ' '.join(utok[1:])
                continue
            if up.startswith('CHECK CODE'):
                rest = tok[2:]
                if rest and rest[0].upper().startswith('MEMB'):
                    rest = rest[1:]
                m.check_members = parse_list(rest, m)
                continue
            if up.startswith('SELECT'):
                continue
            name = utok[0]
            val = float(utok[1])
            rest = tok[2:]
            if rest and rest[0].upper().startswith('MEMB'):
                rest = rest[1:]
            ids = parse_list(rest, m) if rest else sorted(m.members)
            d = m.params.setdefault(name, {})
            for e in ids:
                d[e] = val
            continue
    return m


def read(path):
    with open(path, 'r', encoding='latin-1') as f:
        return parse(f.read())
