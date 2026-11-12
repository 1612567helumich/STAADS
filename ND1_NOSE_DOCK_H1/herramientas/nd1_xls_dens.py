"""Genera la hoja de DENSIDAD del ND1 sobre la plantilla del usuario
(002_DENSIDAD_NOSE_DOCK_H5H6_3.2.2.xlsx).  Mismo formato y mismos bloques que
la plantilla: solo cambian los perfiles y pesos de la cuantificacion.

uso: python3 nd1_xls_dens.py PLANTILLA.xlsx resumen.json SALIDA.xlsx"""
import sys, os, json, copy, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import openpyxl
from xlsx_xml import Book, recalc_and_inject


def hss_txt(name):
    """'HSST6X6X0.25' -> 'HSS 6"×6"×1/4"' (texto de la plantilla)."""
    m = re.match(r'HSST(\d+)X(\d+)X([\d.]+)$', name)
    fr = {'0.125': '1/8', '0.188': '3/16', '0.25': '1/4', '0.313': '5/16', '0.375': '3/8', '0.5': '1/2'}
    return 'HSS %s"×%s"×%s"' % (m.group(1), m.group(2), fr[m.group(3)])


def main(template, resumen, out):
    S = json.load(open(resumen))
    to = S['takeoff']
    tg = S['takeoff_tag']
    pc = S['sections'].get('PC', 'HSST4X4X0.25')     # postes de cortina
    wb = openpyxl.load_workbook(template)
    ws = wb.active
    # ------------------------------------------------ tabla PROFILE / WEIGHT (Q:R)
    # (nombre, peso, bloque): col = columnas, roof = cubierta, wall = muros; los demas van a su propia celda
    mce_wall = S['sections'].get('LST')          # larguero de cubierta del eje 3 en MCE (CF_BELOW_TOP)
    w_lst = tg.get('LST', 0.0) if mce_wall else 0.0
    vr_sec = S['sections'].get('VR', 'MCE10-14')
    rows = [('W12X26', to['W12X26']['W'], 'col')]
    if mce_wall == vr_sec:
        rows.append((vr_sec + ' CUBIERTA', to[vr_sec]['W'] - w_lst, 'roof'))
    else:
        rows.append((vr_sec, to[vr_sec]['W'], 'roof'))
    rows += [
        ('MCE6-14', to['MCE6-14']['W'], 'roof'),
        ('MCE4-14', to['MCE4-14']['W'], 'roof'),
        ('C-14', to['C-14']['W'], 'roof'),
        ('2-14', to['2-14']['W'], 'roof'),
        ('MC10-14 CUBIERTA', tg['LC'], 'roof'),
        ('MC10-14 MUROS', to['MC10-14']['W'] - tg['LC'], 'wall'),   # todos los MC10-14 que no son de cubierta
    ]
    if mce_wall:
        rows.append((mce_wall + ' MUROS', w_lst, 'wall'))
    rows += [
        ('MCC10-14', to['MCC10-14']['W'], 'wall'),
        ('MC4-14', to['MC4-14']['W'], 'wall'),
        ('PTR4-14', to['PTR4-14']['W'], 'ptr'),
        (pc, to[pc]['W'], 'hss'),                                   # postes de cortina
        ('PIPS7 CUBIERTA', tg['CFC'], 'pips_roof'),
        ('PIPS7 MUROS', tg['CF'], 'pips_wall'),
        ('REDONDOS CUBIERTA', tg['TC'], 'rod_roof'),
        ('REDONDOS MUROS', tg['TM'], 'rod_wall'),
    ]
    assert abs(sum(w for _, w, _ in rows) - S['weight']) < 0.5, (sum(w for _, w, _ in rows), S['weight'])
    s_q, s_r = copy.copy(ws['Q6']._style), copy.copy(ws['R6']._style)
    s_tot_q, s_tot_r = copy.copy(ws['Q18']._style), copy.copy(ws['R18']._style)
    s_sum_q, s_sum_r = copy.copy(ws['Q21']._style), copy.copy(ws['R21']._style)
    s_blank = copy.copy(ws['Q19']._style)
    rt = 6 + len(rows)                          # fila del TOTAL
    for r in range(6, rt + 4):                  # limpia la tabla anterior
        for col in (17, 18):
            c = ws.cell(r, col)
            c.value = None
            c._style = copy.copy(s_blank)
    where = {}
    for i, (name, w, blk) in enumerate(rows):
        r = 6 + i
        ws.cell(r, 17, name)._style = copy.copy(s_q)
        ws.cell(r, 18, round(w, 3))._style = copy.copy(s_r)
        where.setdefault(blk, []).append('R%d' % r)
    ws.cell(rt, 17, 'TOTAL=')._style = s_tot_q
    ws.cell(rt, 18, '=SUM(R6:R%d)' % (rt - 1))._style = s_tot_r
    ws.cell(rt + 3, 17, 'SUMA TOTAL DE ELEMENTOS=')._style = s_sum_q
    ws.cell(rt + 3, 18, '=SUM(E12,E27,E42)')._style = s_sum_r
    # ------------------------------------------------ columnas
    ws['C7'] = 'W12×26'
    ws['E7'] = '=' + where['col'][0]
    ws['C8'] = hss_txt(pc)
    ws['E8'] = '=' + where['hss'][0]
    ws['C9'] = 'PTR 4×4 Cal. 14'
    ws['E9'] = '=' + where['ptr'][0]
    ws['E15'] = '=15*16'
    # ------------------------------------------------ cubierta (largueros, vigas de borde y armaduras)
    ws['E22'] = '=' + '+'.join(where['roof'])
    ws['E23'] = '=' + where['pips_roof'][0]
    ws['E24'] = '=' + where['rod_roof'][0]
    # ------------------------------------------------ largueros de muro
    ws['E37'] = '=' + '+'.join(where['wall'])
    ws['E38'] = '=' + where['pips_wall'][0]
    ws['C39'] = 'Redondo Liso Ø= 1/2"(MUROS LATERAL)'
    ws['E39'] = '=' + where['rod_wall'][0]
    tmp = out + '.tmp.xlsx'
    wb.save(tmp)
    b = Book(tmp)
    b.force_recalc()
    n = recalc_and_inject(b, out)
    os.remove(tmp)
    print('formulas actualizadas:', n)


if __name__ == '__main__':
    main(*sys.argv[1:4])
