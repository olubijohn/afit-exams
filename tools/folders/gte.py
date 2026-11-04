"""Gas Turbine Engine paper: two files, one folder each, split into the file's own topics -> in/gte.json
  GTE LICENSE EXAM COMPILATION 2024.docx  six papers, each under a blue bold heading (GAS TURBINE PRACTICE FOR LICENCE ...
      GAS TURBINE ENGINE OBJECTIVE TEST QUESTIONS). Each paper is typed differently: "1)" + "a)" lines, Word-numbered
      questions and options, "1." + "Option A." lines, or "1." questions followed by unlabelled option lines.
      The answer is the option typed in red (FF0000); papers with no red use bold.
  EASA PART 66 BLOG Module 15, Gas Turbine Engine.pdf  topics 15.1 ... 15.22; every question has "Option A./B./C.",
      "Correct Answer is." (the answer's text) and "Explanation."; the blog comments after the last question are dropped.
Usage: python -I gte.py <docx> <pdf> <tools/folders dir>"""
import sys, os, re, json, zipfile, difflib
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
DOCX, PDF, T = sys.argv[1:4]
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
norm = lambda t: re.sub(r'[^a-z0-9]+', ' ', t.lower()).strip()
sim = lambda a, b: difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()
SKIP_FIG = re.compile(r'\b(figure|diagram|illustrat|shown (below|above)|see fig)', re.I)   # need a picture the app can't show

# ======================= the Word file =======================
z = zipfile.ZipFile(DOCX)
N = ET.fromstring(z.read('word/numbering.xml'))
absf = {a.get(W + 'abstractNumId'): {l.get(W + 'ilvl'): l.find(W + 'numFmt').get(W + 'val') for l in a.findall(W + 'lvl') if l.find(W + 'numFmt') is not None} for a in N.findall(W + 'abstractNum')}
numfmt = {n.get(W + 'numId'): absf.get(n.find(W + 'abstractNumId').get(W + 'val'), {}) for n in N.findall(W + 'num')}
HEADCOL = ('548DD4', '0070C0')
text = lambda cs: re.sub(r'\s+', ' ', ''.join(c[0] for c in cs)).strip()
paras = []
for p in ET.fromstring(z.read('word/document.xml')).iter(W + 'p'):
    cs, pieces = [], []          # a line break inside a paragraph starts a new line (one paper puts a question and its options in one paragraph)
    for r in p.iter(W + 'r'):
        rp = r.find(W + 'rPr'); col = bold = head = False
        if rp is not None:
            ce = rp.find(W + 'color'); v = (ce.get(W + 'val') or '').upper() if ce is not None else ''
            col, head = v == 'FF0000', v in HEADCOL
            be = rp.find(W + 'b'); bold = be is not None and be.get(W + 'val') not in ('0', 'false')
        for x in r:
            if x.tag == W + 'br' and x.get(W + 'type') in (None, 'textWrapping'): pieces.append(cs); cs = []
            elif x.tag == W + 't': cs += [(ch, col, bold, head) for ch in (x.text or '')]
            elif x.tag == W + 'tab': cs.append((' ', col, bold, head))
    pieces.append(cs)
    kind = None; pp = p.find(W + 'pPr')
    if pp is not None and pp.find(W + 'numPr') is not None:
        np_ = pp.find(W + 'numPr'); nid = np_.find(W + 'numId'); il = np_.find(W + 'ilvl')
        f = numfmt.get(nid.get(W + 'val') if nid is not None else None, {}).get(il.get(W + 'val') if il is not None else '0')
        if f and f not in ('none', 'bullet'): kind = 'q' if f == 'decimal' else 'o'
    pieces = [c for c in pieces if text(c)] or [[]]
    for j, c in enumerate(pieces): paras.append({'c': c, 'kind': kind if j == 0 else None})

def frac(cs, i):
    s = [c for c in cs if not c[0].isspace()]
    return sum(c[i] for c in s) / len(s) if s else 0
def strip_label(cs, pat):
    m = re.match(pat, ''.join(c[0] for c in cs)); return cs[m.end():] if m else cs
QPAT = r'^\s*(?:Q(?:uestion)?\.?\s*)?(\d{1,3})\s*[.):]\s*'
OPAT = r'^\s*(?:Option\s+)?\(?([a-dA-D])\s*[.)]\s*'

# split into the six papers by their headings
secs, cur = [], None
for x in paras:
    t = text(x['c'])
    if not t: continue
    if x['kind'] is None and frac(x['c'], 3) > .8 and t.upper() == t and len(t) > 10:
        cur = {'name': t, 'lines': []}; secs.append(cur); continue
    if cur: cur['lines'].append(x)

doc_out, bad = [], []
for s in secs:
    L = s['lines']
    labelled = sum(1 for x in L if x['kind'] == 'o' or re.match(OPAT + r'\S', text(x['c'])))
    nq = sum(1 for x in L if x['kind'] == 'q' or re.match(QPAT + r'\S', text(x['c'])))
    bare = labelled < nq * 2              # some questions have plain, unlabelled option lines (decided per question below)
    qs, q = [], None
    for x in L:
        cs, t, kind = x['c'], text(x['c']), x['kind']
        if kind is None and re.match(QPAT + r'\S', t): kind, cs = 'q', strip_label(cs, QPAT)
        elif kind is None and re.match(OPAT + r'\S', t): kind, cs = 'o', strip_label(cs, OPAT)
        elif kind == 'o': cs = strip_label(cs, OPAT)
        cs = strip_label(cs, r'^[\s.\-:]+')
        if kind == 'q' and q is not None and not q['o'] and frac(cs, 1) > .5: kind = 'o'   # a red line straight after a stem is an option
        if kind == 'q':
            q = {'q': cs, 'o': [], 'lab': False, 'pieces': [cs]}; qs.append(q)
        elif kind == 'o' and q is not None: q['o'].append(cs); q['lab'] = True
        elif q is not None:
            if bare and not q['lab'] and (q['o'] or re.search(r'[:?.]\s*$|\b(is|are|by|the|a|an|of|to|in|at|as|be|will|for|with)\s*$|_{3,}\s*$', text(q['q']), re.I)):
                q['o'].append(cs)                  # plain line under the stem: an option
            elif q['o']: q['o'][-1] = q['o'][-1] + [(' ', False, False, False)] + cs
            else: q['q'] = q['q'] + [(' ', False, False, False)] + cs; q['pieces'].append(cs)
    keep, used = [], set()
    for q in qs:
        if bare and not q['lab'] and not q['o'] and len(q['pieces']) >= 4:    # stem with no closing mark: its last three lines are the options
            q['o'] = q['pieces'][-3:]; q['q'] = [c for p in q['pieces'][:-3] for c in p + [(' ', False, False, False)]]
        stem = text(q['q']); opts = [o for o in q['o'] if text(o)]
        a = [i for i, o in enumerate(opts) if frac(o, 1) > .5]
        if len(a) == 1: used.add('red')
        else:
            sb = frac(q['q'], 2) > .5   # papers that set every line in bold mark nothing with bold
            b = [i for i, o in enumerate(opts) if frac(o, 2) > .5]
            if len(b) == 1 and not (sb and len(b) == len(opts)): a = b; used.add('bold')
        if len(opts) < 2 or len(a) != 1:
            bad.append((s['name'], f'{len(opts)} options, {len(a)} marked', stem, [text(o) for o in opts])); continue
        if SKIP_FIG.search(stem): bad.append((s['name'], 'needs a figure', stem, [text(o) for o in opts])); continue
        it = {'q': stem, 'o': [text(o) for o in opts], 'a': a}
        if any(len(it['o']) == len(k['o']) and sim(it['q'], k['q']) > .9 and all(sim(u, v) > .85 for u, v in zip(it['o'], k['o'])) for k in keep): continue
        keep.append(it)
    print(f'DOC {s["name"]:45} {"+".join(sorted(used)):8} {"bare" if bare else "":4} found {len(qs):4} kept {len(keep):4}')
    if keep: doc_out.append({'name': s['name'], 'qs': keep})

# ======================= the PDF =======================
import pymupdf
raw = '\n'.join(p.get_text() for p in pymupdf.open(PDF)).replace('\xa0', ' ')
raw = re.split(r'\n\d+ comments:\n', raw)[0]                         # the blog's comment section
TOP = re.compile(r'^\s*15\.(\d+),?\s+(.+?)\s*$', re.M)
heads = [(m.start(), m.end(), int(m.group(1)), m.group(2)) for m in TOP.finditer(raw)]
def tname(n, t):
    t = re.sub(r'\.$', '', t.strip()); t = re.sub(r'^GAS TURBINE ENGINE\s+', '', t)
    return f'15.{n} {t[:1].upper() + t[1:]}'
pdf_out = []
for i, (s0, e0, n, t) in enumerate(heads):
    body = raw[e0: heads[i + 1][0] if i + 1 < len(heads) else len(raw)]
    keep, found = [], 0
    for blk in re.split(r'Question Number\.\s*\d+\.\s*', body)[1:]:
        found += 1
        m = re.match(r'(?s)(.*?)\s*Option A\.\s*(.*?)\s*Correct Answer is\.\s*(.*?)\s*(?:Explanation\.\s*(.*))?$', blk)
        if not m: bad.append((f'15.{n}', 'unreadable', blk[:100], [])); continue
        stem, opttxt, ans, expl = m.group(1), m.group(2), m.group(3), m.group(4) or ''
        opts = [re.sub(r'\s+', ' ', o).strip() for o in re.split(r'\s*Option [B-E]\.\s*', opttxt)]
        stem = re.sub(r'\s+', ' ', stem).strip(); ans = re.sub(r'\s+', ' ', ans).strip(); expl = re.sub(r'\s+', ' ', expl).strip()
        sc = [sim(ans, o) for o in opts]; best = max(range(len(opts)), key=lambda j: sc[j]) if opts else -1
        if len(opts) < 2 or best < 0 or sc[best] < .75 or sorted(sc)[-2:][0] > .97 and len(opts) > 1 and sc.count(sc[best]) > 1:
            bad.append((tname(n, t), 'answer not one of the options', stem, opts + ['ANSWER: ' + ans])); continue
        if SKIP_FIG.search(stem): bad.append((tname(n, t), 'needs a figure', stem, opts)); continue
        it = {'q': stem, 'o': opts, 'a': [best]}
        if expl and not re.fullmatch(r'(?i)nil\.?', expl): it['x'] = expl
        if any(sim(it['q'], k['q']) > .92 and len(k['o']) == len(opts) and all(sim(u, v) > .9 for u, v in zip(opts, k['o'])) for k in keep): continue
        keep.append(it)
    print(f'PDF {tname(n, t):45} found {found:4} kept {len(keep):4}')
    if keep: pdf_out.append({'name': tname(n, t), 'qs': keep})

print('DOC total', sum(len(s['qs']) for s in doc_out), '| PDF total', sum(len(s['qs']) for s in pdf_out), '| left out', len(bad))
for b in bad: print('  SKIP', b[0][:30], '|', b[1], '|', b[2][:100], '|', ' / '.join(o[:40] for o in b[3]))
json.dump({'doc': doc_out, 'pdf': pdf_out}, open(os.path.join(T, 'in', 'gte.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
json.dump(bad, open(os.path.join(T, 'in', 'gte_unresolved.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
