"""UNPRESSURIZED LICENSE AAP14.docx -> in/aap14.json (one folder under Unpressurised Metal Airframe, one section per heading
in the file, in the file's order).
The file is already split into sections by bold headings (AIRCRAFT GROUND HANDLING, LANDING GEAR, ... ELECTRICAL SYSTEM);
"LANDING GEAR PART 2" only introduces Tyres / Wheels / Brakes / Anti-skid, so it holds no questions itself.
Questions are Word numbered paragraphs (decimal) or typed "12." lines; options are lettered / roman numbered paragraphs or typed
"(a)" / "a." lines, sometimes all on one line ("a. Toe   b. Heel   c. Apex slip").
The answer is typed in red (FF0000) in most sections, green (00B050) in Vacuum, and bold in the sections with no colour at all
(Tyres, Wheels, Brakes, Anti-skid). Each section uses its own marker.
Usage: python -I aap14.py <docx> <tools/folders dir>"""
import sys, os, re, json, zipfile, difflib
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
z = zipfile.ZipFile(sys.argv[1]); T = sys.argv[2]

N = ET.fromstring(z.read('word/numbering.xml'))
absfmt = {}
for a in N.findall(W + 'abstractNum'):
    absfmt[a.get(W + 'abstractNumId')] = {l.get(W + 'ilvl'): l.find(W + 'numFmt').get(W + 'val') for l in a.findall(W + 'lvl') if l.find(W + 'numFmt') is not None}
numfmt = {n.get(W + 'numId'): absfmt.get(n.find(W + 'abstractNumId').get(W + 'val'), {}) for n in N.findall(W + 'num')}

COLOUR = ('FF0000', '00B050')
paras = []   # each: {'c': [(char, colour?, bold?)], 'kind': 'q'|'o'|None}
for p in ET.fromstring(z.read('word/document.xml')).iter(W + 'p'):
    cs = []
    for r in p.iter(W + 'r'):
        t = ''.join((x.text or '') if x.tag == W + 't' else (' ' if x.tag == W + 'tab' else '') for x in r)
        if not t: continue
        rp = r.find(W + 'rPr'); col = bold = False
        if rp is not None:
            ce = rp.find(W + 'color'); col = ce is not None and (ce.get(W + 'val') or '').upper() in COLOUR
            be = rp.find(W + 'b'); bold = be is not None and be.get(W + 'val') not in ('0', 'false')
        cs += [(ch, col, bold) for ch in t]
    kind = None
    pp = p.find(W + 'pPr')
    if pp is not None and pp.find(W + 'numPr') is not None:
        np_ = pp.find(W + 'numPr'); nid = np_.find(W + 'numId'); il = np_.find(W + 'ilvl')
        f = numfmt.get(nid.get(W + 'val') if nid is not None else None, {}).get(il.get(W + 'val') if il is not None else '0')
        if f and f != 'none': kind = 'q' if f == 'decimal' else 'o'
    paras.append({'c': cs, 'kind': kind})

text = lambda cs: re.sub(r'\s+', ' ', ''.join(c for c, _, _ in cs)).strip()
def frac(cs, i):
    s = [c for c in cs if not c[0].isspace()]
    return sum(c[i] for c in s) / len(s) if s else 0

def strip_label(cs, pat):
    t = ''.join(c for c, _, _ in cs); m = re.match(pat, t)
    return cs[m.end():] if m else None
def split_inline(cs):
    """a. Toe   b. Heel   c. Apex  ->  three option pieces (labels b., c., d. in order, preceded by a space)"""
    t = ''.join(c for c, _, _ in cs); cuts, nxt, pos = [], 'b', 0
    while True:
        m = re.compile(r'(?<=\s)\(?[' + nxt + nxt.upper() + r']\s*[.)]\s+').search(t, pos)
        if not m: break
        cuts.append((m.start(), m.end())); nxt = chr(ord(nxt) + 1); pos = m.end()
    if not cuts: return [cs]
    out, start = [], 0
    for a, b in cuts: out.append(cs[start:a]); start = b
    out.append(cs[start:]); return out

HEAD = re.compile(r"[A-Z0-9 &,()'\-/.]{4,60}")
QPAT, OPAT = r'^\s*(\d{1,3})\s*[.)]\s*', r'^\s*\(?([a-eA-E]|i{1,3}|iv)\s*[.)]\s*'
sections, cur, q, started = [], None, None, False
for x in paras:
    cs, t = x['c'], text(x['c'])
    if not t: continue
    if x['kind'] is None and frac(cs, 2) > .8 and HEAD.fullmatch(t) and not re.match(r'^\(?[A-Ea-e][.)]', t):
        if t != 'COURSE DISTRIBUTION':
            started = True; cur = {'name': t, 'qs': []}; sections.append(cur); q = None
        continue
    if not started: continue
    kind = x['kind']
    if kind is None and re.match(QPAT + r'\S', t): kind, cs = 'q', strip_label(cs, QPAT)
    elif kind is None and re.match(OPAT + r'\S', t): kind, cs = 'o', strip_label(cs, OPAT)
    elif kind == 'o' and re.match(OPAT + r'\S', t): cs = strip_label(cs, OPAT)          # numbered and typed "(b)" too
    if kind == 'q' and q is not None and not q['o'] and frac(cs, 1) > .5: kind = 'o'   # a red line straight after a stem is an option
    if kind == 'q' and q is not None and not q['o']:
        # a numbered line before the question has any options is one of its statements ("Which of the following ...: 1. ... 2. ...")
        q['n'] = q.get('n', 0) + 1; q['q'] = q['q'] + [(' ', False, False)] + [(ch, False, False) for ch in f"({q['n']}) "] + cs; continue
    if kind == 'q':
        q = {'q': cs, 'o': []}; cur['qs'].append(q)
    elif kind == 'o' and q is not None:
        q['o'] += split_inline(cs)
    elif q is not None:                                   # unlabelled line: continues the stem or the last option
        if q['o']: q['o'][-1] = q['o'][-1] + [(' ', False, False)] + cs
        else: q['q'] = q['q'] + [(' ', False, False)] + cs

norm = lambda t: re.sub(r'[^a-z0-9]+', ' ', t.lower()).strip()
sim = lambda a, b: difflib.SequenceMatcher(None, norm(a), norm(b)).ratio() > .85
out, bad, report = [], [], []
for s in sections:
    # the answer marker: colour (red, or green in Vacuum) when exactly one option is coloured, otherwise bold
    keep, used = [], set()
    for q in s['qs']:
        stem = text(q['q'])
        opts = [a for a in q['o'] if text(a)]
        a = [i for i, x in enumerate(opts) if frac(x, 1) > .5]; used.add('colour')
        if len(a) != 1:
            b = [i for i, x in enumerate(opts) if frac(x, 2) > .5]
            if len(b) == 1: a = b; used.add('bold')
        o = [(text(x), i in a) for i, x in enumerate(opts)]
        if len(o) < 2 or len(a) != 1:
            bad.append((s['name'], f'{len(o)} options, {len(a)} marked', stem, [x for x, _ in o])); continue
        it = {'q': stem, 'o': [x for x, _ in o], 'a': a}
        if any(len(it['o']) == len(k['o']) and sim(it['q'], k['q']) and all(sim(u, v) for u, v in zip(it['o'], k['o'])) for k in keep): continue
        keep.append(it)
    report.append((s['name'], '+'.join(sorted(used)), len(s['qs']), len(keep)))
    if keep: out.append({'name': s['name'], 'qs': keep})
for r in report: print(f'{r[0]:36} {r[1]:7} found {r[2]:4}  kept {r[3]:4}')
print('total kept', sum(len(s['qs']) for s in out), '| unresolved', len(bad))
for b in bad: print('  SKIP', b[0], '|', b[1], '|', b[2][:110], '|', ' / '.join(o[:45] for o in b[3]))
json.dump(out, open(os.path.join(T, 'in', 'aap14.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
json.dump(bad, open(os.path.join(T, 'in', 'aap14_unresolved.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
