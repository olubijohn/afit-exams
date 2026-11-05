"""Survey the cabin crew source files: how many question-like lines, how answers are marked (colour / bold /
highlight / an "Answer" line / a key at the end).  python -I survey.py src"""
import os, re, sys, zipfile, collections
from lxml import etree
import docx, pymupdf
sys.stdout.reconfigure(encoding='utf-8')
D = sys.argv[1]
ANS = re.compile(r'\b(ans(wer)?s?|correct answer|key)\b\s*[:\-=]', re.I)
QNUM = re.compile(r'^\s*(Q(uestion)?\s*)?\d{1,3}\s*[\.\):]\s+\S')
OPT = re.compile(r'^\s*\(?[a-eA-E][\.\)]\s+\S')


def docx_runs(path):
    d = docx.Document(path); rows = []
    paras = list(d.paragraphs)
    for t in d.tables:
        for row in t.rows:
            for c in row.cells: paras += c.paragraphs
    for p in paras:
        txt = p.text.strip()
        if not txt: continue
        col = set(); bold = hl = False
        for r in p.runs:
            if not r.text.strip(): continue
            if r.font.color is not None and r.font.color.type is not None and r.font.color.rgb not in (None,) and str(r.font.color.rgb) not in ('000000',): col.add(str(r.font.color.rgb))
            if r.bold: bold = True
            if r.font.highlight_color: hl = True
        rows.append((txt, col, bold, hl))
    return rows


def pdf_runs(path):
    rows = []
    for page in pymupdf.open(path):
        for b in page.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                txt = ''.join(s['text'] for s in l['spans']).strip()
                if not txt: continue
                col = {f"{s['color']:06X}" for s in l['spans'] if s['text'].strip() and s['color'] not in (0,)}
                bold = any(s['flags'] & 16 or 'Bold' in s['font'] for s in l['spans'] if s['text'].strip())
                rows.append((txt, col, bold, False))
    return rows


def pptx_runs(path):
    rows = []; ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}
    z = zipfile.ZipFile(path)
    slides = sorted([n for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml$', n)], key=lambda n: int(re.findall(r'\d+', n)[-1]))
    for n in slides:
        x = etree.fromstring(z.read(n))
        for p in x.iter('{%s}p' % ns['a']):
            runs = p.findall('.//a:r', ns); txt = ''.join(r.findtext('a:t', '', ns) for r in runs).strip()
            if not txt: continue
            col = {c.get('val') for r in runs for c in r.findall('.//a:srgbClr', ns) if r.findtext('a:t', '', ns).strip()}
            bold = any((r.find('a:rPr', ns) is not None and r.find('a:rPr', ns).get('b') == '1') for r in runs)
            rows.append((txt, col, bold, False))
        rows.append(('--- slide ---', set(), False, False))
    return rows


def txt_runs(path):
    return [(l.strip(), set(), False, False) for l in open(path, encoding='utf-8') if l.strip()]


for f in sorted(os.listdir(D)):
    p = os.path.join(D, f); ext = f.rsplit('.', 1)[-1].lower()
    try:
        rows = {'docx': docx_runs, 'pdf': pdf_runs, 'pptx': pptx_runs, 'txt': txt_runs}[ext](p)
    except KeyError: continue
    except Exception as e: print(f'##### {f}: FAILED {e}'); continue
    cols = collections.Counter(c for _, cs, _, _ in rows for c in cs)
    print(f'##### {f}')
    print(f'  lines {len(rows)} | numbered {sum(bool(QNUM.match(t)) for t, *_ in rows)} | lettered options {sum(bool(OPT.match(t)) for t, *_ in rows)} | "answer:" lines {sum(bool(ANS.search(t)) for t, *_ in rows)} | bold lines {sum(b for _, _, b, _ in rows)} | highlighted {sum(h for *_, h in rows)} | colours {dict(cols.most_common(4))}')
    sample = [t for t, *_ in rows[:400] if len(t) > 2][8:20]
    for t in sample: print('    ' + t[:110])
