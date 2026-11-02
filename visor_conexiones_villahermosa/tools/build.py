"""Arma el visor: inserta el JSON del modelo STAAD en la plantilla.

Uso:
    python3 -I build.py                 -> ../index.html (documento completo)
    python3 -I build.py --fragment OUT  -> fragmento sin <html>/<head> (para publicar)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(ROOT, "src", "visor.html")
DATA = os.path.join(ROOT, "data", "staad_villahermosa_r1.3.json")

with open(TEMPLATE, encoding="utf-8") as fh:
    page = fh.read()
with open(DATA, encoding="utf-8") as fh:
    data = fh.read().strip()
if "</" in data:
    raise SystemExit("El JSON contiene '</' y rompería la etiqueta <script>.")
page = page.replace("__STAAD_DATA__", data, 1)

if len(sys.argv) > 2 and sys.argv[1] == "--fragment":
    out = sys.argv[2]
    html = page
else:
    out = os.path.join(ROOT, "index.html")
    html = (
        '<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "</head>\n<body>\n" + page + "\n</body>\n</html>\n"
    )
with open(out, "w", encoding="utf-8") as fh:
    fh.write(html)
print(f"{out}: {len(html) / 1024:.0f} KB")
