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
    rows = [
        ('W12X26', to['W12X26']['W']),                 # R6
        ('MCE10-14', to['MCE10-14']['W']),             # R7
        ('MCE6-14', to['MCE6-14']['W']),               # R8
        ('MCE4-14', to['MCE4-14']['W']),               # R9
        ('C-14', to['C-14']['W']),                     # R10
        ('2-14', to['2-14']['W']),                     # R11
        ('MC10-14 CUBIERTA', tg['LC']),                # R12
        ('MC10-14 MUROS', tg['LM']),                   # R13
        ('MCC10-14', to['MCC10-14']['W']),             # R14
        ('MC4-14', to['MC4-14']['W']),                 # R15
        ('PTR4-14', to['PTR4-14']['W']),               # R16
        (pc, to[pc]['W']),                             # R17
        ('PIPS7 CUBIERTA', tg['CFC']),                 # R18
        ('PIPS7 MUROS', tg['CF']),                     # R19
        ('REDONDOS CUBIERTA', tg['TC']),               # R20
        ('REDONDOS MUROS', tg['TM']),                  # R21
    ]
    assert abs(sum(w for _, w in rows) - S['weight']) < 0.5, (sum(w for _, w in rows), S['weight'])
    s_q, s_r = copy.copy(ws['Q6']._style), copy.copy(ws['R6']._style)
    s_tot_q, s_tot_r = copy.copy(ws['Q18']._style), copy.copy(ws['R18']._style)
    s_sum_q, s_sum_r = copy.copy(ws['Q21']._style), copy.copy(ws['R21']._style)
    s_blank = copy.copy(ws['Q19']._style)
    for r in range(6, 26):                      # limpia la tabla anterior
        for col in (17, 18):
            c = ws.cell(r, col)
            c.value = None
            c._style = copy.copy(s_blank)
    for i, (name, w) in enumerate(rows):
        r = 6 + i
        ws.cell(r, 17, name)._style = copy.copy(s_q)
        ws.cell(r, 18, round(w, 3))._style = copy.copy(s_r)
    rt = 6 + len(rows)                          # 22
    ws.cell(rt, 17, 'TOTAL=')._style = s_tot_q
    ws.cell(rt, 18, '=SUM(R6:R%d)' % (rt - 1))._style = s_tot_r
    ws.cell(rt + 3, 17, 'SUMA TOTAL DE ELEMENTOS=')._style = s_sum_q
    ws.cell(rt + 3, 18, '=SUM(E12,E27,E42)')._style = s_sum_r
    # ------------------------------------------------ columnas
    ws['C7'] = 'W12×26'
    ws['E7'] = '=R6'
    ws['C8'] = hss_txt(pc)
    ws['E8'] = '=R17'
    ws['C9'] = 'PTR 4×4 Cal. 14'
    ws['E9'] = '=R16'
    ws['E15'] = '=15*16'
    # ------------------------------------------------ cubierta (largueros, vigas de borde y armaduras)
    ws['E22'] = '=R7+R8+R9+R10+R11+R12'
    ws['E23'] = '=R18'
    ws['E24'] = '=R20'
    # ------------------------------------------------ largueros de muro
    ws['E37'] = '=R13+R14+R15'
    ws['E38'] = '=R19'
    ws['C39'] = 'Redondo Liso Ø= 1/2"(MUROS LATERAL)'
    ws['E39'] = '=R21'
    tmp = out + '.tmp.xlsx'
    wb.save(tmp)
    b = Book(tmp)
    b.force_recalc()
    n = recalc_and_inject(b, out)
    os.remove(tmp)
    print('formulas actualizadas:', n)


if __name__ == '__main__':
    main(*sys.argv[1:4])
