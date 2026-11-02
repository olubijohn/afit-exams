"""GENERAL PAPER 2.pdf -> in/gp2.json (one folder under General, in the file's order, like Deji / 2023 GENERALS).
The answer is the option with a highlight annotation over it. Questions start at "Qn/100"; options are "A." / "a." lines,
a line without a label continues the line above. Empty options ("C. ") and placeholder ones ("Ggg") are dropped.
Usage: python -I gp2.py <pdf> <tools/folders dir>"""
import sys, json, os, re
import pymupdf
sys.stdout.reconfigure(encoding='utf-8')
d = pymupdf.open(sys.argv[1]); T = sys.argv[2]
L = []                                      # (text, highlighted)
for p in d:
    hl = [a.rect for a in p.annots() if a.type[1] == 'Highlight']
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            r = pymupdf.Rect(l['bbox']); t = ''.join(s['text'] for s in l['spans']).replace('120”', '120°')
            if not t.strip(): continue
            on = any((h & r).height > r.height * .5 and (h & r).width > 8 for h in hl)
            L.append((t.strip(), on))
qs, cur = [], None
for t, on in L:
    m = re.match(r'^Q?(\d+)\s*/\s*1?100\b', t)
    if m: cur = {'n': int(m[1]), 'q': [], 'o': []}; qs.append(cur); continue
    if cur is None: continue
    m = re.match(r'^([A-Ea-e])\s*\.\s*(.*)$', t)
    if m: cur['o'].append([m[2], on]); continue
    if cur['o']: cur['o'][-1][0] += ' ' + t; cur['o'][-1][1] |= on
    else: cur['q'].append(t)
out, bad = [], []
for q in qs:
    stem = re.sub(r'\s+', ' ', ' '.join(q['q'])).strip()
    o = [(re.sub(r'\s+', ' ', x).strip(), on) for x, on in q['o']]
    o = [x for x in o if x[0] and not re.fullmatch(r'(?i)g+', x[0])]
    a = [i for i, x in enumerate(o) if x[1]]
    if len(o) < 2 or len(a) != 1: bad.append((q['n'], f'{len(o)} options, {len(a)} marked', stem)); continue
    out.append({'q': stem, 'o': [x[0] for x in o], 'a': a})
# two answers the file highlights wrongly
FIX = {"Charles’ law states that": ('Volume varies directly with temperature', "The file highlights 'Volume equals pressure x temperature'; Charles' law is volume proportional to temperature."),
       'Lateral stability is reduced by increasing': ('Anhedral', 'The file highlights Dihedral; dihedral (and sweepback) add lateral stability, anhedral reduces it.')}
for q in out:
    if q['q'] in FIX: q['a'] = [q['o'].index(FIX[q['q']][0])]; q['x'] = FIX[q['q']][1]
# the file types a few questions twice with a small slip ("performed be" / "performed by", a missing colon): keep the first
import difflib
norm = lambda t: re.sub(r'[^a-z0-9]+', ' ', t.lower()).strip()
keep = []
for q in out:
    sim = lambda a, b: difflib.SequenceMatcher(None, norm(a), norm(b)).ratio() > .85
    if not any(len(q['o']) == len(k['o']) and q['a'] == k['a'] and sim(q['q'], k['q']) and all(sim(a, b) for a, b in zip(q['o'], k['o'])) for k in keep): keep.append(q)
print(len(out) - len(keep), 'typed twice'); out = keep
print(len(qs), 'found', len(out), 'questions', {n: sum(len(q['o']) == n for q in out) for n in (2, 3, 4)})
print('numbers missing:', sorted(set(range(1, 101)) - {q['n'] for q in qs}))
for b in bad: print('  SKIP Q%d' % b[0], b[1], '|', b[2][:90])
json.dump(out, open(os.path.join(T, 'in', 'gp2.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
