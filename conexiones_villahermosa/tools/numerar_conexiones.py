"""Sella el número de conexión en azul, arriba a la derecha, en las hojas de pieza del PDF.

Las hojas 22 a 36 de 001_CONEXIONES_VILLAHERMOSA.pdf son los planos de pieza (placas de conexión),
en orden de número de parte. Se numeran 1 a 15 en ese orden; el visor usa la misma regla
(conexión = hoja − 21, ver connNum en src/visor.html).

Uso:
    python3 -I numerar_conexiones.py ENTRADA.pdf SALIDA.pdf [primera_hoja=22] [ultima_hoja=36]

Requiere pypdf y reportlab. Las hojas 1 a 21 (ensambles de columna) no se tocan.
"""
import io
import sys

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas

src, dst = sys.argv[1], sys.argv[2]
first = int(sys.argv[3]) if len(sys.argv) > 3 else 22
last = int(sys.argv[4]) if len(sys.argv) > 4 else 36
BLUE = Color(0 / 255, 82 / 255, 204 / 255)
FRAME = 27.0  # el marco del plano queda a 27 pt de la orilla superior y ~28 pt de la derecha

writer = PdfWriter()
writer.append(PdfReader(src))
for numero, idx in enumerate(range(first - 1, last), start=1):
    page = writer.pages[idx]
    w, h = float(page.mediabox.width), float(page.mediabox.height)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(w, h))
    txt, size = str(numero), 30
    box_w, box_h = max(c.stringWidth(txt, "Helvetica-Bold", size) + 20, 46), 44
    x1, y1 = w - (FRAME + 1) - 8, h - FRAME - 8  # esquina superior derecha, 8 pt dentro del marco
    x0, y0 = x1 - box_w, y1 - box_h
    c.setStrokeColor(BLUE)
    c.setLineWidth(2.2)
    c.roundRect(x0, y0, box_w, box_h, 6, stroke=1, fill=0)
    c.setFillColor(BLUE)
    c.setFont("Helvetica-Bold", size)
    c.drawCentredString((x0 + x1) / 2, y0 + (box_h - size * 0.72) / 2, txt)
    c.save()
    page.merge_page(PdfReader(io.BytesIO(buf.getvalue())).pages[0])
    print(f"hoja {idx + 1:2d} -> conexión {numero:2d}")
writer.compress_identical_objects()
with open(dst, "wb") as fh:
    writer.write(fh)
