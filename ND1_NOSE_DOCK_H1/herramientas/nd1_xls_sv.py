"""Genera la hoja de SISMO y VIENTO del ND1 a partir de la plantilla del usuario
(002_SISMO_VIENTO_SALVADOR_3.2.xlsx de H5-H6).  Solo se actualizan las celdas
que ya existen en la plantilla (mismo formato, sin tablas ni bloques nuevos).
Se edita el XML interno para conservar formatos, imagenes y la grafica del
espectro, y despues se recalcula con LibreOffice para dejar al dia los valores
guardados de las formulas.

uso: python3 nd1_xls_sv.py PLANTILLA.xlsx resumen.json SALIDA.xlsx"""
import sys, os, json, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from xlsx_xml import Book, Sheet, recalc_and_inject

PROY = 'NOSE DOCK H1'


def main(template, resumen, out):
    S = json.load(open(resumen))
    b = Book(template)
    wb = b.text('xl/workbook.xml')
    wb = re.sub(r'<mc:AlternateContent.*?</mc:AlternateContent>', '', wb, flags=re.S)     # ruta local de la plantilla
    b.put('xl/workbook.xml', wb)

    # ------------------------------------------------------------ CARGAS Y SISMO
    sh = Sheet(b, 'CARGAS Y SISMO F1')
    sheet = S['sheet']
    tips = S['tips']
    proy = S.get('proy', PROY)
    sh.set('D3', text=proy)
    h3 = tips['A-3']['xyz'][1] / 100.0
    h1 = tips['A-1']['xyz'][1] / 100.0
    sh.set('F131', formula='(%s+%s)/2' % (repr(round(h3, 3)), repr(round(h1, 3))))
    rows = sheet['rows']
    domx = sheet['X']['dom']
    sh.set('F137', value=rows[domx - 1]['T'])
    sh.set('E165', value=sheet['W'])
    sh.set('E166', value=sheet['W'])
    # --- tabla modal (primeros 43 modos, con el formato con que los imprime STAAD)
    for i, r in enumerate(rows):
        n = 177 + i
        sh.set('C%d' % n, value=r['f'])
        sh.set('D%d' % n, value=r['T'])
        sh.set('E%d' % n, value=r['px'])
        sh.set('F%d' % n, value=0)
        sh.set('G%d' % n, value=r['pz'])
    # --- reacciones del caso 4 SISMO X: misma tabla pegada de la plantilla (T:AA,
    #     encabezados en 188-189 y suma de Fx en V283); se sustituyen sus renglones
    for r in range(190, 282):
        for col in ('T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'AA'):
            sh.clear('%s%d' % (col, r))
    sup = sorted(int(n) for n in S['reactions'])
    for i, n in enumerate(sup):
        rr = 190 + i
        v = S['reactions'][str(n)]['4']
        sh.set('T%d' % rr, value=n)
        sh.set('U%d' % rr, text='4 SISMO X')
        for k, col in enumerate(('V', 'W', 'X')):
            sh.set('%s%d' % (col, rr), value=round(v[k] / 1000.0, 3))
        for k, col in enumerate(('Y', 'Z', 'AA')):
            sh.set('%s%d' % (col, rr), value=round(v[3 + k] / 1e5, 3))
    sh.commit()

    # ------------------------------------------------------------ VIENTO
    sv = Sheet(b, 'VIENTO NTDV-97')
    sv.set('D4', text=proy)
    sv.set('D49', value=round(0.5 * (h3 + h1), 3))
    sv.set('G86', formula='15*%s' % repr(round(S.get('nie', 9.36), 3)))      # abertura del frente: ancho x N.I.E.
    sv.set('G88', value=round(15 * h1, 3))                # fachada del frente: ancho x altura en eje 1
    sv.set('G94', text='Eje 1 abierto')
    sv.set('B106', text='Muro C (Eje C)')
    sv.set('E106', text='X = 1500')
    sv.set('B107', text='Muro 3 (Eje 3)')
    sv.set('B108', text='Eje 1 (faldón)')
    sv.set('F108', text='SI')
    sv.set('H108', text='GZ INCLINED' + ((' TOWARDS %d' % S['towards']) if S.get('towards') else ''))
    sv.commit()

    b.force_recalc()
    n = recalc_and_inject(b, out)
    print('formulas actualizadas:', n)


if __name__ == '__main__':
    main(*sys.argv[1:4])
