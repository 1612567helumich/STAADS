# Visor 3D de conexiones · Villahermosa

Visor interactivo para revisar los planos de taller de columnas **SYR-01 … SYR-07**
(GMI, planos S07713000573–579) contra el modelo **STAAD 001_VILLAHERMOSA_SAYER R1.3**.

Muestra la estructura completa del STAAD y, en cada columna, las placas de conexión
modeladas con sus dimensiones reales (chaflanes, muescas, barrenos y oblongos), en la
elevación que indican los planos. Cada conexión se cruza contra las barras STAAD que
llegan a ese nudo.

## Cómo abrirlo

Abre `index.html` en un navegador con internet (three.js se carga de jsDelivr).
Las hojas del PDF están en `planos/` y se abren desde el panel.

- **Columnas**: planta con ejes, marca asignada a cada columna, conexiones por nivel
  (cubierta, mezzanine, fachada, base), barras STAAD con relación de diseño y fuerzas,
  lista de partes y miniaturas del plano.
- **Piezas**: cuántas placas de cada número de parte hay en el edificio y dónde van
  (al tocar una se aísla en el 3D).
- **Revisión**: hallazgos automáticos plano ↔ STAAD y los comandos STAAD para obtener
  fuerzas en extremos.
- **Capas**: armaduras, largueros, fachada, losa, muros, vigas sólidas y la opción de
  ver las vigas en la elevación de los nudos STAAD o alineadas con las placas.

## Supuestos

- El PDF no trae plano de montaje ni cantidades por marca. La ubicación de cada marca
  se dedujo por el patrón de vigas que le llega en STAAD (esquina, borde, interior) y se
  puede cambiar en el panel. Los nombres de eje (1–4, A–C) son de este visor; STAAD no
  los tiene.
- Elevaciones en mm desde el lecho inferior de la placa base (= Y 0 del STAAD).
- La orientación de cada ensamble se elige para que las placas apunten a las vigas
  STAAD. En SYR-04 la orientación en planta de las placas a 412.7 mm no está definida
  en el plano; se tomó de la vista D-D tal cual.
- Los desfases de las placas de cortante y el clip de SYR-03 son aproximados.

## Regenerar

```bash
python3 tools/prep_data.py <001_VILLAHERMOSA_SAYER_R1.3.ANL> data/staad_villahermosa_r1.3.json
python3 tools/build.py
```

`tools/staad_anl.py` lee el eco de datos del `.ANL` (nudos, barras, placas, grupos,
perfiles, BETA, apoyos, liberaciones) y los resultados de `CHECK CODE`.
Las hojas de `planos/` se generaron del PDF a 120 dpi en escala de grises.
