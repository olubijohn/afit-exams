# Extracts questions from "SLIDE ON PISTON AND SYSTEMS.pdf": the answer is the highlighted (or red) option.
# Usage: python tools/extract_piston_slides.py "<pdf>" out.json
import pymupdf, sys, re, json, unicodedata, collections
sys.stdout.reconfigure(encoding='utf-8')
d = pymupdf.open(sys.argv[1])
RED = {0xff0000}
MARK_RE = re.compile(r'^\s*(?:[◦•▪]|[a-dA-D]\s*[).]|\(?[a-dA-D]\))\s*')
LETTER_RE = re.compile(r'^\s*\(?([a-dA-D])\s*[).]\s*')

def fix(t):
    t = t.replace('⁰', '°').replace('º', '°').replace('ﬁ', 'fi').replace('ﬂ', 'fl').replace(' ', ' ')
    return unicodedata.normalize('NFC', t)

def norm(t):
    t = fix(t)
    t = re.sub(r'[-]', '', t)          # Wingdings glyphs
    return re.sub(r'\s+', ' ', t).strip()

SUP = str.maketrans('0123456789+-', '⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻')

def sup(s):
    """raised text: a raised 0/o after a number is a degree sign, other raised digits stay superscript"""
    t = s['text']
    if not s['flags'] & 1 or not t.strip(): return t
    if t.strip() in ('0', 'o', 'O'): return '°'
    return t.translate(SUP)

def hl_rects(p):
    out = []
    for a in p.annots():
        v = a.vertices or []
        for i in range(0, len(v) - 3, 4):
            xs = [q[0] for q in v[i:i + 4]]; ys = [q[1] for q in v[i:i + 4]]
            out.append(pymupdf.Rect(min(xs), min(ys), max(xs), max(ys)))
    return out

def rows(p):
    hl = hl_rects(p)
    raw = []
    for b in p.get_text('dict')['blocks']:
        if b['type'] != 0: continue
        for l in b['lines']:
            r = pymupdf.Rect(l['bbox'])
            if r.y0 > 452: continue                      # footer/logo
            t = ''.join(sup(s) for s in l['spans'])
            if not norm(t) and '◦' not in t: continue
            h = any((r & x).get_area() > 0.4 * r.get_area() for x in hl)
            red = any(s['color'] in RED and s['text'].strip() for s in l['spans'])
            raw.append([r.x0, r.y0, r.y1, t, h, red])
    raw.sort(key=lambda z: (round(z[1] / 6), z[0]))
    merged = []                                          # join pieces on the same visual row (bullet + text)
    for x0, y0, y1, t, h, red in raw:
        if merged and abs(merged[-1]['y'] - y0) < 6:
            m = merged[-1]; m['t'] += ' ' + t; m['h'] |= h; m['red'] |= red
        else:
            merged.append({'x': x0, 'y': y0, 't': t, 'h': h, 'red': red})
    for m in merged:
        m['t'] = fix(m['t'])
        m['mark'] = bool(MARK_RE.match(m['t'])) and bool(norm(MARK_RE.sub('', m['t'], 1)))
        m['bullet_only'] = norm(MARK_RE.sub('', m['t'], 1)) == ''
    return [m for m in merged if not m['bullet_only']]

COMBO_RE = re.compile(r'^(?:[\dI](?:(?:\s*(?:,|and/or|and|or|&))+\s*[\dI])+\.?|only no\.? ?\d.*|neither .*|both .*)$', re.I)

def split(rs):
    """first row = question; returns (question_rows, statement_groups, [option_rows...])"""
    k = len(rs)
    while k > 0 and COMBO_RE.match(norm(MARK_RE.sub('', rs[k - 1]['t'], 1))): k -= 1
    if len(rs) - k >= 2 and k >= 2:
        return rs[:1], [[r] for r in rs[1:k]], [[r] for r in rs[k:]]
    letters = [i for i, r in enumerate(rs) if LETTER_RE.match(r['t'])]
    if len(letters) >= 2 and letters[0] > 0:
        starts = letters
    else:
        marks = [i for i, r in enumerate(rs) if r['mark']]
        if len(marks) >= 3:
            starts = [i for i in marks if i > 0] if marks[0] == 0 else marks
        else:
            if len(rs) < 2: return rs, [], []
            minx = min(r['x'] for r in rs[1:])
            starts = [i for i, r in enumerate(rs) if i > 0 and r['x'] <= minx + 4]
    if not starts: return rs, [], []
    q = rs[:starts[0]]
    opts = [rs[a:b] for a, b in zip(starts, starts[1:] + [len(rs)])]
    if len(opts) > 4:                      # statements listed as separate lines, combinations last
        return q, opts[:-3], opts[-3:]
    return q, [], opts

# slides where the marking itself is wrong (checked by hand)
FIX = {37: ([3], 'Both a) and d) were highlighted on the slide; detonation comes from fuel with too LOW an octane rating, so d) is the answer.')}
FIXQ = {288: '(1) Cast iron piston rings may be used in chrome plated cylinders.\n(2) Chrome plated rings may be used in plain steel cylinders.\nRegarding the above statements,'}
out, odd = [], []
for pn in range(1, len(d)):
    rs = rows(d[pn])
    if not rs: continue
    q, groups, opts = split(rs)
    qt = norm(MARK_RE.sub('', ' '.join(r['t'] for r in q), 1))
    if groups:
        # statements to choose from ("1. ... 2. ...") go on their own lines, numbered
        texts_ = [norm(MARK_RE.sub('', ' '.join(r['t'] for r in g), 1)) for g in groups]
        stm = []
        for t in texts_:
            if not stm and t[:1].islower() and not qt.rstrip().endswith(('?', ':')): qt += ' ' + t   # question carried on
            elif stm and t[:1].islower() and not re.match(r'^\(?\d', t): stm[-1] += ' ' + t
            else: stm.append(t)
        if stm and not any(re.match(r'^\(?\d', t) for t in stm):
            stm = [f'{i + 1}. {t}' for i, t in enumerate(stm)]
        qt += ''.join(chr(10) + t for t in stm)
    qt = re.sub(r'^\d{1,3}\s*[.)]\s*', '', qt)
    if pn + 1 in FIXQ: qt = FIXQ[pn + 1]
    texts = [norm(LETTER_RE.sub('', MARK_RE.sub('', ' '.join(r['t'] for r in o), 1), 1)) for o in opts]
    hmark = [any(r['h'] for r in o) for o in opts]
    rmark = [any(r['red'] for r in o) for o in opts]
    mark = hmark if any(hmark) else rmark
    ans = [i for i, m in enumerate(mark) if m]
    note = ''
    # a highlighted last line that is working ("(28+180+165)= 373", "F=BIL") is an explanation, not an option
    if len(texts) == 4 and len(ans) == 2 and 3 in ans and (re.search(r'[=+]', texts[3]) or len(texts[3]) <= 3):
        note = texts.pop(); ans = [i for i in ans if i != 3]
    if pn + 1 in FIX: ans, note = FIX[pn + 1]
    item = {'page': pn + 1, 'q': qt, 'o': texts, 'a': ans, 'via': 'highlight' if any(hmark) else 'red' if any(rmark) else 'none'}
    if note: item['x'] = note
    out.append(item)
    if len(texts) not in (3, 4) or len(ans) != 1 or not qt or any(not t for t in texts):
        odd.append(item)
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('slides with a question:', len(out))
print('options:', collections.Counter(len(x['o']) for x in out))
print('answer source:', collections.Counter(x['via'] for x in out))
print('marked answers per question:', collections.Counter(len(x['a']) for x in out))
print('odd:', len(odd))
for x in odd: print(f"  p{x['page']} a={x['a']} via={x['via']} | {x['q'][:70]} | {[t[:35] for t in x['o']]}")
