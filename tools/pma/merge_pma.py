"""Merge the pressurised metal airframe sources into one de-duplicated list.
Order: NCAA PDF (papers 1-3), then anything only in the 200+ PDF, then the PMA 2019 scan.
The 200+ PDF and both .doc files are used to fill and cross-check answers.
Usage: python merge_pma.py <pma dir> <out.json>"""
import json, re, sys, glob, os
sys.stdout.reconfigure(encoding='utf-8')
D = sys.argv[1]
L = lambda f: json.load(open(os.path.join(D, f), encoding='utf-8'))
k = lambda t: re.sub(r'[^a-z0-9]', '', t.lower())

def tidy_q(q):
    q = re.sub(r'\s*\?\s*\.$', '?', q.strip())              # "...?." -> "...?"
    q = re.sub(r'(?<=\S) (?=(?:i{1,3}|iv|v|vi)\. )', '\n', q) if re.search(r'(^|\s)i\. ', q) else q
    return q.strip()
def tidy_o(o): return re.sub(r'\s+', ' ', o).strip().rstrip('.').strip() if not re.search(r'\d\.$', o.strip()) else o.strip()

def key(q, o): return (k(q)[:120], tuple(sorted(k(x) for x in o)))

items, seen, conflicts = [], {}, []
def add(src, q, o, a):
    if not q or len(o) < 2 or len(a) != 1: return False
    q, o = tidy_q(q), [tidy_o(x) for x in o]
    kk = key(q, o)
    if kk in seen:
        prev = items[seen[kk]]
        if k(prev['o'][prev['a'][0]]) != k(o[a[0]]): conflicts.append((src, q, prev['o'][prev['a'][0]], o[a[0]]))
        return False
    seen[kk] = len(items); items.append({'q': q, 'o': o, 'a': a, 'src': src}); return True

ncaa, p200 = L('ncaa.json'), L('p200.json')
# answers from the 200+ copy fill gaps in the NCAA copy (same question text and options)
by200 = {key(tidy_q(x['q']), [tidy_o(o) for o in x['o']]): x for x in p200 if len(x['a']) == 1}
filled = 0
for x in ncaa:
    if len(x['a']) != 1:
        m = by200.get(key(tidy_q(x['q']), [tidy_o(o) for o in x['o']]))
        if m: x['a'] = [[k(o) for o in x['o']].index(k(m['o'][m['a'][0]]))]; filled += 1
for x in ncaa: add('NCAA p%d' % x['page'], x['q'], x['o'], x['a'])
n_ncaa = len(items)
for x in p200: add('200+ p%d' % x['page'], x['q'], x['o'], x['a'])
n_200 = len(items) - n_ncaa
scan = [y for f in sorted(glob.glob(os.path.join(D, 'scan_*.json'))) for y in json.load(open(f, encoding='utf-8'))]
for n, q, o, a in scan:
    if a >= 0: add('PMA 2019 scan q%d' % n, q, o, [a])
n_scan = len(items) - n_ncaa - n_200

# cross-check against the .doc copies: red option text of each question
docs = {}
for f in ('PRESSURISED METAL AIRFRAME2018.json', 'PMA 2019 STUDIES-1.json'):
    P = L(f)
    for i, p in enumerate(P):
        if any(r[2] == '#ff0000' for r in p['runs'] if r[0].strip()):
            docs.setdefault(k(p['t'])[:60], 0); docs[k(p['t'])[:60]] += 1
miss_doc = []
for it in items:
    if not it['src'].startswith('NCAA'): continue
    ans = k(it['o'][it['a'][0]])[:60]
    others = [k(x)[:60] for j, x in enumerate(it['o']) if j != it['a'][0]]
    if any(o in docs for o in others) and ans not in docs: miss_doc.append(it)

print('NCAA:', n_ncaa, '(answers filled from 200+:', filled, ')  only in 200+:', n_200, '  scan new:', n_scan, '  total:', len(items))
print('answer conflicts between copies:', len(conflicts))
for c in conflicts: print('  ', c[0], '|', c[1][:70], '| kept:', c[2][:40], '| other:', c[3][:40])
print('NCAA answers where a .doc marks a different option:', len(miss_doc))
for it in miss_doc: print('  ', it['src'], '|', it['q'][:70], '|', it['o'][it['a'][0]][:40])
json.dump(items, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
