"""Add the Oct 2026 files to data/questions.json and group the subjects into three papers.
General paper  <- GENERAL PAPER.pdf (new questions only, each filed under its closest general subject)
Pressurised    <- NCAA AIRFRAME.docx (EASA Module 11 bank, split by chapter),
                  AME PART 1/2 (Quizlet) and AIRFRAME QUESTION - JULY 2019 (new ones go into NCAA past papers)
Re-runnable: earlier output of this script is removed first.  Usage: python -I merge.py"""
import json, re, sys, math, collections, os
sys.stdout.reconfigure(encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
from fuzzy import match, k
DATA = os.path.join(H, '..', '..', 'data', 'questions.json')
L = lambda f: json.load(open(os.path.join(H, f), encoding='utf-8'))
B = json.load(open(DATA, encoding='utf-8'))
MINE = ('GENERAL PAPER 2026', 'NCAA AIRFRAME (Module 11)', 'AME (Quizlet)', 'AIRFRAME JULY 2019')
Q = [q for q in B['questions'] if q.get('src') not in MINE]

GEN = ['law', 'aero1', 'aero2', 'sheet', 'hardware', 'drawing', 'hf1', 'hf2']
AF = [('af-aero', 'Aeroplane Aerodynamics', 'AER'), ('af-struct', 'Airframe Structures', 'STR'), ('af-aircon', 'Air Conditioning & Pressurisation', 'AC'),
      ('af-instr', 'Instruments & Avionics', 'INS'), ('af-elec', 'Electrical Power', 'ELE'), ('af-equip', 'Equipment, Furnishings & Fire', 'EQP'),
      ('af-fctl', 'Flight Controls', 'FCT'), ('af-fuel', 'Fuel Systems', 'FUE'), ('af-hyd', 'Hydraulic Power', 'HYD'), ('af-ice', 'Ice & Rain Protection', 'ICE'),
      ('af-gear', 'Landing Gear', 'LG'), ('af-lox', 'Lights, Oxygen & Pneumatics', 'LOX'), ('af-misc', 'Mixed Systems', 'MIX')]
next_n = collections.Counter()
for q in Q: next_n[q['s']] = max(next_n[q['s']], q['n'])
def add(s, q, src):
    if len({k(o) for o in q['o']}) < len(q['o']): return None   # the source repeats an option: can't be marked fairly
    next_n[s] += 1
    o = [re.sub(r'(?<=[a-z\)])\.$', '', x.strip()) for x in q['o']]
    r = {'id': f'{s}-{next_n[s]}', 's': s, 'n': next_n[s], 'q': q['q'].strip(), 'o': o, 'a': q['a']}
    x = re.sub(r'^(NIL|Nil|nil)\.?\s*', '', (q.get('x') or '').strip())
    if x: r['x'] = x
    r['src'] = src; Q.append(r); return r

# ---- General paper: new questions only, filed by nearest neighbours (tf-idf over the existing general questions) ----
gen_old = [q for q in Q if q['s'] in GEN]
gp = [q for q in L('gp.json') if not re.search(r'figure|diagram|shown', q['q'], re.I)]
gp_new = [q for q, o, s in match(gp, gen_old, 0.85) if not (o and s > 0.7)]
tok = lambda q: re.findall(r'[a-z]{3,}', (q['q'] + ' ' + ' '.join(q['o'])).lower())
df = collections.Counter(w for q in gen_old for w in set(tok(q))); N = len(gen_old)
def vec(q):
    c = collections.Counter(tok(q)); v = {w: (1 + math.log(n)) * math.log((N + 1) / (df.get(w, 0) + 1)) for w, n in c.items()}
    z = math.sqrt(sum(x * x for x in v.values())) or 1
    return {w: x / z for w, x in v.items()}
V = [(vec(q), q['s']) for q in gen_old]
filed = collections.Counter()
for q in gp_new:
    v = vec(q); sc = sorted(((sum(x * u.get(w, 0) for w, x in v.items()), s) for u, s in V), reverse=True)[:7]
    vote = collections.Counter()
    for c, s in sc: vote[s] += c
    s = vote.most_common(1)[0][0]; add(s, q, 'GENERAL PAPER 2026'); filed[s] += 1
print('general paper: parsed', len(gp), 'new', len(gp_new), dict(filed))

# ---- Module 11 bank: dedupe inside itself and against the NCAA past papers ----
pma_old = [q for q in Q if q['s'] == 'pma']
m11 = L('m11.json'); seen = set(); m11u = []
for q in m11:
    kk = (k(q['q'])[:90], tuple(sorted(k(o)[:40] for o in q['o'])))
    if kk not in seen: seen.add(kk); m11u.append(q)
m11n = [q for q, o, s in match(m11u, pma_old, 0.9) if not (o and s > 0.8)]
keep, by = [], collections.defaultdict(list)
for q in m11n:   # near-identical repeats inside the bank (some chapters appear twice in the source)
    r = match([q], by[q['s']], 0.93) if by[q['s']] else [(q, None, 0)]
    if r[0][1] and r[0][2] > 0.88: continue
    keep.append(q); by[q['s']].append(q)
cnt = collections.Counter()
for q in keep: add(q['s'], q, 'NCAA AIRFRAME (Module 11)'); cnt[q['s']] += 1
print('module 11: parsed', len(m11), 'unique', len(m11u), 'not in past papers', len(m11n), 'kept', len(keep), dict(cnt))

# ---- AME parts + July 2019: new ones into NCAA past papers ----
pool = [q for q in Q if q['s'] == 'pma' or q['s'].startswith('af-')]
for name, f in (('AME (Quizlet)', 'ame.json'), ('AIRFRAME JULY 2019', 'july.json')):
    arr = L(f); new = [q for q, o, s in match(arr, pool, 0.85) if not (o and s > 0.7)]
    # July 2019's unmatched leftovers are misaligned fragments of its unlabelled layout: only clean ones count
    new = [q for q in new if len(set(k(o) for o in q['o'])) == len(q['o']) and not any(re.search(r'\?|^How |^What |Option [A-D]', o) for o in q['o'])]
    if f == 'july.json': new = []
    for q in new: r = add('pma', q, name); r and pool.append(r)
    print(name, 'parsed', len(arr), 'new', len(new))

# ---- subjects grouped into papers ----
names = {s['id']: s['name'] for s in B['subjects']}
names['pma'] = 'NCAA Past Papers'
subs = [{'id': s, 'name': names[s], 'paper': 'general'} for s in GEN] + [{'id': 'piston', 'name': names['piston'], 'paper': 'piston'}] \
     + [{'id': 'pma', 'name': names['pma'], 'paper': 'pma', 'short': 'PP'}] + [{'id': i, 'name': n, 'paper': 'pma', 'short': sh} for i, n, sh in AF]
c = collections.Counter(q['s'] for q in Q)
for s in subs: s['count'] = c[s['id']]
order = {s['id']: i for i, s in enumerate(subs)}
Q.sort(key=lambda q: (order[q['s']], q['n']))
B['subjects'] = [s for s in subs if s['count']]
B['papers'] = [{'id': 'general', 'name': 'General Paper', 'short': 'General'}, {'id': 'piston', 'name': 'Piston Engines', 'short': 'Piston'},
               {'id': 'pma', 'name': 'Pressurised Airframe', 'short': 'Pressurised'}]
B['source'] = ('GENERAL PAPER (NCAT, two sets); SLIDE ON PISTON AND SYSTEMS; PRESSURISED METAL AIRFRAME (NCAA papers, 200+ licence exam, '
               'PMA 2019, 2018 exams, AME Quizlet parts 1-2, July 2019); NCAA AIRFRAME Module 11 bank')
B['questions'] = Q
json.dump(B, open(DATA, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('total', len(Q), {p['id']: sum(s['count'] for s in B['subjects'] if s['paper'] == p['id']) for p in B['papers']})
