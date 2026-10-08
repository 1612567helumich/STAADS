# Resumen para continuar — NOSE DOCK H5-H6, modelo 002 (rev. 3.0)

Repo `1612567helumich/STAADS`, rama `claude/vibrant-turing-wx2gs8`, carpeta `002/`. No abrir PR salvo que se pida.
Responder en español, conciso; el usuario quiere rapidez.

## Reglas del usuario (no negociables)
- STAAD **sin comentarios** (`*`). Cada nodo/miembro completo en su renglón (STAAD rechaza registros partidos con `-` en JOINT COORDINATES / MEMBER INCIDENCES); renglones ≤ 79 car.
- Excel: **no cambiar formato**; en la hoja de sismo solo agregar filas/columnas, **sin pestañas nuevas**.
- Geometría: ejes 1-2-3 en Z = 0 / 8 / 16 m (claros 8 + 8), ancho X = 10.08 m; alero Y = 10.43 / 10.01501 / 9.60002 m. 10 largueros de techo @1.333 m.
- Eje 3 empotrado, bases 1-6 **FIXED** (sin soltar eje débil). **Un solo tipo de IR** en columnas. Peraltes pares, continuidad, modelo uniforme.
- Remates donde terminan contraflambeos: **cajón MCC**. Largueros de muro @**1.20 m** (0.60 y luego @1.20 hasta 9.00, más 9.45 en claro 1-2).
- Tensores de muros A/B (845-852) anclados en el **larguero de 0.60 m** (NO en la base).
- Criterios: L/180; distorsión **0.015 con Cd = 6** (el usuario la revisa como Δ ≤ 0.015·h/6 con los desplazamientos de las comb. 16-23).
- Cargas: CM techo **19.32**, CM muros **5.85**, CV **20** kg/m²; cortina 12 kg/m² × 5.10 × 6.50 = 397.8 kg (½ en nodos 69 y 70).
- Masa sísmica (caso 4) concentrada en cabezas: techo 19.32 × área tributaria; muros A/B de 0.30 m al alero con ½ de cada claro; **muro 1 partido con línea vertical en X = 5.04 m** (cada mitad con sus vanos) a nodos 7 y 8; ½ cortina en cada jamba. Resultado: 7 = 1006.45, 8 = 1033.96, 75/76 = 1233.64, 9/10 = 609.54 kg.
- Viento NTDV-97 con presión interna (eje 3 abierto, Cpi), hoja `VIENTO NTDV-97`; cargas en STAAD a 2 decimales.
- Factores del espectro: los de la hoja `CARGAS Y SISMO F1` (K239/L239) con los **modos y DYNAMIC WEIGHT del .ANL** del usuario; CUT OFF 43.
- Desglose: formato FPRIN, revisión **1.0**, campos FPRIN en blanco, render 3D en portada, conexiones 5 %, densidad sobre 161.28 m².
- Commits terminan con: `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` y `Claude-Session: https://claude.ai/code/session_01DbpSpoM7qi5cJ9LMKpwgVv`.

## Estado: opción #1 = rev. 3.0 (TERMINADA y confirmada con el .ANL del usuario)
- Columnas W14X22 todas, `FYLD 3515 MEMB` (grado 50) solo columnas. Vigas de marco y alero MCE12-14. Largueros techo MC12-14. Muros A/B MC10-14; muro 1: 39/581-584 MC10-12, resto MC10-14 y MC4-14 cortos; remates/dintel MCC10-14. CF techo PIPS7, CF muros PIPS5, tensores Ø1/2" (Ø5/8" muro 1), cortina HSST6X6X0.125, puerta HSST2X2X0.125.
- 6,673.62 kg → **43.45 kg/m²** con 5 %. STAAD: 0 errores, 0 FAIL, ratio máx. 0.933 (largueros muro claro 2-3), Δ eje 3 = 2.252 cm vs 2.40 permitido (0.938). W dinámico 12,330.62 kg, T1 0.6167 s. Factores X **1.0979**, Z **1.0218** (ya en el STD).
- Grupos STD: `_COLUMNAS_EJES_1_Y_3`, `_COLUMNAS_EJE_2`, `_LARGUEROS_AB_C12`, `_LARGUEROS_AB_C23`.
- Archivos en `002/`: `002_NOSE_DOCK_H5_H6_3.0.STD`, `002_SISMO_VIENTO_SALVADOR_3.0.xlsx`, `002_AreasTributarias_NOSE_DOCK_H5_H6_3.0.xlsx`, `002_ATRIBUTARIA_NOSE_DOCK_H5_H6_3.0.dxf`, `002_DESTRUCTURAL_H5H6_3.0.docx/.pdf`, `002_REACCIONES_BASES_3.0.xlsx`.

## Pendiente: opción #3 (nombre propuesto rev. 3.1)
- Igual a la 3.0 pero con viento **sin presión interna** (solo Cpe, como el modelo de referencia "panzón" H2-H3), asumiendo eje 3 cerrado o criterio aceptado por el jefe. Advertirlo: con eje 3 realmente abierto no pasaría.
- Estimación previa (antes de los últimos ajustes): ~41.0 kg/m² con bases empotradas, W14X22, VM y VA MCE10-14, muros claro 1-2 MC8-14, claro 2-3 y muro 1 MC10-14, remates MCC10-14, cortina HSST4X4X0.125. **Hay que recalcularla** con los criterios actuales (tensores en 0.60 m, masas del muro 1 partido, FYLD 3515) y entregar el mismo paquete de 7 archivos.
- Si se separa viento sin Cpi: windward 0.8·P, sotavento 0.5·P, laterales y techo 0.7·P, con P = 48.58 kg/m².

## Referencia "panzón" (MODELO_NOSE_DOCK-H2-H3)
232 m², armaduras (el usuario usa vigas, no cambiar), columnas W12X30 con FYLD 3515, bases empotradas, viento sin presión interna (~34 kg/m²), 39.83 kg/m² con 5 %.

## Ojo
- El motor de cálculo propio (FE + AISC 360-16, calibrado contra STAAD; ratios iguales a ±0.001) y los scripts de generación vivían en el scratchpad de la sesión anterior, **no están en el repo**. Para recalcular hay que reconstruirlos o pedir que se suban.
- La hoja de sismo se edita a nivel XML (sin re-guardar con openpyxl) para no tocar formato; el Excel de áreas se edita con LibreOffice (UNO).
