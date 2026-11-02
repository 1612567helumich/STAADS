# Visor 3D de conexiones · Villahermosa

Visor interactivo para revisar los planos de taller de columnas **SYR-01 … SYR-07**
(GMI, planos S07713000573–579) contra el modelo **STAAD 001_VILLAHERMOSA_SAYER R1.3**.

Muestra la estructura completa del STAAD con el perfil real de cada barra y, en cada
columna, las placas de conexión modeladas con sus dimensiones reales (chaflanes,
muescas, barrenos y oblongos), en la elevación que indican los planos. Cada conexión se
cruza contra las barras STAAD que llegan a ese nudo.

## Cómo abrirlo

| Archivo | Cuándo usarlo |
| --- | --- |
| `index_offline.html` | Doble clic y listo. Funciona **sin internet** (three.js va dentro del archivo). |
| `index.html` | Igual, pero descarga three.js de jsDelivr: necesita internet. |

Las hojas del PDF están en `planos/` y se abren desde el panel; deja esa carpeta junto
al HTML.

Navegación tipo CAD: arrastrar con el botón izquierdo gira; con la rueda presionada (o
el botón derecho) mueve el modelo; girar la rueda acerca o aleja hacia el cursor;
Shift + rueda presionada gira. En pantallas táctiles: un dedo gira y dos dedos mueven y
hacen zoom.

Arriba, **Barras** cambia entre:

- **Perfiles 3D**: cada barra extruida con la forma de su sección (HSS, Monten espalda con
  espalda, cajón, IR, T, Z, top hat, poste C, tubo, diagonal C), orientada con los ejes
  locales del STAAD y su BETA, con un color por perfil.
- **Líneas**: el modelo analítico, una línea por barra con el color de su perfil.

Pestañas del panel:

- **Columnas**: planta con ejes, marca asignada a cada columna, conexiones por nivel
  (cubierta, mezzanine, fachada, base), barras STAAD con relación de diseño y fuerzas,
  lista de partes y miniaturas del plano.
- **Piezas**: cuántas placas de cada número de parte hay en el edificio y dónde van.
  Tocar una lleva a la primera; «Todas» las resalta juntas en el edificio.
- **Revisión**: hallazgos automáticos plano ↔ STAAD y los comandos STAAD para obtener
  fuerzas en extremos.
- **Capas**: armaduras, largueros, fachada, losa, muros, alineación de niveles y la
  tabla **Perfiles del STAAD** (corte de cada sección, número de barras, longitud y peso
  del STEEL TAKE OFF); tocar un perfil lo aísla en el 3D.

Al pasar el cursor sobre una barra se ve su perfil, dimensiones, BETA, grupo, longitud y
relación de diseño; con un clic aparece además el corte de la sección.

### Seleccionar una pieza

Al tocar una placa en el 3D, una fila de **Piezas**, una fila de la lista de partes o
**Ver placa** en una conexión:

- la cámara vuela a esa pieza;
- la pieza queda resaltada, sus aledañas (la misma conexión y la columna) en color, la
  barra STAAD que recibe en azul y todo lo demás en gris;
- aparecen las cotas de la pieza y globos con el número de ítem del plano;
- el inspector muestra medidas, espesor, material, barrenos, peso (plano y calculado con
  la forma modelada), soldadura según el detalle, la barra STAAD con sus fuerzas en el
  nudo y una revisión rápida (AISC 360-16, LRFD) para placas de patín y de cortante.

`‹ ›` o las flechas del teclado recorren todas las piezas iguales del edificio; `Esc`
o `×` regresan a la vista completa.

La revisión rápida es una referencia: usa las fuerzas del CHECK CODE en el nudo (una
combinación, no la envolvente), placas A-36, HSS con espesor de diseño 0.93 t y el Fy
que elijas (el del STAAD, A500 Gr. B o Gr. C). No revisa tornillos porque los planos
no los especifican.

## Llevarlo a otra sesión o a otra computadora

El paquete `.zip` trae esta carpeta completa más `fuentes/` con el PDF de conexiones y
el `.ANL` originales.

- **Solo verlo**: descomprime y abre `index_offline.html`.
- **Seguir trabajándolo con Claude**: sube el `.zip` a la nueva sesión (o clona la rama
  `claude/dreamy-bardeen-4o6zgi` del repo) y pide que lo descomprima. Este README y
  `src/visor.html` bastan para retomar: todo el visor está en esa plantilla y los datos
  salen de `fuentes/` con los comandos de abajo.
- La asignación de marcas que cambies en el panel se guarda solo en ese navegador.

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
- Las formas de las placas reproducen el peso de cada plano de pieza dentro de ~1 %
  (2 % en el ángulo doblado de SYR-03).
- Secciones: peralte y ancho salen de las tablas de usuario del STAAD (o de AISC para
  TUB60604, W8X10, W16X36 y PIPS5) y el espesor del calibre. Las pestañas de los Monten y
  postes son aproximadas. Los perfiles C y Z del STAAD son secciones GENERAL, que no dicen
  hacia qué lado abren los patines; se dibujan con un lado fijo.
- «Alinear niveles con los planos» sube o baja los nudos de 20, 327 y 604 cm a las
  elevaciones de los planos para que las vigas asienten en las placas. Apagado muestra
  los nudos tal cual el STAAD. En modo Líneas siempre se ven los nudos del STAAD.

## Regenerar

```bash
python3 tools/prep_data.py fuentes/001_VILLAHERMOSA_SAYER_R1.3.ANL data/staad_villahermosa_r1.3.json
python3 tools/build.py            # index.html
python3 tools/build.py --offline  # index_offline.html
```

`tools/staad_anl.py` lee el eco de datos del `.ANL` (nudos, barras, placas, grupos,
perfiles, BETA, apoyos, liberaciones), los resultados de `CHECK CODE` y el `STEEL TAKE
OFF`. Las hojas de `planos/` se generaron del PDF a 120 dpi en escala de grises.
`vendor/three-0.160.0/` trae three.js (licencia MIT) para la versión sin internet.
