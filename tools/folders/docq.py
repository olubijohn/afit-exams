"""Questions from the Word .doc dumps (paragraph text + run colours): stem, then options, the red option is the answer.
Stems that wrap onto a second paragraph are joined when the joined text matches a known question."""
import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')
k = lambda t: re.sub(r'[^a-z0-9]', '', t.lower())
def red(p): return any(r[2] in ('#ff0000', '#c00000', '#00b050') for r in p['runs'] if r[0].strip())
def parse(f, known):
    KS = {k(q['q'])[:45] for q in known if len(k(q['q'])) >= 20}
    KO = {k(o)[:40] for q in known for o in q['o']}
    P = [{'t': p['t'].strip(), 'r': red(p)} for p in json.load(open(f, encoding='utf-8')) if p['t'].strip()]
    out, bad, i, failed = [], [], 1, False
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
        if not got:
            # statement-style question (stem, numbered statements, then three options): find the next red answer and
            # take the three options around it that are followed by the next question
            r = next((x for x in range(i + 1, min(i + 14, len(P))) if P[x]['r']), None)
            win = None
            if r is not None:
                for st in (r - 1, r - 2, r):
                    if st <= i or st + 3 > len(P): continue
                    nxt = P[st + 3] if st + 3 < len(P) else None
                    if any(P[x]['r'] for x in range(st, st + 3) if x != r) or (nxt is not None and nxt['r']): continue
                    if any(stemish(P[x]['t']) for x in range(st, st + 3)): continue
                    if nxt is None or stemish(nxt['t']) or len(nxt['t']) > 45 or k(nxt['t'])[:45] in KS:
                        win = st; break
            if win is not None:
                lines = [P[x]['t'] for x in range(i, win)]
                # an earlier question with no marked answer sits in front: start at the last stem line (not "regarding the above")
                cut = [n for n, t in enumerate(lines) if n and re.search(r'[?:;]\s*$', t) and not re.search(r'above', t, re.I)]
                if cut: bad.append(('no answer marked', lines[0])); i += cut[-1]; lines = lines[cut[-1]:]
                stmt = lambda t: re.match(r'^(\(\d\)|\d[\.\)]\s|\(?[ivx]{1,4}[\.\)]\s|regarding the above)', t.strip(), re.I)
                combos = all(re.match(r'^(only|both|neither|all of|none of|[ivx\d]{1,3}\s*,|[ivx\d]{1,3}\s+and\b)', P[x]['t'].strip(), re.I) for x in range(win, win + 3))
                wrapped = all(len(lines[n - 1]) > 40 and not re.search(r'[.?:;]\s*$', lines[n - 1]) for n in range(1, len(lines)))
                # a question whose own answer isn't marked must not borrow the next question's red answer
                # (a wrapped stem only right after a question that was read cleanly, not in the leftovers of a skipped one)
                if not (any(stmt(t) for t in lines[1:]) or combos or (wrapped and len(lines) <= 3 and not failed)): win = None
            if win is not None:
                stem = '\n'.join(re.sub(r'\s+', ' ', P[x]['t']) for x in range(i, win))
                out.append({'q': stem, 'o': [re.sub(r'\s+', ' ', o['t']) for o in P[win:win + 3]], 'a': [r - win]}); i = win + 3; failed = False; continue
            bad.append(('no clean options', q['t'])); i = j if j > i + 1 else i + 1; failed = True; continue
        n, a = got
        out.append({'q': re.sub(r'\s+', ' ', q['t']), 'o': [re.sub(r'\s+', ' ', o['t']) for o in P[j:j + n]], 'a': [a]}); i = j + n; failed = False
    return out, bad
