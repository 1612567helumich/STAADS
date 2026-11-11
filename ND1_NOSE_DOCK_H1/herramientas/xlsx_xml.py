"""Edicion de un .xlsx a nivel XML (conserva formatos, imagenes y graficas que
openpyxl perderia) y recalculo de valores con LibreOffice para dejar al dia los
valores guardados de las formulas."""
import os
import re
import subprocess
import tempfile
import zipfile
from xml.sax.saxutils import escape


def col_idx(ref):
    letters = re.match(r'[A-Z]+', ref).group(0)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n


def row_num(ref):
    return int(re.search(r'\d+', ref).group(0))


class Book:
    def __init__(self, path):
        self.files = {}
        with zipfile.ZipFile(path) as z:
            self.order = z.namelist()
            for n in self.order:
                self.files[n] = z.read(n)

    def text(self, name):
        return self.files[name].decode('utf-8')

    def put(self, name, s):
        self.files[name] = s.encode('utf-8')

    def sheet_path(self, title):
        wb = self.text('xl/workbook.xml')
        rels = self.text('xl/_rels/workbook.xml.rels')
        m = re.search(r'<sheet[^>]*name="%s"[^>]*r:id="([^"]+)"' % re.escape(escape(title)), wb)
        if not m:
            raise KeyError(title)
        rid = m.group(1)
        t = re.search(r'<Relationship[^>]*Id="%s"[^>]*Target="([^"]+)"' % rid, rels) or \
            re.search(r'<Relationship[^>]*Target="([^"]+)"[^>]*Id="%s"' % rid, rels)
        return 'xl/' + t.group(1).lstrip('/')

    def force_recalc(self):
        wb = self.text('xl/workbook.xml')
        wb = re.sub(r'<calcPr[^>]*/>', '', wb)
        wb = wb.replace('</workbook>', '<calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>') if '<definedNames' not in wb else \
            re.sub(r'(</definedNames>)', r'\1<calcPr calcId="191029" fullCalcOnLoad="1"/>', wb, count=1)
        # calcPr debe ir despues de sheets/definedNames y antes de extLst
        if '<extLst>' in wb and wb.index('<calcPr') > wb.index('<extLst>'):
            wb = re.sub(r'<calcPr[^>]*/>', '', wb)
            wb = wb.replace('<extLst>', '<calcPr calcId="191029" fullCalcOnLoad="1"/><extLst>', 1)
        self.put('xl/workbook.xml', wb)
        if 'xl/calcChain.xml' in self.files:
            del self.files['xl/calcChain.xml']
            self.order.remove('xl/calcChain.xml')
            ct = self.text('[Content_Types].xml')
            ct = re.sub(r'<Override[^>]*calcChain[^>]*/>', '', ct)
            self.put('[Content_Types].xml', ct)
            rels = self.text('xl/_rels/workbook.xml.rels')
            rels = re.sub(r'<Relationship[^>]*calcChain[^>]*/>', '', rels)
            self.put('xl/_rels/workbook.xml.rels', rels)

    def save(self, path):
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
            for n in self.order:
                z.writestr(n, self.files[n])


class Sheet:
    CELL = r'<c r="%s"((?:\s[^>]*?)?)(/>|>.*?</c>)'

    def __init__(self, book, title):
        self.book = book
        self.path = book.sheet_path(title)
        self.xml = book.text(self.path)

    def commit(self):
        rows = [int(r) for r in re.findall(r'<row r="(\d+)"', self.xml)]
        cols = [col_idx(c) for c in re.findall(r'<c r="([A-Z]+)\d+"', self.xml)]
        if rows and cols:
            def letters(n):
                s = ''
                while n:
                    n, r = divmod(n - 1, 26)
                    s = chr(65 + r) + s
                return s
            ref = '%s%d:%s%d' % (letters(min(cols)), min(rows), letters(max(cols)), max(rows))
            self.xml = re.sub(r'<dimension ref="[^"]*"/>', '<dimension ref="%s"/>' % ref, self.xml, count=1)
        self.book.put(self.path, self.xml)

    def _build(self, ref, style, value=None, formula=None, text=None):
        s = (' s="%s"' % style) if style else ''
        if formula is not None:
            return '<c r="%s"%s><f>%s</f></c>' % (ref, s, escape(formula))
        if text is not None:
            return '<c r="%s"%s t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (ref, s, escape(text))
        if value is None:
            return '<c r="%s"%s/>' % (ref, s)
        return '<c r="%s"%s><v>%s</v></c>' % (ref, s, repr(float(value)) if not isinstance(value, int) else value)

    def clear(self, ref):
        """Elimina la celda (valor, formula y formato)."""
        m = re.search(self.CELL % ref, self.xml, re.S)
        if m:
            self.xml = self.xml[:m.start()] + self.xml[m.end():]

    def style_of(self, ref):
        m = re.search(self.CELL % ref, self.xml, re.S)
        if not m:
            return None
        ms = re.search(r'\ss="(\d+)"', m.group(1))
        return ms.group(1) if ms else None

    def set(self, ref, value=None, formula=None, text=None, style=None):
        m = re.search(self.CELL % ref, self.xml, re.S)
        if m:
            if style is None:
                ms = re.search(r'\ss="(\d+)"', m.group(1))
                style = ms.group(1) if ms else None
            new = self._build(ref, style, value, formula, text)
            self.xml = self.xml[:m.start()] + new + self.xml[m.end():]
            return
        new = self._build(ref, style, value, formula, text)
        rn = row_num(ref)
        mr = re.search(r'<row r="%d"([^>]*?)(/>|>(.*?)</row>)' % rn, self.xml, re.S)
        if mr:
            if mr.group(2) == '/>':
                rep = '<row r="%d"%s>%s</row>' % (rn, mr.group(1), new)
                self.xml = self.xml[:mr.start()] + rep + self.xml[mr.end():]
                return
            body = mr.group(3)
            pos = None
            for mc in re.finditer(r'<c r="([A-Z]+)\d+"', body):
                if col_idx(mc.group(1)) > col_idx(ref):
                    pos = mc.start()
                    break
            body2 = body + new if pos is None else body[:pos] + new + body[pos:]
            rep = '<row r="%d"%s>%s</row>' % (rn, mr.group(1), body2)
            self.xml = self.xml[:mr.start()] + rep + self.xml[mr.end():]
            return
        # fila nueva
        rowxml = '<row r="%d">%s</row>' % (rn, new)
        pos = None
        for mr in re.finditer(r'<row r="(\d+)"', self.xml):
            if int(mr.group(1)) > rn:
                pos = mr.start()
                break
        if pos is None:
            if '<sheetData/>' in self.xml:
                self.xml = self.xml.replace('<sheetData/>', '<sheetData>' + rowxml + '</sheetData>')
            else:
                i = self.xml.index('</sheetData>')
                self.xml = self.xml[:i] + rowxml + self.xml[i:]
        else:
            self.xml = self.xml[:pos] + rowxml + self.xml[pos:]


CELLRE = re.compile(r'<c r="([A-Z]+\d+)"((?:\s[^>]*?)?)(?:/>|>(.*?)</c>)', re.S)
VRE = re.compile(r'<v(?:\s[^>]*)?>.*?</v>|<v\s*/>', re.S)
TRE = re.compile(r'\st="[a-zA-Z]+"')


def _strip_cached(xml):
    """Quita los valores guardados de las celdas con formula (fuerza el calculo)."""
    def rep(m):
        ref, attrs, body = m.group(1), m.group(2), m.group(3)
        if body is None or '<f' not in body:
            return m.group(0)
        return '<c r="%s"%s>%s</c>' % (ref, TRE.sub('', attrs), VRE.sub('', body))
    return CELLRE.sub(rep, xml)


def recalc_and_inject(book, out_path, workdir=None):
    """Guarda el libro, lo recalcula con LibreOffice y vuelve a escribir en el XML
    original los valores calculados de cada formula."""
    import openpyxl
    from xml.sax.saxutils import unescape
    workdir = workdir or tempfile.mkdtemp()
    tmp_in = os.path.join(workdir, 'in')
    tmp_out = os.path.join(workdir, 'out')
    os.makedirs(tmp_in, exist_ok=True)
    os.makedirs(tmp_out, exist_ok=True)
    sheets = {}
    wbx = book.text('xl/workbook.xml')
    for name in re.findall(r'<sheet[^>]*name="([^"]+)"', wbx):
        title = unescape(name, {'&quot;': '"'})
        sheets[title] = book.sheet_path(title)
    b2 = Book.__new__(Book)
    b2.files = dict(book.files)
    b2.order = list(book.order)
    for title, p in sheets.items():
        b2.put(p, _strip_cached(b2.text(p)))
    src = os.path.join(tmp_in, 'libro.xlsx')
    b2.save(src)
    env = dict(os.environ)
    env['HOME'] = os.path.join(workdir, 'home')
    os.makedirs(env['HOME'], exist_ok=True)
    subprocess.run(['soffice', '--headless', '--norestore', '--convert-to', 'xlsx:Calc MS Excel 2007 XML', '--outdir', tmp_out, src],
                   env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=170, check=True)
    wv = openpyxl.load_workbook(os.path.join(tmp_out, 'libro.xlsx'), data_only=True)
    nupd = 0
    for title, p in sheets.items():
        ws = wv[title]

        def rep(m):
            nonlocal nupd
            ref, attrs, body = m.group(1), m.group(2), m.group(3)
            if body is None or '<f' not in body:
                return m.group(0)
            v = ws[ref].value
            attrs = TRE.sub('', attrs)
            body = VRE.sub('', body)
            if v is None:
                newv = ''
            elif isinstance(v, bool):
                attrs += ' t="b"'
                newv = '<v>%d</v>' % int(v)
            elif isinstance(v, (int, float)):
                newv = '<v>%s</v>' % repr(float(v))
            elif isinstance(v, str) and v.startswith('#') and v.endswith(('!', '?', '/A', '/0')):
                attrs += ' t="e"'
                newv = '<v>%s</v>' % escape(v)
            else:
                attrs += ' t="str"'
                sp = ' xml:space="preserve"' if (v != v.strip() or '  ' in v) else ''
                newv = '<v%s>%s</v>' % (sp, escape(str(v)))
            nupd += 1
            return '<c r="%s"%s>%s%s</c>' % (ref, attrs, body, newv)
        book.put(p, CELLRE.sub(rep, book.text(p)))
    book.save(out_path)
    return nupd
