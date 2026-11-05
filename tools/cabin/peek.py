"""Show marked text (bold / underline / highlight) and the last lines of a source file.  python -I peek.py file [n]"""
import sys, re, docx, pymupdf
from docx.oxml.ns import qn
sys.stdout.reconfigure(encoding='utf-8')
p = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 12


def marks_docx(path):
    d = docx.Document(path); out, allp = [], []
    for para in d.paragraphs:
        t = para.text.strip()
        if not t: continue
        allp.append(t)
        for r in para.runs:
            rp = r._r.rPr
            if rp is None or not r.text.strip(): continue
            m = []
            if rp.find(qn('w:b')) is not None and rp.find(qn('w:b')).get(qn('w:val')) not in ('0', 'false'): m.append('B')
            if rp.find(qn('w:u')) is not None and rp.find(qn('w:u')).get(qn('w:val')) not in ('none', None): m.append('U')
            if rp.find(qn('w:highlight')) is not None and rp.find(qn('w:highlight')).get(qn('w:val')) != 'none': m.append('H')
            if m: out.append(f"[{''.join(m)}] {r.text.strip()[:70]}   <- {t[:60]}")
    return out, allp


def marks_pdf(path):
    out, allp = [], []
    for page in pymupdf.open(path):
        for b in page.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                t = ''.join(s['text'] for s in l['spans']).strip()
                if not t: continue
                allp.append(t)
                for s in l['spans']:
                    if s['text'].strip() and (s['flags'] & 16 or 'Bold' in s['font'] or s['color'] not in (0, 0x231F20)):
                        out.append(f"[{'B' if s['flags'] & 16 or 'Bold' in s['font'] else ''}{'#%06X' % s['color'] if s['color'] else ''}] {s['text'].strip()[:70]}   <- {t[:60]}")
    return out, allp


out, allp = (marks_pdf if p.lower().endswith('.pdf') else marks_docx)(p)
print(f'marked runs: {len(out)}')
for x in out[:n]: print('  ' + x)
print('last lines:')
for x in allp[-n:]: print('  ' + x[:120])
