"""Lee tablas de resultados de un .ANL de STAAD (reacciones, desplazamientos,
fuerzas en extremos, frecuencias, participacion)."""
import re
import numpy as np

NUM = re.compile(r'-?\d+\.\d+(?:[Ee][-+]?\d+)?')


def _lines(path):
    with open(path, 'r', encoding='latin-1') as f:
        return f.read().splitlines()


def reactions(path):
    L = _lines(path)
    out = {}
    i = 0
    while i < len(L):
        if 'SUPPORT REACTIONS -UNIT' in L[i]:
            i += 1
            cur = None
            while i < len(L):
                s = L[i]
                if 'END OF LATEST ANALYSIS' in s or 'MEMBER END FORCES' in s or 'JOINT DISPLACEMENT' in s or re.match(r'\s+\d+\. ', s):
                    break
                if 'SUPPORT REACTIONS' in s or 'JOINT  LOAD' in s or '-----' in s or 'PAGE NO' in s or not s.strip():
                    i += 1
                    continue
                head = s[:12]
                nums = NUM.findall(s[12:])
                if len(nums) == 6:
                    h = head.split()
                    if len(h) == 2:
                        cur = int(h[0]); lc = int(h[1])
                    elif len(h) == 1:
                        lc = int(h[0])
                    else:
                        i += 1
                        continue
                    out[(cur, lc)] = np.array([float(v) for v in nums])
                i += 1
            continue
        i += 1
    return out


def displacements(path):
    L = _lines(path)
    out = {}
    i = 0
    while i < len(L):
        if 'JOINT DISPLACEMENT (CM' in L[i]:
            i += 1
            cur = None
            while i < len(L):
                s = L[i]
                if 'END OF LATEST ANALYSIS' in s or 'SUPPORT REACTIONS' in s or 'MEMBER END FORCES' in s or re.match(r'\s+\d+\. ', s):
                    break
                head = s[:12]
                nums = NUM.findall(s[12:])
                if len(nums) == 6 and 'PAGE' not in s:
                    h = head.split()
                    if len(h) == 2:
                        cur = int(h[0]); lc = int(h[1])
                    elif len(h) == 1:
                        lc = int(h[0])
                    else:
                        i += 1
                        continue
                    out[(cur, lc)] = np.array([float(v) for v in nums])
                i += 1
            continue
        i += 1
    return out


def member_forces(path):
    L = _lines(path)
    out = {}
    i = 0
    while i < len(L):
        if 'MEMBER END FORCES' in L[i]:
            i += 1
            cur = None
            lc = None
            while i < len(L):
                s = L[i]
                if 'END OF LATEST ANALYSIS' in s or 'SUPPORT REACTIONS' in s or 'JOINT DISPLACEMENT' in s or re.match(r'\s+\d+\. ', s):
                    break
                head = s[:18]
                nums = NUM.findall(s[18:])
                if len(nums) == 6 and 'PAGE' not in s:
                    h = head.split()
                    if len(h) == 3:
                        cur = int(h[0]); lc = int(h[1]); jt = int(h[2])
                    elif len(h) == 2:
                        lc = int(h[0]); jt = int(h[1])
                    elif len(h) == 1:
                        jt = int(h[0])
                    else:
                        i += 1
                        continue
                    out[(cur, lc, jt)] = np.array([float(v) for v in nums])
                i += 1
            continue
        i += 1
    return out


def frequencies(path):
    L = _lines(path)
    out = {}
    i = 0
    while i < len(L):
        if 'CALCULATED FREQUENCIES FOR LOAD CASE' in L[i]:
            i += 1
            while i < len(L):
                s = L[i]
                m = re.match(r'\s+(\d+)\s+(\d+\.\d+)\s+(\d+\.\d+)\s*$', s)
                if m:
                    out[int(m.group(1))] = (float(m.group(2)), float(m.group(3)))
                elif 'MODAL WEIGHT' in s or 'PARTICIPATION' in s or 'RESPONSE LOAD CASE' in s:
                    break
                i += 1
            if out:
                return out
        i += 1
    return out


def participation(path):
    L = _lines(path)
    out = {}
    i = 0
    seen = False
    while i < len(L):
        if 'MASS  PARTICIPATION FACTORS IN PERCENT' in L[i]:
            seen = True
            i += 1
            while i < len(L):
                s = L[i]
                m = re.match(r'\s+(\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)', s)
                if m:
                    k = int(m.group(1))
                    if k in out:
                        return out
                    out[k] = [float(m.group(j)) for j in range(2, 11)]
                elif 'TOTAL SRSS' in s:
                    return out
                i += 1
        i += 1
    return out
