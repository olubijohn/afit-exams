"""DIRECT_READING_COMPASS_QUESTIONS.pdf -> in/compass.json (one folder, the file's own order).
The file has a few sections typed differently:
  - "1." then the question, options "a)" / "a." on their own line with the text on the next line; the answer is in GREEN
  - "Q1. ..." with options "A. ..." on one line; the answer is in RED, often followed by "Answer A."
In the green sections, red text is the typist's own note (e.g. "(I think)", "(supposed to be 'at the magnetic equator')"):
it is kept out of the option text. Questions with no options (a statement, or a worked answer only) are left out.
Usage: python -I compass.py <pdf> <tools/folders dir>"""
import sys, json, os, re, difflib
import pymupdf
sys.stdout.reconfigure(encoding='utf-8')
d = pymupdf.open(sys.argv[1]); T = sys.argv[2]
RED, GREEN = 16711680, 45136
L = []                                     # (text, colour flag, red-only text)
for p in d:
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            sp = [s for s in l['spans'] if s['text'].strip()]
            if not sp: continue
            spans = [(s['text'], s['color']) for s in sp]
            # two options typed on one line ("b) 10   c) 1"): split it at the second label, keeping colours
            chars = [(ch, c) for t, c in spans for ch in t]; txt = ''.join(ch for ch, _ in chars)
            # labels inside a line: "b) 10", "(a) True", or a row "A. 10 Inches     B. 20 Inches". Only the next letter in
            # order, in the same style as the line's own label, counts ("180* (c) and 360* (c)" and "(a) and (b)" are text)
            cuts = []
            st = re.match(r'^\s*(\()?([a-eA-E])\s*([.)])', txt)
            paren, nxt, mark = (st[1] or '', chr(ord(st[2]) + 1), st[3]) if st else ('', None, ')')
            for m in re.finditer(r'\s{2,}(\(?)([a-eA-E])(\s*[.)])\s', txt):   # a wide gap before it: a real label
                if m.start(2) == 0 or (st and m.start(2) <= st.end(2)): continue
                if nxt is None and m[3].strip() == ')': nxt, paren, mark = m[2], m[1], ')'   # "100   b) 10   c) 1" under a bare "a)"
                if m[2] == nxt and m[3].strip() == mark and m[1] == paren:
                    cuts.append(m.start(1) if m[1] else m.start(2)); nxt = chr(ord(nxt) + 1)
            for a0, a1 in zip([0] + cuts, cuts + [len(chars)]):
                part = chars[a0:a1]; seg = []
                for ch, c in part:
                    if seg and seg[-1][1] == c: seg[-1] = (seg[-1][0] + ch, c)
                    else: seg.append((ch, c))
                L.append(seg)

Q_START = re.compile(r'^\s*Q?\s*(\d+)\s*\.{0,2}\s*(?=\S|$)(.*)$')
OPT = re.compile(r'^\s*[/(]?\s*([A-Ea-e])\s*[.)]\s*(.*)$')
ANS = re.compile(r'^\s*Answer\s*[:\-]?\s*([A-Ea-e])\b', re.I)
qs, cur, opt_label_pending = [], None, None
def text(spans, drop_red=False): return re.sub(r'\s+', ' ', ''.join(t for t, c in spans if not (drop_red and c == RED))).strip()
for spans in L:
    t = text(spans); cols = {c for _, c in spans}
    m = ANS.match(t)
    if m and cur: cur['ans'] = m[1].lower(); continue
    m = OPT.match(t)
    if m and cur is not None and not re.match(r'^\s*\d', t):
        cur['o'].append({'t': '', 'g': GREEN in cols, 'r': RED in cols, 'raw': []})
        rest = [(tt, c) for tt, c in spans]
        # drop the label itself from the first span
        first = re.sub(r'^\s*[/(]?\s*[A-Ea-e]\s*[.)]\s*', '', rest[0][0]); rest[0] = (first, rest[0][1])
        cur['o'][-1]['raw'] += rest
        continue
    if cur and cur['o'] and not text(cur['o'][-1]['raw']).strip() and not re.match(r'^\s*Q?\s*\d+\s*\.{1,2}\s*$', t):   # the text under a bare "a)" label
        cur['o'][-1]['raw'] += spans; continue
    m = Q_START.match(t)
    is_q = m and (m[2].strip() == '' or (len(m[2]) > 3 and not re.match(r'^\d', m[2])))
    if is_q and not (cur and cur['o'] == [] and not cur['q'] and m[2].strip() == ''):
        cur = {'n': int(m[1]), 'q': [m[2]] if m[2].strip() else [], 'o': [], 'ans': None, 'qcols': set()}; qs.append(cur); continue
    if cur is None: continue
    if re.fullmatch(r'[A-Z0-9 .,&()\-]{12,}', t) and t.upper() == t and len(t.split()) >= 2:   # a section heading
        cur = None; continue
    if cur['o']: cur['o'][-1]['raw'] += spans; cur['o'][-1]['g'] |= GREEN in cols; cur['o'][-1]['r'] |= RED in cols
    else: cur['q'].append(t); cur['qcols'] |= cols

out, bad = [], []
for q in qs:
    stem = re.sub(r'\s+', ' ', ' '.join(q['q'])).strip()
    share = lambda o, col: (lambda tot: sum(len(t.strip()) for t, c in o['raw'] if c == col) / tot if tot else 0)(sum(len(t.strip()) for t, c in o['raw']))
    for o in q['o']: o['g'] = share(o, GREEN) > .5; o['r'] = share(o, RED) > .5
    anyg = any(o['g'] for o in q['o'])
    opts = []
    for o in q['o']:
        tx = re.sub(r'\s*\(I think\)', '', text(o['raw'])).strip()   # the typist's own doubt is not part of the option
        note = ''
        if tx.strip(' .') == '': continue
        opts.append({'t': tx, 'm': o['g'] if anyg else o['r'], 'note': note})
    a = [i for i, o in enumerate(opts) if o['m']]
    if not a and q['ans']: a = [ord(q['ans']) - 97] if ord(q['ans']) - 97 < len(opts) else []
    if len(opts) < 2 or len(a) != 1 or not stem: bad.append((q['n'], f'{len(opts)} options, {len(a)} marked', stem)); continue
    stem = stem.replace('|E –', 'E –').replace('400\Hz', '400 Hz')
    item = {'q': stem, 'o': [o['t'] for o in opts], 'a': a}
    notes = [o['note'] for o in opts if o['note'] and not o['m']] + [o['note'] for o in opts if o['note'] and o['m']]
    if notes: item['x'] = 'Note in the file: ' + '; '.join(n.strip('() ') for n in notes)
    out.append(item)
norm = lambda t: re.sub(r'[^a-z0-9]+', ' ', t.lower()).strip()
sim = lambda a, b: difflib.SequenceMatcher(None, norm(a), norm(b)).ratio() > .9
keep = []
for q in out:
    if not any(len(q['o']) == len(k['o']) and q['a'] == k['a'] and sim(q['q'], k['q']) and all(sim(x, y) for x, y in zip(q['o'], k['o'])) for k in keep): keep.append(q)
print(len(qs), 'found', len(out), 'read', len(out) - len(keep), 'asked twice ->', len(keep), {n: sum(len(q['o']) == n for q in keep) for n in (2, 3, 4, 5)})
for b in bad: print('  SKIP Q%s' % b[0], b[1], '|', b[2][:90])
json.dump(keep, open(os.path.join(T, 'in', 'compass.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
