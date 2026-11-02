"""Small reader for STAAD.Pro output files (.ANL).

parse_input()      -> model echoed at the top of the .ANL (joints, members,
                      plates, groups, properties, BETA, supports, releases,
                      truss members, load titles).
parse_code_check() -> one record per member from CHECK CODE (AISC 360-16).

Only the commands used by this project are handled.
"""
import re

ECHO = re.compile(r"^\s{0,6}(\d+)\. (.*)$")
INT = re.compile(r"^\d+$")


def _commands(lines):
    """Echoed input commands with '-' continuations joined."""
    cmds, buf, started = [], "", False
    for raw in lines:
        m = ECHO.match(raw.rstrip("\n"))
        if not m:
            continue
        num, text = int(m.group(1)), m.group(2).rstrip()
        if num == 1 and text.startswith("STAAD"):
            started = True
        if not started:
            continue
        if text.endswith(" -") or text == "-":
            buf += text[:-1] + " "
            continue
        cmds.append((buf + text).strip())
        buf = ""
        if text.strip() == "FINISH":
            break
    return cmds


def expand(tokens):
    """'1 TO 5 7' -> [1, 2, 3, 4, 5, 7] (stops at the first non-number)."""
    res, i = [], 0
    while i < len(tokens):
        t = tokens[i]
        if t == "TO":
            a, b, step, j = res[-1], int(tokens[i + 1]), 1, i + 2
            if j + 1 < len(tokens) and tokens[j] == "BY":
                step, j = int(tokens[j + 1]), j + 2
            res.extend(range(a + step, b + 1, step))
            i = j
            continue
        if not INT.match(t):
            break
        res.append(int(t))
        i += 1
    return res


def _split_list(tokens):
    k = 0
    while k < len(tokens) and (tokens[k] == "TO" or INT.match(tokens[k])):
        k += 1
    return expand(tokens[:k]), tokens[k:]


def parse_input(path):
    with open(path, encoding="latin-1") as fh:
        lines = fh.readlines()
    head = "".join(lines[:40])
    meta = {
        "version": (re.search(r"Version\s+([\d.]+)", head) or [None, ""])[1],
        "run_date": (re.search(r"Date=\s+(.+?)\s+\*", head) or [None, ""])[1],
        "input_file": (re.search(r"INPUT FILE:\s*(.+)", head) or [None, ""])[1].strip(),
    }
    joints, members, shells, groups, props, ptypes = {}, {}, {}, {}, {}, {}
    beta, supports, releases, truss, load_titles = {}, {}, {}, set(), {}
    section, kind, group = None, None, None
    starts = {
        "JOINT COORDINATES": "JOINT", "MEMBER INCIDENCES": "MEMB",
        "ELEMENT INCIDENCES": "ELEM", "START GROUP DEFINITION": "GROUP",
        "START USER TABLE": "UTABLE", "MEMBER PROPERTY": "PROP",
        "ELEMENT PROPERTY": None, "DEFINE MATERIAL": None, "CONSTANTS": "CONST",
        "SUPPORTS": "SUPP", "MEMBER RELEASE": "REL", "MEMBER TRUSS": "TRUSS",
        "ELEMENT RELEASE": None, "CUT OFF": None,
    }
    for c in _commands(lines):
        up = c.upper()
        if section == "UTABLE":
            if up == "END":
                section = None
            continue
        if up.startswith("END GROUP DEFINITION"):
            section = None
            continue
        hit = next((v for k, v in starts.items() if up.startswith(k)), "nohit")
        if hit != "nohit":
            section = hit
            continue
        m = re.match(r"LOAD (\d+) .*TITLE (.*)", c) or re.match(r"LOAD COMB (\d+) (.*)", c)
        if m:
            load_titles[int(m.group(1))] = " ".join(m.group(2).split())
            section = None
            continue
        if c.startswith("*") or up.startswith("LOAD") or up.startswith("PERFORM"):
            section = None if not c.startswith("*") else section
            continue
        tok = c.split()
        if section == "JOINT":
            for part in c.split(";"):
                p = part.split()
                if len(p) >= 4:
                    joints[int(p[0])] = [float(p[1]), float(p[2]), float(p[3])]
        elif section == "MEMB":
            for part in c.split(";"):
                p = part.split()
                if len(p) >= 3:
                    members[int(p[0])] = [int(p[1]), int(p[2])]
        elif section == "ELEM":
            for part in c.split(";"):
                p = part.split()
                if len(p) >= 4:
                    shells[int(p[0])] = [int(x) for x in p[1:]]
        elif section == "GROUP":
            if up in ("MEMBER", "GEOMETRY", "ELEMENT", "JOINT"):
                kind = up
            elif tok[0].startswith("_"):
                group = tok[0]
                groups[group] = {"kind": kind, "ids": expand(tok[1:])}
            else:
                groups[group]["ids"].extend(expand(tok))
        elif section == "PROP":
            ids, rest = _split_list(tok)
            name = rest[2] if rest and rest[0] in ("TABLE", "UPTABLE") else " ".join(rest)
            if rest and rest[0] == "TABLE":
                ptypes[name] = rest[1]          # ST = sencillo, T = te cortada del perfil, ...
            elif rest and rest[0] == "UPTABLE":
                ptypes[name] = "UPT"
            for i in ids:
                props[i] = name
        elif section == "CONST" and tok[0] == "BETA":
            for i in expand(tok[3:]):
                beta[i] = float(tok[1])
        elif section == "SUPP":
            ids, rest = _split_list(tok)
            for i in ids:
                supports[i] = " ".join(rest)
        elif section == "REL":
            ids, rest = _split_list(tok)
            for i in ids:
                releases.setdefault(i, {})[rest[0]] = rest[1:]
        elif section == "TRUSS":
            truss.update(expand(tok))
    return {
        "meta": meta, "joints": joints, "members": members, "shells": shells,
        "groups": groups, "props": props, "beta": beta, "supports": supports,
        "releases": releases, "truss": truss, "load_titles": load_titles,
        "ptypes": ptypes,
    }


NUM = r"([-+]?[\d.]+(?:E[-+]?\d+)?)"
BLOCK = re.compile(
    r"Member No:\s+(\d+)\s+Profile:\s+\S+\s+(\S+).*?\n"
    r"\|\s+Status:\s+(\w+)\s+Ratio:\s+" + NUM + r"\s+Loadcase:\s+(\d+)\s*\|\n"
    r"\|\s+Location:\s+" + NUM + r"\s+Ref:\s+(.*?)\s*\|\n"
    r"\|\s+Pz:\s+" + NUM + r"\s+([CT ])\s+Vy:\s+" + NUM + r"\s+Vx:\s+" + NUM + r"\s*\|\n"
    r"\|\s+Tz:\s+" + NUM + r"\s+My:\s+" + NUM + r"\s+Mx:\s+" + NUM,
    re.S,
)


def parse_code_check(path):
    with open(path, encoding="latin-1") as fh:
        txt = fh.read()
    res = {}
    for m in BLOCK.finditer(txt):
        g = m.groups()
        res[int(g[0])] = {
            "profile": g[1], "status": g[2], "ratio": float(g[3]), "lc": int(g[4]),
            "loc": float(g[5]), "ref": g[6].strip(), "Pz": float(g[7]), "PzCT": g[8],
            "Vy": float(g[9]), "Vx": float(g[10]), "Tz": float(g[11]),
            "My": float(g[12]), "Mx": float(g[13]),
        }
    return res


TAKEOFF = re.compile(r"^\s+([A-Z]{1,3})\s+(\S+)\s+([\d.]+)\s+([\d.]+)\s*$")


def parse_takeoff(path):
    """STEEL TAKE OFF: [{'type', 'profile', 'length_cm', 'weight_kg'}] y total."""
    with open(path, encoding="latin-1") as fh:
        lines = fh.readlines()
    out, total, inside = [], None, False
    for ln in lines:
        if "STEEL TAKE-OFF" in ln:
            inside, out = True, []
            continue
        if not inside:
            continue
        m = re.search(r"TOTAL =\s+([\d.]+)", ln)
        if m:
            total = float(m.group(1))
            inside = False
            continue
        m = TAKEOFF.match(ln.rstrip("\n"))
        if m:
            out.append({"type": m.group(1), "profile": m.group(2),
                        "length_cm": float(m.group(3)), "weight_kg": float(m.group(4))})
    return out, total
