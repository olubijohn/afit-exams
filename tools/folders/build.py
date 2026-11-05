"""Build data/questions.json with one folder per file that was sent, in that file's own order.
Papers: General Paper, Piston Engines, Pressurised Airframe, Unpressurised Metal Airframe, Gas Turbine Engine, Compass. Each folder holds the file's questions;
where the file has its own sections (NCAA papers 1-3, Module 11 chapters, the general paper's subjects)
they become sections inside the folder.
Questions that were already in the app keep their id, so people's progress carries over.
Inputs are in in/ (parsed copies of each file; base.json is the bank before the folders).
Usage: python -I build.py"""
import json, re, sys, os, glob, collections
sys.stdout.reconfigure(encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__))
I = lambda f: json.load(open(os.path.join(H, 'in', f), encoding='utf-8'))
DATA = os.path.join(H, '..', '..', 'data', 'questions.json')
k = lambda t: re.sub(r'[^a-z0-9]', '', t.lower())

def tidy_q(q):
    q = re.sub(r'\s+', ' ', q).strip()
    q = re.sub(r'\s*\?\s*\.$', '?', q)
    return q
def tidy_o(o):
    o = re.sub(r'\s+', ' ', o).strip()
    return o if re.search(r'\d\.$', o) else re.sub(r'(?<=[A-Za-z\)])\.$', '', o)

base = I('base.json')
GEN = ['law', 'aero1', 'aero2', 'sheet', 'hardware', 'drawing', 'hf1', 'hf2']
gen_old = [q for q in base['questions'] if q['s'] in GEN]
piston = [q for q in base['questions'] if q['s'] == 'piston']
names = {s['id']: s['name'] for s in base['subjects']}

# old pressurised ids: which file each came from (same filter as tools/pma/export_pma.py)
DROP = ['positive pressure signals from', 'mixing chamber ha', 'identification of the horn for the landing gear', 'over pressure is usually caused by']
merged = [it for it in I('merged.json') if not any(x in it['q'].lower() for x in DROP) and 'Option A.' not in it['q']]
old_pma = {q['id']: q for q in base['questions'] if q['s'] == 'pma'}
assert len(merged) == len(old_pma) == 527
SRC = {'NCAA': 'ncaa', '200+': 'p200', 'PMA 2019 scan': 'pma19'}
reuse = {}
for n, it in enumerate(merged, 1):
    f = next(v for p, v in SRC.items() if it['src'].startswith(p))
    reuse.setdefault((f, k(tidy_q(it['q']))[:90]), f'pma-{n}')
    reuse.setdefault(('any', k(tidy_q(it['q']))[:60]), f'pma-{n}')

folders, subjects, Q, used = [], [], [], set()
# a question that an earlier (more original) file of the same paper already has is left out: each question appears once per paper
audit = {}
prior = collections.defaultdict(lambda: collections.defaultdict(list)); dropped = collections.Counter()
def is_repeat(paper, q, uo):
    ok = {k(x)[:20] for x in uo}
    return any(len(ok & other) >= 2 for other in prior[paper][k(q)[:70]])
def folder(fid, name, paper, sections, topics=False):
    """sections: list of (subject id, section name or None, [questions]); topics=True opens the folder onto its sections"""
    folders.append({'id': fid, 'name': name, 'paper': paper, **({'topics': True} if topics else {})})
    tot = 0; audit[name] = collections.Counter()
    for sid, sname, items in sections:
        audit[name]['parsed'] += len(items)
        seen, n = set(), 0
        for it in items:
            o = [tidy_o(x) for x in it['o']]; al = [x for x in (it.get('a') or []) if isinstance(x, int) and 0 <= x < len(o)]
            if not al or len(o) < 2: audit[name]['no answer marked'] += 1; continue          # the file marks no answer
            a = al[0]                                    # some questions are marked with two answers in the file: both count
            # the file prints the same option twice: keep one, answer still points at it
            uo, remap = [], {}
            for i, x in enumerate(o):
                if k(x) in [k(y) for y in uo]: remap[i] = [k(y) for y in uo].index(k(x)); continue
                remap[i] = len(uo); uo.append(x)
            if len(uo) < 2: continue
            q = tidy_q(it['q']); key = (k(q)[:90], tuple(sorted(k(x)[:40] for x in uo)))
            if not k(q) or (key in seen and not it.get('id')): audit[name]['asked twice in the file'] += 1; continue          # repeated inside the same file (questions already in the app stay)
            # every folder keeps its whole file: questions that other files also have are NOT removed (only repeats inside the same file are)
            prior[paper][k(q)[:70]].append({k(x)[:20] for x in uo})
            seen.add(key); n += 1
            qid = it.get('id') or reuse.get((fid, k(q)[:90]))
            if (not qid or qid in used) and paper == 'pma': qid = reuse.get(('any', k(q)[:60]))
            if qid in old_pma and not it.get('id'):   # only when this file gives the same answer, so earlier results still hold
                op = old_pma[qid]
                if k(op['o'][op['a'][0]])[:30] != k(uo[remap[a]])[:30]: qid = None
            if not qid or qid in used: qid = f'{sid}-{n}'
            while qid in used: qid += 'b'
            used.add(qid)
            r = {'id': qid, 's': sid, 'n': n, 'q': q, 'o': uo, 'a': sorted({remap[x] for x in al})}
            x = re.sub(r'^(NIL|Nil|nil)\.?\s*', '', (it.get('x') or '').strip())
            if x: r['x'] = x
            Q.append(r)
        subjects.append({'id': sid, 'name': sname or name, 'folder': fid, 'paper': paper, 'count': n}); tot += n
    print(f'{paper:8} {name:45} {tot:5}' + (f'  ({len(sections)} sections)' if len(sections) > 1 else '') + (f'  {dropped[name]} repeats of earlier files left out' if dropped[name] else ''))

# ---------- General Paper ----------
folder('gp24', 'GENERAL PAPER _240124_171633', 'general', [(s, names[s], [q for q in gen_old if q['s'] == s]) for s in GEN])
gp = [q for q in I('gp.json') if not re.search(r'figure|diagram|shown', q['q'], re.I)]   # 3 need a drawing the app can't show
folder('gp', 'GENERAL PAPER', 'general', [('gp', None, gp)])
deji = [{**q, 'q': re.sub(r'^\d+[.)]\s+', '', q['q'])} for q in I('deji.json')]   # one folder, its topics are not split out
folder('deji', 'General to use (Deji)', 'general', [('deji', None, deji)])
folder('g23', '2023 GENERALS', 'general', [('g23', None, I('g23.json'))])   # one folder, like Deji
folder('gp2', 'GENERAL PAPER 2', 'general', [('gp2', None, I('gp2.json'))])   # one folder, like Deji
folder('comp', 'DIRECT READING COMPASS QUESTIONS', 'compass', [('comp', None, I('compass.json'))])   # its own section, Compass

# ---------- Piston ----------
folder('pist', 'SLIDE ON PISTON AND SYSTEMS', 'piston', [('piston', None, piston)])

# ---------- Pressurised Airframe ----------
# processed from the most original copy down, so a repeat stays in the first file; shown in the order the files are listed
p200 = I('p200.json'); ncaa = I('ncaa.json')
by200 = {k(tidy_q(x['q']))[:90]: x for x in p200 if len(x['a']) == 1}   # the NCAA copy leaves a few unmarked; the 200+ copy marks them
for x in ncaa:
    if len(x['a']) != 1:
        m = by200.get(k(tidy_q(x['q']))[:90])
        if m and k(m['o'][m['a'][0]]) in [k(o) for o in x['o']]: x['a'] = [[k(o) for o in x['o']].index(k(m['o'][m['a'][0]]))]
folder('ncaa', 'PRESSURIZED AIRFRAME NCAA', 'pma', [(f'ncaa-{p}', f'Paper {p}', [x for x in ncaa if x['sect'] == p]) for p in sorted({x['sect'] for x in ncaa})])
folder('p200', '200+PRESSURISED AIRFRAME LICENSE EXAM', 'pma', [('p200', None, p200)])
scan = [{'q': q, 'o': o, 'a': [a]} for f in sorted(glob.glob(os.path.join(H, '..', 'pma', 'scan_*.json'))) for n, q, o, a in json.load(open(f, encoding='utf-8'))]
folder('pma19', 'PMA 2019', 'pma', [('pma19', None, scan)])
m11 = I('m11ch.json'); chs = list(dict.fromkeys(q['s'] for q in m11))
folder('m11', 'NCAA AIRFRAME', 'pma', [('m11-' + c.split(' ')[0].replace('11.', '').replace('.', '-'), c, [q for q in m11 if q['s'] == c]) for c in chs])
folder('pmas', 'PMA 2019 STUDIES-1', 'pma', [('pmas', None, I('PMA 2019 STUDIES-1.q.json'))])
folder('pma18', 'PRESSURISED METAL AIRFRAME2018', 'pma', [('pma18', None, I('PRESSURISED METAL AIRFRAME2018.q.json'))])
ame = I('ame.json')
folder('ame1', 'AME PART 1', 'pma', [('ame1', None, [q for q in ame if q['src'].startswith('AME PART 1')])])
folder('ame2', 'AME PART 2', 'pma', [('ame2', None, [q for q in ame if q['src'].startswith('AME PART 2')])])
folder('jul19', 'AIRFRAME QUESTION - JULY 2019', 'pma', [('jul19', None, I('july.json'))])
# ---------- Unpressurised Metal Airframe ----------
# one folder, the file's own sections in its order (aap14.py: answer = red / green / bold option)
AAP = {'AIRCRAFT GROUND HANDLING': 'gh', 'LANDING GEAR': 'lg', 'AIRCRAFT STRUCTURES': 'str', 'FUEL SYSTEM AAP6': 'fuel',
       'ICE AND RAIN PROTECTION SYSTEM': 'ice', 'HYDRAULICS & PNEUMATIC SYSTEM': 'hyd', 'TYRES': 'tyre', 'WHEELS': 'whl',
       'BRAKES': 'brk', 'ANTI-SKID': 'ask', 'CABIN EQUIPMENT': 'cab', 'AIRCRAFT FIRE PROTECTION SYSTEMS': 'fire',
       'VACUUM SYSTEM': 'vac', 'WATER AND WASTE SYSTEMS': 'ww', 'ELECTRICAL SYSTEM': 'elec'}
folder('aap14', 'UNPRESSURIZED LICENSE AAP14', 'upma', [('aap14-' + AAP[s['name']], s['name'], s['qs']) for s in I('aap14.json')], topics=True)
# ---------- Gas Turbine Engine ----------
# two files, each split into its own topics (gte.py: the Word file's six papers by their headings, the PDF's 15.1-15.22)
G = I('gte.json')
folder('gte24', 'GTE LICENSE EXAM COMPILATION 2024', 'gte', [(f'gte24-{i}', s['name'], s['qs']) for i, s in enumerate(G['doc'], 1)], topics=True)
folder('m15', 'EASA PART 66 BLOG Module 15, Gas Turbine Engine', 'gte', [('m15-' + s['name'].split(' ')[0].split('.')[1], s['name'], s['qs']) for s in G['pdf']], topics=True)
# a slide deck with no topics of its own: one folder (gte_ncaa.py: the bold green option is the answer)
folder('gtencaa', 'GTE General NCAA 1', 'gte', [('gtencaa', None, I('gte_ncaa.json'))])
# ---- Cabin Crew department: tools/cabin/parse_cabin.py reads the files into in/cabin-*.json (one folder per file)
CC = lambda f: I(f'cabin-{f}.json')
folder('cc-airlaw', 'AIR LAW AND PROCEDURES EXAMINATION', 'cc-law', [('cc-airlaw', None, CC('airlaw'))])
folder('cc-mockairlaw34', 'MOCK AIR LAW - 34', 'cc-law', [('cc-mockairlaw34', None, CC('mockairlaw34'))])
folder('cc-b737exam', 'B737 AIRCRAFT TYPE EXAM', 'cc-type', [('cc-b737exam', None, CC('b737exam'))])
folder('cc-progress2', 'AIRCRAFT TYPE B737-300 PROGRESS TEST II', 'cc-type', [('cc-progress2', None, CC('progress2'))])
folder('cc-cctb36', 'CCTB 36 MOCK PAPER II', 'cc-type', [('cc-cctb36', None, CC('cctb36'))])
folder('cc-sep', 'SEP EXAM', 'cc-safety', [('cc-sep', None, CC('sep'))])
folder('cc-dg', 'DANGEROUS GOODS EXAM', 'cc-safety', [('cc-dg', None, CC('dg'))])
folder('cc-firstaid', 'FIRST AID AND AVIATION MEDICINE EXAM', 'cc-safety', [('cc-firstaid', None, CC('firstaid'))])
folder('cc-prep', 'PREPARATORY GUIDE TO FLIGHT ATTENDANT LICENCE EXAM', 'cc-licence',
       [('cc-prep-type', 'Aircraft Type B737', CC('prep-type')), ('cc-prep-gen', 'Air Law / General Paper', CC('prep-gen'))], topics=True)
folder('cc-ncaa2', 'NCAA QUESTIONS 2', 'cc-licence', [('cc-ncaa2', None, CC('ncaa2'))])
CARDS = [{'id': f'card-{i}', **c} for i, c in enumerate(CC('cards'), 1)]
SHOW = ['gp24', 'gp', 'deji', 'g23', 'gp2', 'comp', 'pist', 'p200', 'jul19', 'ame1', 'ame2', 'm11', 'pma19', 'pmas', 'pma18', 'ncaa', 'aap14', 'gte24', 'm15', 'gtencaa',
        'cc-airlaw', 'cc-mockairlaw34', 'cc-b737exam', 'cc-progress2', 'cc-cctb36', 'cc-sep', 'cc-dg', 'cc-firstaid', 'cc-prep', 'cc-ncaa2']
live = {x['folder'] for x in subjects if x['count']}
folders = sorted([fo for fo in folders if fo['id'] in live], key=lambda fo: SHOW.index(fo['id']))   # a file with nothing new is not shown
subjects.sort(key=lambda x: SHOW.index(x['folder']))

kept = sum(1 for q in Q if q['id'] in old_pma or q['s'] in GEN or q['s'] == 'piston')
print('total', len(Q), '| ids kept from before:', kept, '| old pressurised ids kept:', sum(q['id'] in old_pma for q in Q), 'of 527')
# files left with fewer than 20 questions of their own share one folder, so the page isn't full of tiny folders
SMALL = 0   # 0: every file is its own folder, however few questions it has left
for paper in ('general', 'piston', 'pma', 'upma', 'gte', 'compass'):
    tiny = [fo for fo in folders if fo['paper'] == paper and sum(x['count'] for x in subjects if x['folder'] == fo['id']) < SMALL]
    if len(tiny) < 2: continue
    mid = paper + '-other'
    for x in subjects:
        if x['folder'] in [fo['id'] for fo in tiny]: x['name'] = next(fo['name'] for fo in tiny if fo['id'] == x['folder']); x['folder'] = mid
    folders = [fo for fo in folders if fo not in tiny] + [{'id': mid, 'name': 'OTHER FILES', 'paper': paper, 'files': [fo['name'] for fo in tiny]}]
    print(paper, 'OTHER FILES:', [fo['name'] for fo in tiny])
B = {'source': 'One folder per file sent: ' + '; '.join(f['name'] for f in folders),
     'papers': [{'id': 'general', 'name': 'General Paper', 'short': 'General'}, {'id': 'piston', 'name': 'Piston Engines', 'short': 'Piston'},
                {'id': 'pma', 'name': 'Pressurised Airframe', 'short': 'Pressurised'},
                {'id': 'upma', 'name': 'Unpressurised Metal Airframe', 'short': 'Unpressurised'},
                {'id': 'gte', 'name': 'Gas Turbine Engine', 'short': 'Gas Turbine'}, {'id': 'compass', 'name': 'Compass', 'short': 'Compass'},
                {'id': 'cc-law', 'name': 'Air Law & Procedures', 'short': 'Air Law', 'dept': 'cabin'},
                {'id': 'cc-type', 'name': 'Aircraft Type (B737)', 'short': 'B737 Type', 'dept': 'cabin'},
                {'id': 'cc-safety', 'name': 'Safety, Dangerous Goods & Medicine', 'short': 'Safety & DG', 'dept': 'cabin'},
                {'id': 'cc-licence', 'name': 'Licence Preparation', 'short': 'Licence prep', 'dept': 'cabin'}],
     'departments': [{'id': 'ame', 'name': 'Aircraft Maintenance (AME)', 'sub': 'NCAA licence papers: General, Piston, Airframes, Gas Turbine, Compass'},
                     {'id': 'cabin', 'name': 'Cabin Crew', 'sub': 'Air Law, B737 type, safety, dangerous goods, first aid and licence preparation'}],
     'folders': folders, 'subjects': [s for s in subjects if s['count']], 'questions': Q, 'cards': CARDS}
for p in B['papers']: p.setdefault('dept', 'ame')
json.dump(B, open(DATA, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

json.dump(audit, open(os.path.join(H, 'audit.json'), 'w', encoding='utf-8'), indent=1)
