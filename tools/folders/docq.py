"""Questions from the Word .doc dumps (paragraph text + run colours): stem, then options, the red option is the answer.
Stems that wrap onto a second paragraph are joined when the joined text matches a known question."""
import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')
k = lambda t: re.sub(r'[^a-z0-9]', '', t.lower())
def red(p): return any(r[2] in ('#ff0000', '#c00000') for r in p['runs'] if r[0].strip())
def parse(f, known):
    KS = {k(q['q'])[:45] for q in known if len(k(q['q'])) >= 20}
    KO = {k(o)[:40] for q in known for o in q['o']}
    P = [{'t': p['t'].strip(), 'r': red(p)} for p in json.load(open(f, encoding='utf-8')) if p['t'].strip()]
    out, bad, i = [], [], 1
    stemish = lambda t: bool(re.search(r'[?:]$|_{2,}$|\.{3,}$|…$', t.strip()))
    while i < len(P):
        q = dict(P[i]); j = i + 1
        if q['r']: bad.append(('red stem', q['t'])); i += 1; continue
        # a stem that wraps onto the next paragraph(s)
        while j < len(P) and not P[j]['r'] and ((not stemish(q['t']) and stemish(P[j]['t']) and k(P[j]['t'])[:40] not in KO) or (k(q['t'])[:45] not in KS and k(q['t'] + ' ' + P[j]['t'])[:45] in KS)):
            q['t'] += ' ' + P[j]['t']; j += 1
        got = None
        for n in (3, 4, 2):
            opts = P[j:j + n]; nxt = P[j + n] if j + n < len(P) else None
            if len(opts) < n or sum(o['r'] for o in opts) != 1 or any(stemish(o['t']) for o in opts): continue
            if nxt is not None and nxt['r']: continue
            if n != 3 and nxt is not None and not (stemish(nxt['t']) or k(nxt['t'])[:45] in KS): continue
            got = (n, [o['r'] for o in opts].index(True)); break
        if not got: bad.append(('no clean options', q['t'])); i = j if j > i + 1 else i + 1; continue
        n, a = got
        out.append({'q': re.sub(r'\s+', ' ', q['t']), 'o': [re.sub(r'\s+', ' ', o['t']) for o in P[j:j + n]], 'a': [a]}); i = j + n
    return out, bad
