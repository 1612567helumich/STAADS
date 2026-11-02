"""Arma el visor: inserta el JSON del modelo STAAD en la plantilla.

Uso:
    python3 -I build.py                 -> ../index.html (three.js desde jsDelivr, requiere internet)
    python3 -I build.py --offline       -> ../index_offline.html (three.js embebido, sin internet)
    python3 -I build.py --fragment OUT  -> fragmento sin <html>/<head> (para publicar)
"""
import base64
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(ROOT, "src", "visor.html")
DATA = os.path.join(ROOT, "data", "staad_villahermosa_r1.3.json")
VENDOR = os.path.join(ROOT, "vendor", "three-0.160.0")

CDN_MAP = """{ "imports": {
  "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
  "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
} }"""

with open(TEMPLATE, encoding="utf-8") as fh:
    page = fh.read()
with open(DATA, encoding="utf-8") as fh:
    data = fh.read().strip()
if "</" in data:
    raise SystemExit("El JSON contiene '</' y rompería la etiqueta <script>.")
page = page.replace("__STAAD_DATA__", data, 1)


def data_url(name):
    with open(os.path.join(VENDOR, name), "rb") as fh:
        return "data:text/javascript;base64," + base64.b64encode(fh.read()).decode("ascii")


def document(body):
    return (
        '<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "</head>\n<body>\n" + body + "\n</body>\n</html>\n"
    )


args = sys.argv[1:]
if args[:1] == ["--fragment"]:
    out, html = args[1], page
elif args[:1] == ["--offline"]:
    if CDN_MAP not in page:
        raise SystemExit("No encontré el importmap de jsDelivr en la plantilla.")
    offline_map = (
        '{ "imports": {\n'
        f'  "three": "{data_url("three.module.min.js")}",\n'
        f'  "three/addons/controls/OrbitControls.js": "{data_url("OrbitControls.js")}",\n'
        f'  "three/addons/renderers/CSS2DRenderer.js": "{data_url("CSS2DRenderer.js")}"\n'
        "} }"
    )
    out = os.path.join(ROOT, "index_offline.html")
    html = document(page.replace(CDN_MAP, offline_map, 1))
else:
    out = os.path.join(ROOT, "index.html")
    html = document(page)
with open(out, "w", encoding="utf-8") as fh:
    fh.write(html)
print(f"{out}: {len(html) / 1024:.0f} KB")
