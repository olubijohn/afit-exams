"""Helicopter Licence Exam paper: one folder per Word file -> in/heli.json
  BASIC HELICOPTER AIRFRAME 2018.docx   answer = bold option
  HELICOPTER AIRFRAME LICENSE.docx      answer = red option
  HELICOPTER LICENSE.docx               two papers (2010, and BHA/TAA/01/03 2006); answer = red option
  Helicopter systems obj.docx           three parts (rotor heads & vibration, flying controls AAP6, transmission);
                                        answer = bold option (bold label alone counts) or red option
Questions are Word-numbered or typed "1." / "(a)"; a line with no label right after a stem is an option.
HELICOPTER AND HELICOPTER SYSTEMS AP.docx is essay questions with written answers, so it is not used.
Usage: python -I heli.py in . (from tools/folders)"""
import sys, os, re, json, zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
SRC, T = sys.argv[1:3]
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
QPAT = r'^\s*(\d{1,3})\s*[.)]\s*'
OPAT = r'^\s*\(?([a-dA-D])\s*[.)]\s*'
SKIP_FIG = re.compile(r'\b(figure|diagram|illustrat|shown (below|above)|see fig)', re.I)
FILES = [('BASIC HELICOPTER AIRFRAME 2018.docx', {}),
         ('HELICOPTER AIRFRAME LICENSE.docx', {}),
         ('HELICOPTER LICENSE.docx', {'Paper 1 – Category ‘A’ Airframe 2010': r'^HELICOPTER AIRFRAME$',
                                      'Basic Helicopter (Airframe) Licence Examination 2006': r'^BASIC HELICOPTER \(AIRFRAME\) LICENCE'}),
         ('Helicopter systems obj.docx', {'Rotor Heads, Tracking and Vibration': None,
                                          'Flying Control Systems Test AAP6': r'FLYING CONTROL SYSTEMS TEST',
                                          'Transmission System': r'^HELICOPTER TRANSMISSION'})]

def paras(path):
    z = zipfile.ZipFile(path)
    N = ET.fromstring(z.read('word/numbering.xml'))
    absf = {a.get(W + 'abstractNumId'): {l.get(W + 'ilvl'): l.find(W + 'numFmt').get(W + 'val') for l in a.findall(W + 'lvl') if l.find(W + 'numFmt') is not None} for a in N.findall(W + 'abstractNum')}
    numfmt = {n.get(W + 'numId'): absf.get(n.find(W + 'abstractNumId').get(W + 'val'), {}) for n in N.findall(W + 'num')}
    out = []
    for p in ET.fromstring(z.read('word/document.xml')).iter(W + 'p'):
        cs = []
        for r in p.iter(W + 'r'):
            rp = r.find(W + 'rPr'); red = bold = False
            if rp is not None:
                ce = rp.find(W + 'color'); red = ce is not None and (ce.get(W + 'val') or '').upper() == 'FF0000'
                be = rp.find(W + 'b'); bold = be is not None and be.get(W + 'val') not in ('0', 'false')
            for x in r:
                if x.tag == W + 't': cs += [(ch, red, bold) for ch in (x.text or '')]
                elif x.tag in (W + 'tab', W + 'br'): cs.append((' ', red, bold))
        kind = None; pp = p.find(W + 'pPr')
        if pp is not None and pp.find(W + 'numPr') is not None:
            np_ = pp.find(W + 'numPr'); nid = np_.find(W + 'numId'); il = np_.find(W + 'ilvl')
            f = numfmt.get(nid.get(W + 'val') if nid is not None else None, {}).get(il.get(W + 'val') if il is not None else '0')
            if f and f not in ('none', 'bullet'): kind = 'q' if f == 'decimal' else 'o'
        if text(cs): out.append((kind, cs))
    return out
text = lambda cs: re.sub(r'\s+', ' ', ''.join(c[0] for c in cs)).strip()
def marked(cs, i):   # any red / bold letter (some options have only their "(a)" label in bold)
    return any(c[i] and not c[0].isspace() for c in cs)
def strip(cs, pat):
    m = re.match(pat, ''.join(c[0] for c in cs)); return cs[m.end():] if m else cs

out, bad = [], []
for fname, secdef in FILES:
    P = paras(os.path.join(SRC, fname))
    names = list(secdef) or [None]
    secs = {n: [] for n in names}; cur = names[0]; q = None
    for kind, cs in P:
        t = text(cs)
        hit = next((n for n, pat in secdef.items() if pat and re.search(pat, t)), None)
        if hit: cur = hit; q = None; continue
        if kind is None and re.match(QPAT + r'\S', t): kind, cs = 'q', strip(cs, QPAT)
        elif kind is None and re.match(OPAT + r'\S', t): kind, cs = 'o', strip(cs, OPAT)
        elif kind == 'o': cs = strip(cs, OPAT)
        if kind == 'q': q = {'q': cs, 'o': [], 'lab': False}; secs[cur].append(q)
        elif q is None: continue                          # title lines before the first question
        elif kind == 'o':                                 # "bevel gears   b. helical gears   c. spur gears" on one line: split it
            cuts = [m.start() for m in re.finditer(r'\s{2,}[b-d][.)]\s', ''.join(c[0] for c in cs))]
            for s0, e0 in zip([0] + cuts, cuts + [len(cs)]): q['o'].append(strip(cs[s0:e0], r'^\s*' + OPAT[2:]) if s0 else cs[s0:e0])
            q['lab'] = True
        elif q['lab']: q['o'][-1] = q['o'][-1] + [(' ', 0, 0)] + cs       # an option that runs onto a second line
        elif q['o'] or re.search(r'[:?]\s*$|_{2,}\s*$', text(q['q'])): q['o'].append(cs)   # plain line under a finished stem: an option
        else: q['q'] = q['q'] + [(' ', 0, 0)] + cs          # a stem that runs onto a second line
    folder = []
    for name in names:
        keep = []
        for q in secs[name]:
            stem = text(q['q']); opts = [o for o in q['o'] if text(o)]
            a = [i for i, o in enumerate(opts) if marked(o, 1)] or [i for i, o in enumerate(opts) if marked(o, 2)]
            if marked(q['q'], 1) or (all(marked(o, 2) for o in opts) and len(opts) > 1): a = [i for i, o in enumerate(opts) if marked(o, 1)]   # stem itself styled: only red counts
            why = None
            if len(opts) < 2: why = f'{len(opts)} options'
            elif len(a) != 1: why = f'{len(a)} of {len(opts)} options marked'
            elif SKIP_FIG.search(stem): why = 'needs a figure'
            if why: bad.append((fname, name, why, stem, [text(o) for o in opts])); continue
            keep.append({'q': stem, 'o': [text(o) for o in opts], 'a': a})
        print(f'{fname:40} {str(name):55} found {len(secs[name]):4} kept {len(keep):4}')
        folder.append({'name': name, 'qs': keep})
    out.append({'file': fname, 'secs': folder})
json.dump(out, open(os.path.join(T, 'in', 'heli.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
json.dump(bad, open(os.path.join(T, 'in', 'heli_unresolved.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('left out', len(bad))
