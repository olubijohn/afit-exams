"""Piston Engines: two more files, one folder each -> in/piston2.json
  PISTON ENGINE  NCAA.pdf    100 questions (AME licence exam, Category 'C' Piston Engines); answer = red bold option
  piston systems Bank.docx   "500 questions on Powerplant Department by Solo-P" and the EASA piston systems bank,
                             split by the file's own headings (all-caps bold, or dark blue); answer = red bold option.
                             Red text that is not bold is the author's note ("But your textbook only mention...") and is dropped.
                             Roman-numbered lines under a stem are its numbered statements ("1, 2, 3" options).
Usage (from tools/folders): <python with pymupdf> -I piston2.py in .
"""
import sys, os, re, json, zipfile, unicodedata
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
SRC, T = sys.argv[1:3]
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
QPAT = r'^\s*(\d{1,3})\s*[.)](?!\d)\s*'
OPAT = r'^\s*\(?([a-dA-D])\s*[.)]\s*'
SKIP_FIG = re.compile(r'\b(figure|diagram|illustrat|shown (below|above)|see fig)', re.I)
text = lambda cs: re.sub(r'\s+', ' ', ''.join(c[0] for c in cs)).strip()
marked = lambda cs: any(c[1] and not c[0].isspace() for c in cs)
def strip(cs, pat):
    m = re.match(pat, ''.join(c[0] for c in cs)); return cs[m.end():] if m else cs
SP = [(' ', False)]
# the Word file runs on after its short Cooling System part with a long mixed set that has no heading of its own
SPLIT = {'An engine equipped with a carburetor air heater is held in which position when starting': 'Mixed Piston Systems Questions'}

def parse(lines, heading=lambda kind, cs, t: None, first=None):
    """lines: (kind, chars) with kind q / o / r (statement) / h (heading) / None; chars = (ch, is_answer_mark)"""
    secs = {first: []}; cur = first; q = None
    for kind, cs in lines:
        t = text(cs)
        h = heading(kind, cs, t) or next((n for st, n in SPLIT.items() if kind == 'q' and t.startswith(st)), None)
        if h: cur = h; secs.setdefault(cur, []); q = None; continue
        if kind is None and re.match(QPAT + r'\S', t): kind, cs = 'q', strip(cs, QPAT)
        elif kind is None and re.match(OPAT + r'\S', t): kind, cs = 'o', strip(cs, OPAT)
        elif kind == 'o': cs = strip(cs, OPAT)
        if kind == 'q': q = {'q': cs, 'o': [], 'lab': False, 'st': 0}; secs[cur].append(q)
        elif q is None: continue
        elif kind == 'r': q['st'] += 1; q['q'] = q['q'] + [(f' ({q["st"]}) ', False)] + cs     # numbered statement, part of the question
        elif kind == 'o':
            cuts = [m.start() for m in re.finditer(r'\s{2,}[b-d][.)]\s', ''.join(c[0] for c in cs))]
            for s0, e0 in zip([0] + cuts, cuts + [len(cs)]): q['o'].append(strip(cs[s0:e0], r'^\s*' + OPAT[2:]) if s0 else cs[s0:e0])
            q['lab'] = True
        elif q['lab']: q['o'][-1] = q['o'][-1] + SP + cs
        elif q['o'] or re.search(r'[:?]\s*$|_{2,}\s*$', text(q['q'])): q['o'].append(cs)
        else: q['q'] = q['q'] + SP + cs
    # "Which of the following ...?" then statements typed as numbered questions, then options like "1, 2, and 5": one question
    for name, qs in secs.items():
        i = 0
        while i < len(qs):
            j = i + 1
            while j < len(qs) and not qs[j - 1]['o'] and len(text(qs[j]['q'])) < 60: j += 1
            if j - i > 2 and not qs[i]['o'] and qs[j - 1]['o'] and all(re.fullmatch(r'[\d,\s.andor/]+', text(o)) for o in qs[j - 1]['o']):
                st = qs[i + 1: j]
                qs[i]['q'] = qs[i]['q'] + [c for n, x in enumerate(st, 1) for c in [(f' ({n}) ', False)] + x['q']]
                qs[i]['o'] = qs[j - 1]['o']; del qs[i + 1: j]
            i += 1
    out = []
    for name, qs in secs.items():
        keep = []
        for q in qs:
            stem = text(q['q']); opts = [o for o in q['o'] if text(o)]
            a = [i for i, o in enumerate(opts) if marked(o)]
            why = None
            if len(opts) < 2: why = f'{len(opts)} options'
            elif len(a) != 1: why = f'{len(a)} of {len(opts)} options marked'
            elif SKIP_FIG.search(stem): why = 'needs a figure'
            if why: bad.append((name, why, stem, [text(o) for o in opts])); continue
            keep.append({'q': stem, 'o': [text(o) for o in opts], 'a': a})
        if qs: out.append({'name': name, 'qs': keep}); print(f'   {str(name):50} found {len(qs):4} kept {len(keep):4}')
    return out

bad, res = [], {}
# ======================= the PDF =======================
import pymupdf
lines = []
for p in pymupdf.open(os.path.join(SRC, 'PISTON ENGINE  NCAA.pdf')):
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            cs = [(ch, s['color'] == 0xFF0000) for s in l['spans'] for ch in unicodedata.normalize('NFKC', s['text'])]   # math bold digits -> plain
            t = text(cs)
            if not t or re.match(r'^Page \d+ of \d+$', t) or 'LICENCE EXAMINATION' in t or 'CATEGORY ‘C’' in t: continue
            if lines and re.fullmatch(r'\d{1,3}\.', text(lines[-1][1])): lines[-1] = (None, lines[-1][1] + SP + cs); continue   # "100." on a line of its own
            lines.append((None, cs))
print('PISTON ENGINE  NCAA.pdf'); res['pdf'] = parse(lines)

# ======================= the Word file =======================
z = zipfile.ZipFile(os.path.join(SRC, 'piston systems Bank.docx'))
N = ET.fromstring(z.read('word/numbering.xml'))
absf = {a.get(W + 'abstractNumId'): {l.get(W + 'ilvl'): l.find(W + 'numFmt').get(W + 'val') for l in a.findall(W + 'lvl') if l.find(W + 'numFmt') is not None} for a in N.findall(W + 'abstractNum')}
numfmt = {n.get(W + 'numId'): absf.get(n.find(W + 'abstractNumId').get(W + 'val'), {}) for n in N.findall(W + 'num')}
lines = []
for p in ET.fromstring(z.read('word/document.xml')).iter(W + 'p'):
    cs, blue, bold = [], 0, 0
    for r in p.iter(W + 'r'):
        rp = r.find(W + 'rPr'); col = ''; b = False
        if rp is not None:
            ce = rp.find(W + 'color'); col = (ce.get(W + 'val') or '').upper() if ce is not None else ''
            be = rp.find(W + 'b'); b = be is not None and be.get(W + 'val') not in ('0', 'false')
        for x in r:
            t = x.text if x.tag == W + 't' else (' ' if x.tag in (W + 'tab', W + 'br') else '')
            if not t: continue
            if col == 'FF0000' and not b and t.strip(): continue          # author's note in plain red
            cs += [(ch, col == 'FF0000') for ch in t]
            blue += (col == '002060') * len(t.strip()); bold += b * len(t.strip())
    if not text(cs): continue
    kind = None; pp = p.find(W + 'pPr')
    if pp is not None and pp.find(W + 'numPr') is not None:
        np_ = pp.find(W + 'numPr'); nid = np_.find(W + 'numId'); il = np_.find(W + 'ilvl')
        f = numfmt.get(nid.get(W + 'val') if nid is not None else None, {}).get(il.get(W + 'val') if il is not None else '0')
        if f and f not in ('none', 'bullet'): kind = 'q' if f == 'decimal' else 'r' if 'Roman' in f else 'o'
    n = len(text(cs).replace(' ', ''))
    if blue >= n * .8 or (kind is None and bold >= n * .8 and text(cs).upper() == text(cs) and re.search('[A-Z]{3}', text(cs))): kind = 'h'
    lines.append((kind, cs))
NAMES = {'500 QUESTIONS ON': None, 'POWERPLANT DEPARTMENT': None, 'BY SOLO-P': None}
def heading(kind, cs, t):
    if kind != 'h' or t in NAMES: return None
    t = re.sub(r'\s+', ' ', t).strip()
    return t.title().replace('Easa', 'EASA')
print('piston systems Bank.docx'); res['doc'] = parse(lines, heading, first='500 Questions on Powerplant (Solo-P)')

json.dump(res, open(os.path.join(T, 'in', 'piston2.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
json.dump(bad, open(os.path.join(T, 'in', 'piston2_unresolved.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('left out', len(bad))
