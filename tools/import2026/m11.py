import sys, re, json, collections
sys.stdout.reconfigure(encoding='utf-8')
L = open(sys.argv[1], encoding='utf-8').read().split('\n')
SEC = [('11.01', 'af-aero'), ('11.2', 'af-struct'), ('11.03', 'af-struct'), ('11.04', 'af-aircon'), ('11.05', 'af-instr'), ('11.06', 'af-elec'),
       ('11.07', 'af-equip'), ('11.08', 'af-equip'), ('11.09', 'af-fctl'), ('11.10', 'af-fuel'), ('11.11', 'af-hyd'), ('11.12', 'af-ice'),
       ('11.13', 'af-gear'), ('11.14', 'af-lox'), ('11.15', 'af-lox'), ('11.16', 'af-lox'), ('11.18', 'af-misc')]
k = lambda t: re.sub(r'[^a-z0-9]', '', t.lower())
def clean(t): return re.sub(r'\s+', ' ', t).strip()
def strip_dot(t):
    t = clean(t)
    t = re.sub(r'\?\.$', '?', t)
    if t.endswith('.') and not re.search(r'(\d|etc|e\.g|i\.e|[A-Z])\.$', t): t = t[:-1]
    return t.replace("\’", "’").replace("\'", "'")
out, bad, cur, sec = [], [], None, None
def flush():
    global cur
    if cur:
        o = [strip_dot(x) for x in cur['o']]; ans = clean(cur['ans'] or '')
        a = None
        m = re.match(r'^([ABC])[\.\)]?\s+(.*)$', ans)
        if m and (not m.group(2) or k(m.group(2))[:12] == k(o['ABC'.index(m.group(1))])[:12] if len(o) > 'ABC'.index(m.group(1)) else False): a = 'ABC'.index(m.group(1))
        if a is None:
            ka = k(re.sub(r'^\.?\s*', '', ans))
            hits = [i for i, x in enumerate(o) if k(x) and (k(x) == ka)]
            if not hits: hits = [i for i, x in enumerate(o) if ka and k(x) and (k(x).startswith(ka) or ka.startswith(k(x)))]
            if len(hits) == 1: a = hits[0]
            elif m: a = 'ABC'.index(m.group(1))
        x = clean(cur['x'] or '')
        if x.upper().rstrip('.') in ('NIL', 'NONE', ''): x = ''
        rec = {'s': cur['sec'], 'q': strip_dot(cur['q']) if not cur['q'].rstrip().endswith('?.') else clean(cur['q'])[:-1], 'o': o, 'a': [a] if a is not None else [], 'x': x}
        (out if a is not None and len(o) >= 2 and rec['q'] else bad).append(rec)
    cur = None
mode = None
for line in L:
    s = line.strip()
    h = re.match(r'^(11\.\d+)', s)
    if h and not s.startswith('Question'):
        flush(); key = h.group(1); key = {'11.1': '11.01'}.get(key, key)
        sec = next((v for p, v in SEC if key == p or key.startswith(p)), sec); mode = None; continue
    m = re.match(r'^Question Number\.?\s*\d+\.?\s*(.*)$', s)
    if m: flush(); cur = {'sec': sec, 'q': m.group(1), 'o': [], 'ans': None, 'x': None}; mode = 'q'; continue
    if not cur: continue
    m = re.match(r'^Option [A-D]\.?\s*(.*)$', s)
    if m: cur['o'].append(m.group(1)); mode = 'o'; continue
    m = re.match(r'^Correct Answer is\.?\s*(.*)$', s)
    if m: cur['ans'] = m.group(1); mode = 'a'; continue
    m = re.match(r'^Explanation\.?\s*(.*)$', s)
    if m: cur['x'] = m.group(1); mode = 'x'; continue
    if not s: continue
    if mode == 'q': cur['q'] += ' ' + s
    elif mode == 'o': cur['o'][-1] += ' ' + s
    elif mode == 'a': cur['ans'] += ' ' + s
    elif mode == 'x': cur['x'] += ' ' + s
flush()
print(len(out), 'ok', len(bad), 'bad'); print(collections.Counter(r['s'] for r in out))
for b in bad[:8]: print('BAD', json.dumps(b, ensure_ascii=False)[:300])
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
json.dump(bad, open(sys.argv[2].replace('.json', '_bad.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
