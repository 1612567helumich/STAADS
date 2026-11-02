"""Build the compact data file used by the 3D viewer.

Reads the STAAD.Pro output file (.ANL), takes the echoed input (joints,
members, plates, groups, properties, releases, supports) and the
CHECK CODE results, and writes one JSON file for the viewer.

Usage:
    python3 -I prep_data.py <archivo.ANL> <salida.json>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from staad_anl import parse_input, parse_code_check  # noqa: E402

src, out = sys.argv[1], sys.argv[2]
model = parse_input(src)
check = parse_code_check(src)

J = model["joints"]
M = model["members"]
P = model["props"]
G = model["groups"]
SH = model["shells"]

member_groups = {}
for g, d in G.items():
    if d["kind"] == "MEMBER":
        for i in d["ids"]:
            member_groups.setdefault(i, g)  # first group wins (display colour)
shell_groups = {}
for g, d in G.items():
    if d["kind"] == "ELEMENT":
        for i in d["ids"]:
            shell_groups[i] = g

sections = sorted(set(P.values()))
groups = sorted(set(member_groups.values()) | set(shell_groups.values())) + ["(sin grupo)"]
sec_idx = {s: k for k, s in enumerate(sections)}
grp_idx = {g: k for k, g in enumerate(groups)}

used = set()
for a, b in M.values():
    used.update((a, b))
for nodes in SH.values():
    used.update(nodes)

def r(v):
    return round(v, 3)

joints = {str(k): [r(v[0]), r(v[1]), r(v[2])] for k, v in J.items() if k in used}

members = {}
for i, (a, b) in M.items():
    rel = model["releases"].get(i, {})
    members[str(i)] = [
        a,
        b,
        sec_idx[P[i]],
        grp_idx[member_groups.get(i, "(sin grupo)")],
        model["beta"].get(i, 0),
        1 if i in model["truss"] else 0,
        " ".join(rel.get("START", [])),
        " ".join(rel.get("END", [])),
    ]

shells = [[e] + nodes + [grp_idx[shell_groups.get(e, "(sin grupo)")]] for e, nodes in SH.items()]

chk = {}
for i, c in check.items():
    pz = c["Pz"] * (-1 if c["PzCT"] == "C" else 1)  # + tension, - compression
    chk[str(i)] = [
        c["status"][0],
        c["ratio"],
        c["lc"],
        c["loc"],
        c["ref"],
        round(pz, 1),
        round(c["Vy"], 1),
        round(c["Vx"], 1),
        round(c["Tz"], 1),
        round(c["My"], 1),
        round(c["Mx"], 1),
    ]

data = {
    "meta": model["meta"],
    "sections": sections,
    "groups": groups,
    "joints": joints,
    "members": members,
    "shells": shells,
    "supports": {str(k): v for k, v in model["supports"].items()},
    "check": chk,
    "loads": model["load_titles"],
}
with open(out, "w") as fh:
    json.dump(data, fh, separators=(",", ":"))
print(f"joints {len(joints)}  members {len(members)}  shells {len(shells)}  check {len(chk)}")
print("sections", sections)
print("groups", groups)
