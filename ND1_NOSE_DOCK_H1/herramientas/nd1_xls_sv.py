"""Genera la hoja de SISMO y VIENTO del ND1 a partir de la plantilla del usuario
(002_SISMO_VIENTO_SALVADOR_3.2.xlsx de H5-H6).  Se edita el XML interno para
conservar formatos, imagenes y la grafica del espectro, y despues se recalcula
con LibreOffice para dejar al dia los valores guardados de las formulas.

uso: python3 nd1_xls_sv.py PLANTILLA.xlsx resumen.json SALIDA.xlsx"""
import sys, os, json, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from xlsx_xml import Book, Sheet, recalc_and_inject

PROY = 'NOSE DOCK H1 (ND1)'
ORDER = ['A-1', 'C-1', 'A-2', 'C-2', 'A-3', 'B-3', 'C-3']


def main(template, resumen, out):
    S = json.load(open(resumen))
    b = Book(template)
    wb = b.text('xl/workbook.xml')
    wb = re.sub(r'<mc:AlternateContent.*?</mc:AlternateContent>', '', wb, flags=re.S)     # ruta local de la plantilla
    b.put('xl/workbook.xml', wb)

    # ------------------------------------------------------------ CARGAS Y SISMO
    sh = Sheet(b, 'CARGAS Y SISMO F1')
    cfg = S['cfg']
    sheet = S['sheet']
    tips = S['tips']
    sh.set('D3', text=PROY)
    h3 = tips['A-3']['xyz'][1] / 100.0
    h1 = tips['A-1']['xyz'][1] / 100.0
    sh.set('F131', formula='(%s+%s)/2' % (repr(round(h3, 3)), repr(round(h1, 3))))
    rows = sheet['rows']
    domx = sheet['X']['dom']
    sh.set('F137', value=rows[domx - 1]['T'])
    sh.set('E165', value=sheet['W'])
    sh.set('E166', value=sheet['W'])
    # --- peso teorico
    det = {k: tips[k]['detail'] for k in ORDER}
    a_cub = sum(d['area_cub'] for d in det.values())
    a_mur = sum(d['area_muros'] for d in det.values())
    w_door = sum(d.get('w_cortina', 0) + d.get('w_pemerg', 0) for d in det.values())
    sh.set('C156', text='Cubierta')
    sh.set('D156', value=round(a_cub, 2), style='26')
    sh.set('E156', formula='F16', style='26')
    sh.set('F156', value=0, style='26')
    sh.set('G156', formula='D156*(E156+F156)', style='26')
    sh.set('H156', text='  area inclinada (15 x 16 m, pendiente 5.1 %)')
    sh.set('C157', text='Puertas')
    sh.set('G157', value=round(w_door, 2), style='26')
    sh.set('H157', text='  cortina 5.00 x 6.00 m y puerta de emergencia')
    sh.set('C158', text='Muros lamina')
    sh.set('D158', value=round(a_mur, 2), style='26')
    sh.set('E158', formula='H16', style='26')
    sh.set('F158', value=0, style='26')
    sh.set('G158', formula='D158*(E158+F158)', style='26')
    sh.set('H158', text='  muros A, C y 3 mas faldon del eje 1, descontando puertas')
    sh.set('G160', value=round(S['weight'], 2), style='26')
    sh.set('H160', text='  STEEL TAKE-OFF del modelo (calculo previo)')
    # --- tabla modal (primeros 43 modos, con el formato con que los imprime STAAD)
    for i, r in enumerate(rows):
        n = 177 + i
        sh.set('C%d' % n, value=r['f'])
        sh.set('D%d' % n, value=r['T'])
        sh.set('E%d' % n, value=r['px'])
        sh.set('F%d' % n, value=0)
        sh.set('G%d' % n, value=r['pz'])
    # --- reacciones de los casos de espectro: misma disposicion de la plantilla
    #     (tabla pegada en T:AA con la suma de Fx en V283); se agrega la del sismo Z
    for r in range(186, 284):
        for col in ('T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'AA'):
            sh.clear('%s%d' % (col, r))
    sup = sorted(int(n) for n in S['reactions'])
    sh.set('T186', text='REACCIONES DEL MODELO ND1 R1.1 (CALCULO PREVIO; SUSTITUIR POR LAS DEL ANL DE STAAD)', style='1')

    def colname(n):
        s_ = ''
        while n:
            n, rr = divmod(n - 1, 26)
            s_ = chr(65 + rr) + s_
        return s_
    for c0, lc, title in ((20, '4', '4 SISMO X'), (29, '5', '5 SISMO Z')):
        col = lambda k: colname(c0 + k)
        for k, t in enumerate(['', '', 'Horizontal', 'Vertical', 'Horizontal', 'Moment', '', '']):
            if t:
                sh.set('%s188' % col(k), text=t)
        for k, t in enumerate(['Node', 'L/C', 'Fx Mton', 'Fy Mton', 'Fz Mton', 'Mx MTon-m', 'My MTon-m', 'Mz MTon-m']):
            sh.set('%s189' % col(k), text=t)
        for i, n in enumerate(sup):
            rr = 190 + i
            v = S['reactions'][str(n)][lc]
            sh.set('%s%d' % (col(0), rr), value=n)
            sh.set('%s%d' % (col(1), rr), text=title)
            for k in range(3):
                sh.set('%s%d' % (col(2 + k), rr), value=round(v[k] / 1000.0, 4))
            for k in range(3):
                sh.set('%s%d' % (col(5 + k), rr), value=round(v[3 + k] / 1e5, 4))
    sh.set('U283', text='Suma Fx =')
    sh.set('V283', formula='SUM(V190:V281)')
    sh.set('AF283', text='Suma Fz =')
    sh.set('AG283', formula='SUM(AG190:AG281)')
    # las sumas de la plantilla apuntaban a columnas de una disposicion anterior
    sh.set('O177', formula='ABS(V283)')
    sh.set('O178', formula='ABS(AG283)')
    sh.commit()

    # ------------------------------------------------------------ VIENTO
    sv = Sheet(b, 'VIENTO NTDV-97')
    sv.set('D4', text=PROY)
    sv.set('D49', value=round(0.5 * (h3 + h1), 3))
    nie = 9.36
    sv.set('F86', text='Area de aberturas en el frente (eje 1, de N.P.T. a N.I.E.) = ')
    sv.set('G86', formula='15*%s' % repr(nie))
    sv.set('G88', formula='15*%s' % repr(round(h1, 3)))
    sv.set('G94', text='Eje 1 abierto')
    sv.set('B106', text='Muro C (Eje C)')
    sv.set('E106', text='X = 1500')
    sv.set('B107', text='Muro 3 (Eje 3)')
    sv.set('B108', text='Eje 1 (faldon N.I.E. a cubierta)')
    sv.set('F108', text='SI')
    sv.set('H108', text='GZ INCLINED TOWARDS %d' % S['towards'])
    # --- bloque nuevo: cargas lineales adicionales
    r0 = 191
    sv.set('B%d' % r0, text='5) CARGAS ADICIONALES EN BARRAS (MEMBER LOAD, kg/cm): FRANJA INFERIOR DE MUROS Y VIENTO SOBRE PUERTAS', style='1')
    sv.set('B%d' % (r0 + 1), text='La lamina bajo el primer larguero (+0.60) y las puertas no forman tableros ONEWAY: su viento se aplica como '
                                  'carga lineal = presion STAAD (seccion 2 o 3) x ancho tributario.')
    sv.set('B%d' % (r0 + 14), text='Columnas: larguero inferior (+0.60) de los muros A, C y 3; postes de la cortina; postes de la puerta de emergencia.')
    hdr = ['Caso', None, 'Muro A (GX)', 'Muro C (GX)', 'Muro 3 (GZ)', 'Cortina (GZ)', 'P.Emerg. (GX)']
    cols = ['B', 'C', 'D', 'E', 'F', 'G', 'H']
    for cc, t in zip(cols, hdr):
        if t:
            sv.set('%s%d' % (cc, r0 + 2), text=t, style='27')
    sv.set('C%d' % (r0 + 2), style='27')
    sv.set('B%d' % (r0 + 3), text='Ancho tributario (cm)', style='16')
    sv.set('C%d' % (r0 + 3), style='15')
    we = S['wind']
    widths = [we['strip'], we['strip'], we['strip'], we['door_w'], we['edoor_w']]
    for cc, w in zip(cols[2:], widths):
        sv.set('%s%d' % (cc, r0 + 3), value=w, style='36')
    # filas de presion STAAD por caso: (OESTE, ESTE, NORTE)
    href = {8: (116, 117, 118), 9: (124, 125, 126), 10: (132, 133, 134), 11: (140, 141, 142),
            12: (151, 152, 153), 13: (159, 160, 161), 14: (167, 168, 169), 15: (175, 176, 177)}
    names = {8: 'VIENTO X', 9: 'VIENTO -X', 10: 'VIENTO Z', 11: 'VIENTO -Z', 12: 'VIENTO X PA', 13: 'VIENTO -X PA',
             14: 'VIENTO Z PA', 15: 'VIENTO -Z PA'}
    wr = r0 + 3
    for i, lc in enumerate(range(8, 16)):
        rr = r0 + 4 + i
        o, e, n = href[lc]
        sv.set('B%d' % rr, text='LOAD %d  %s' % (lc, names[lc]), style='16')
        sv.set('C%d' % rr, style='15')
        sv.set('D%d' % rr, formula='H%d*D$%d' % (o, wr), style='121')
        sv.set('E%d' % rr, formula='H%d*E$%d' % (e, wr), style='121')
        sv.set('F%d' % rr, formula='H%d*F$%d' % (n, wr), style='121')
        sv.set('G%d' % rr, formula='H%d*G$%d' % (n, wr), style='121')
        sv.set('H%d' % rr, formula='H%d*H$%d' % (o, wr), style='121')
    rr = r0 + 15
    low = we.get('low_members', {})
    sv.set('B%d' % rr, text='Barras cargadas en el STD R1.1: larguero inferior muro A %s, muro C %s, muro 3 %s; postes de cortina %s; '
                            'postes de puerta de emergencia %s.' % (low.get('_OESTE', ''), low.get('_ESTE', ''), low.get('_NORTE', ''),
                                                                   low.get('pc', ''), low.get('pe', '')))
    sv.set('B%d' % (rr + 1), text='En el caso 13 el muro A (sotavento) tiene presion neta 0, por eso no lleva carga en franja ni en puerta de emergencia.')
    sv.commit()

    b.force_recalc()
    n = recalc_and_inject(b, out)
    print('formulas actualizadas:', n)


if __name__ == '__main__':
    main(*sys.argv[1:4])
