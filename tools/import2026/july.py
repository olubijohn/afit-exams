import docx, sys, re, json
sys.stdout.reconfigure(encoding='utf-8')
d = docx.Document(sys.argv[1])
k = lambda t: re.sub(r'[^a-z0-9]', '', t.lower())
def red(p): return any(r.text.strip() and r.font.color is not None and r.font.color.type is not None and str(r.font.color.rgb) in ('FF0000', 'C00000', 'E36C0A') for r in p.runs)
P = [(p.text, red(p)) for p in d.paragraphs if p.text.strip()]
out, bad, i = [], [], 0
def tidy(t):
    t = re.sub(r'\s+', ' ', t).strip(); t = re.sub(r'\?\.$', '?', t)
    if t.endswith('.') and not re.search(r'(\d|etc|[A-Z])\.$', t): t = t[:-1]
    return t
while i < len(P):
    q, _ = P[i]
    if re.match(r'^(Option [A-D]\.|Correct Answer|Explanation|[a-d]\))', q.strip()): i += 1; continue
    q = re.sub(r'^\d+\.\s*', '', q.strip()); i += 1
    while i < len(P) and P[i][0][:1] in '\t ' and len(P[i][0].strip()) < 25: q += ' ' + P[i][0].strip(); i += 1
    opts, ans, x = [], None, ''
    if i < len(P) and re.match(r'^Option A\.', P[i][0].strip()):
        while i < len(P) and re.match(r'^Option [A-D]\.', P[i][0].strip()):
            opts.append(re.sub(r'^Option [A-D]\.\s*', '', P[i][0].strip()));
            if P[i][1]: ans = len(opts) - 1
            i += 1
        if i < len(P) and P[i][0].strip().startswith('Correct Answer'):
            t = re.sub(r'^Correct Answer is\s*[A-D]?\.?\s*', '', P[i][0].strip()); i += 1
            hits = [j for j, o in enumerate(opts) if k(o) == k(t)] or [j for j, o in enumerate(opts) if k(t) and (k(o).startswith(k(t)) or k(t).startswith(k(o)))]
            if len(hits) == 1: ans = hits[0]
        if i < len(P) and P[i][0].strip().startswith('Explanation'):
            x = re.sub(r'^Explanation\.?\s*', '', P[i][0].strip()); i += 1
            if x.upper().rstrip('.') in ('NIL', ''): x = ''
    elif i < len(P) and re.match(r'^[a-d]\)', P[i][0].strip()):
        while i < len(P) and re.match(r'^[a-d]\)', P[i][0].strip()):
            opts.append(re.sub(r'^[a-d]\)\s*', '', P[i][0].strip()))
            if P[i][1]: ans = len(opts) - 1
            i += 1
    else:
        for _ in range(3):
            if i < len(P): opts.append(P[i][0].strip()); ans = len(opts) - 1 if P[i][1] else ans; i += 1
    rec = {'q': tidy(q), 'o': [tidy(o) for o in opts], 'a': [ans] if ans is not None else [], 'x': x}
    (out if ans is not None and len(opts) >= 2 and not re.match(r'^[?.\s]+$', rec['q']) and len(k(rec['q'])) > 8 else bad).append(rec)
print(len(out), 'ok', len(bad), 'bad')
for b in bad: print(' BAD', json.dumps(b, ensure_ascii=False)[:200])
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
