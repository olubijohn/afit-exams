import sys, re, json
sys.stdout.reconfigure(encoding='utf-8')
def parse(path):
    L = [l.rstrip() for l in open(path, encoding='utf-8').read().split('\n')]
    L = [l for l in L if l.strip() and not re.match(r'^(Pressurized Metal Airframe.*|Study online at .*|\d+ / \d+)$', l.strip())]
    out, cur, bad = [], None, []
    def add_text(t, s):
        t = t.rstrip(); s = s.strip()
        if t.endswith('-') and s[:1].islower(): return t[:-1] + s
        return t + ' ' + s
    def flush():
        if cur:
            o = [re.sub(r'\s+', ' ', x).strip() for x in cur['o']]
            if cur['a'] is not None and cur['a'] < len(o) and len(o) >= 2: out.append({'q': re.sub(r'\s+', ' ', cur['q']).strip(), 'o': o, 'a': [cur['a']], 'n': cur['n']})
            else: bad.append(cur)
    for l in L:
        s = l.strip()
        m = re.match(r'^(\d+)\.\s*(.*)$', s)
        if m and (cur is None or len(cur['o']) >= 2) and (cur is None or 0 < int(m.group(1)) - cur['n'] <= 3):
            q = m.group(2); n = int(m.group(1))
            while re.match(r'^\d+\.\s*', q): n = int(re.match(r'^(\d+)', q).group(1)); q = re.sub(r'^\d+\.\s*', '', q)
            flush(); cur = {'n': n, 'q': q, 'o': [], 'a': None, 'm': 'q'}; continue
        if cur is None: continue
        if re.fullmatch(r'[a-dA-D]', s): cur['a'] = 'abcd'.index(s.lower()); continue
        if s.lower() in ('nil', 'none'): cur['m'] = 'x'; continue
        m = re.match(r'^(?:Option )?([a-dA-D])[\.\)]\s*(.*)$', s)
        if m and 'abcd'.index(m.group(1).lower()) == len(cur['o']): cur['o'].append(m.group(2)); cur['m'] = 'o'; continue
        if cur['m'] == 'x': continue
        if cur['m'] == 'q': cur['q'] = add_text(cur['q'], s)
        else: cur['o'][-1] = add_text(cur['o'][-1], s)
    flush()
    return out, bad
res = []
for f in sys.argv[2:]:
    o, b = parse(f); print(f.rsplit('/',1)[-1], len(o), 'ok', len(b), 'bad', 'last n', o[-1]['n'])
    for x in b[:5]: print('  BAD', json.dumps(x, ensure_ascii=False)[:250])
    for x in o: x['src'] = f.rsplit('/',1)[-1].replace('.txt','') + ' q%d' % x['n']
    res += o
json.dump(res, open(sys.argv[1], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
