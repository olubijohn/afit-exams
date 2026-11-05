"""Cabin Crew department: read the source files in src/ into ../folders/in/cabin-<id>.json (questions) and
../folders/in/cabin-cards.json (study cards: question + written answer). build.py turns them into folders.
How each file marks the answer:
  letter   - a line with just the letter (A/B/C/D) after the options        (Air Law, B737 type exam, First Aid, SEP,
                                                                              Progress Test II, Dangerous Goods)
  highlight- the highlighted option                                          (Mock Air Law 34)
  bold     - the bold option                                                 (CCTB 36 Mock Paper II, PDF)
  key      - an answer key at the back, numbering restarting in each section (Preparatory Guide, PDF)
  Usage: python -I parse_cabin.py"""
import json, os, re, sys, collections
import docx, pymupdf
from docx.oxml.ns import qn
sys.stdout.reconfigure(encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(H, 'src'); OUT = os.path.join(H, '..', 'folders', 'in')
LET = re.compile(r'^\(?([A-Ea-e])\)?\.?$')
ANSLINE = re.compile(r'^(?:ans(?:wer)?\s*[:.\-]?\s*)?\(?([A-Ea-e])\)?\.?$', re.I)
OPTMARK = re.compile(r'^\s*\(?([a-eA-E])[\.\)]\s*')
QNUM = re.compile(r'^\s*(?:Q(?:uestion)?\s*)?\d{1,3}\s*[\.\):]\s*')
HEADER = re.compile(r'^(cabin crew initial training|progress test|final examination|subject\b|time\b|instructions?\b|course\b|duration\b|date\b|sep exam|instruction:|read carefully|answer all|b737 . 300/400/500 aircraft type$|nigerian college|flying school|mastery test)', re.I)
report = {}
SKIPPED = []


def split_inline(t):
    """'(a) x (b) y (c) z' or 'x (b) y (c) z' -> ['x', 'y', 'z']"""
    parts = re.split(r'\s*\(\s*[b-eB-E]\s*\)\s*|	+\s*[b-eB-E][\.\)]\s+|\s{2,}[b-eB-E][\.\)]\s+', t)
    if len(parts) > 1:
        parts[0] = re.sub(r'^\s*\(\s*[aA]\s*\)\s*', '', parts[0])
        return [p.strip() for p in parts if p.strip()]
    return [t]


def docx_paras(path):
    d = docx.Document(path); out = []
    for p in d.paragraphs:
        t = p.text.strip()
        if not t: continue
        pPr = p._p.pPr; num = pPr.find(qn('w:numPr')) if pPr is not None else None
        nid = num.find(qn('w:numId')).get(qn('w:val')) if num is not None and num.find(qn('w:numId')) is not None else None
        tot = sum(len(r.text) for r in p.runs) or 1
        hl = sum(len(r.text) for r in p.runs if r._r.rPr is not None and r._r.rPr.find(qn('w:highlight')) is not None and r._r.rPr.find(qn('w:highlight')).get(qn('w:val')) != 'none') / tot
        out.append({'t': t, 'nid': nid, 'hl': hl})
    return out


def blocks_by_letter(paras, qnid=None):
    """Split at answer-letter lines; in each block the question is the numbered / list-1 / question-looking line,
    the lines after it are the options (inline '(a) .. (b) ..' options are split)."""
    items, cur, bad = [], [], 0
    for p in paras:
        m = ANSLINE.match(p['t'])
        if m and cur:
            lines = [x for x in cur if not HEADER.match(x['t'])]
            qi = None
            for i, x in enumerate(lines):          # the first list-1 / numbered line after the last answer is the question
                if (qnid and x['nid'] == qnid) or QNUM.match(x['t']): qi = i; break
            if qi is None:
                qi = next((i for i, x in enumerate(lines) if re.search(r'(\?|:|…|\.\.\.|-)\s*$', x['t'])), 0)
            if not lines: cur = []; continue
            q = QNUM.sub('', lines[qi]['t']).strip()
            opts = []
            for x in lines[qi + 1:]:
                opts += split_inline(OPTMARK.sub('', x['t']).strip())
            a = 'abcde'.index(m.group(1).lower())
            if len(opts) >= 2 and a < len(opts): items.append({'q': q, 'o': opts, 'a': [a]})
            else: bad += 1; SKIPPED.append((q, opts, m.group(1)))
            cur = []
        else:
            cur.append(p)
    return items, bad


def blocks_by_highlight(paras, qnid):
    items, bad, q, opts = [], 0, None, []
    def flush():
        nonlocal bad
        if q is None: return
        a = [i for i, (_, h) in enumerate(opts) if h > 0.5]
        if len(opts) >= 2 and a: items.append({'q': q, 'o': [o for o, _ in opts], 'a': a})
        else: bad += 1
    for p in paras:
        if p['nid'] == qnid:
            flush(); q, opts = QNUM.sub('', p['t']).strip(), []
        elif q is not None and not HEADER.match(p['t']):
            opts.append((OPTMARK.sub('', p['t']).strip(), p['hl']))
    flush()
    return items, bad


def txt_paras(path):
    return [{'t': l.strip(), 'nid': None, 'hl': 0} for l in open(path, encoding='utf-8') if l.strip()]


def pdf_lines(path, drop=()):
    rows = []
    for page in pymupdf.open(path):
        for b in page.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                sp = [s for s in l['spans'] if s['text'].strip()]
                t = ' '.join(''.join(s['text'] for s in l['spans']).split())
                if not t or any(re.search(d, t, re.I) for d in drop): continue
                tot = sum(len(s['text'].strip()) for s in sp) or 1
                bold = sum(len(s['text'].strip()) for s in sp if s['flags'] & 16 or 'Bold' in s['font']) / tot
                rows.append({'t': t, 'b': bold})
    return rows


def pdf_numbered(rows, qre=r'^(\d{1,3})\s*[\.\)]\s*(.*)$', ore=r'^([a-eA-E])\s*[\.\)]\s*(.*)$', seq=False):
    """numbered questions with lettered options; wrapped lines are joined. Returns [{'n','q','o':[(text, bold)]}]
    seq=True: also accept the next number without a full stop ('42 Temperature'), even in the middle of a line"""
    out, cur, last = [], None, None
    if seq:   # split '98.6oF 42 Temperature ...' at the next question number
        rows2 = []
        for r in rows:
            rows2.append(r)
        rows = rows2
    pending = list(rows)
    while pending:
        r = pending.pop(0)
        t = r['t']
        if seq and cur is not None:
            nxt = cur['n'] + 1
            m = re.match(rf'^(.*?\S)\s+({nxt})\s*\.?\s+(\S.*)$', t)
            if m and not re.match(rf'^{nxt}\s*[\.\)]', t):
                pending.insert(0, {'t': f'{nxt}. {m.group(3)}', 'b': r['b']}); t = m.group(1); r = {'t': t, 'b': r['b']}
            m2 = re.match(rf'^({nxt})\s+(\S.*)$', t)
            if m2: t = f'{nxt}. {m2.group(2)}'
        mq = re.match(qre, t); mo = re.match(ore, t)
        if mq and (cur is None or not cur['o'] or len(cur['o']) >= 2 or int(mq.group(1)) == cur['n'] + 1):
            cur = {'n': int(mq.group(1)), 'q': mq.group(2), 'o': []}; out.append(cur); last = 'q'
        elif mo and cur is not None:
            cur['o'].append([mo.group(2), [r['b'], len(mo.group(2)) or 1]]); last = 'o'
        elif cur is not None:
            if last == 'o' and cur['o']: cur['o'][-1][0] += ' ' + t; cur['o'][-1][1].append(r['b']); cur['o'][-1][1].append(len(t))
            elif last == 'q': cur['q'] += ' ' + t
    for c in out:
        c['o'] = [(o.strip(), (sum(w[i] * w[i + 1] for i in range(0, len(w), 2)) / max(1, sum(w[i + 1] for i in range(0, len(w), 2))))) for o, w in c['o']]
    return out


def save(fid, items, name, bad=0):
    json.dump(items, open(os.path.join(OUT, f'cabin-{fid}.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    report[name] = {'questions': len(items), 'skipped': bad}


S = lambda f: os.path.join(SRC, f)

# ---- answer letter after the options
for fid, f, qnid in [('airlaw', 'AIR LAW AND PROCEDURES EXAMINATION.docx', '1'), ('b737exam', 'B737 AIRCRAFT TYPE EXAM.docx', '1'),
                     ('firstaid', 'FIRST AID AND AVIATION MEDICINE EXAM.docx', '1'), ('progress2', 'AIRCRAFT TYPE B737300 PROGRESS TEST II.docx', None),
                     ('dg', 'DANGEROUS GOODS EXAM.docx', None)]:
    items, bad = blocks_by_letter(docx_paras(S(f)), qnid); save(fid, items, f, bad)
items, bad = blocks_by_letter(txt_paras(S('SEP EXAM.txt'))); save('sep', items, 'SEP EXAM.doc', bad)

# ---- highlighted option
items, bad = blocks_by_highlight(docx_paras(S('MOCK AIR LAW - 34.docx')), '1'); save('mockairlaw34', items, 'MOCK AIR LAW - 34.docx', bad)

# ---- bold option (PDF)
rows = pdf_lines(S('CCTB 36 MOCK PAPER II.pdf'), drop=[r'^Page \d+ of \d+$'])
qs = pdf_numbered(rows); items, bad = [], 0
for c in qs:
    a = [i for i, (_, b) in enumerate(c['o']) if b > 0.6]
    if len(c['o']) >= 2 and len(a) >= 1: items.append({'q': c['q'], 'o': [o for o, _ in c['o']], 'a': a[:1] if len(a) > 1 else a})
    else: bad += 1
save('cctb36', items, 'CCTB 36 MOCK PAPER II.pdf', bad)


# ---- answer key at the back (Preparatory Guide): two sections, numbering restarts in each
PG = S('PREPARATORY GUIDE TO FLIGHT ATTENDANT QUESTIONS AND ANSWER BY PETER SUNDAY.pdf')
doc = pymupdf.open(PG)
def pg_rows(first, last):
    rows = []
    for pn in range(first - 1, last):
        for b in doc[pn].get_text('dict')['blocks']:
            for l in b.get('lines', []):
                t = ' '.join(''.join(s['text'] for s in l['spans']).split())
                if not t or re.match(r'^\d{1,3}$', t) or t.startswith('Content are not your expected'): continue
                if t in ('AIRCRAFT TYPE B737 CLASSIC (300/400/500)', 'AIR-LAW/GENERAL PAPER', 'ABOUT THE PAPER'): continue   # section headings
                rows.append({'t': t, 'b': 0})
    return rows
def pg_key(pages):
    key, last = {}, 0
    for pn in pages:
        for n, a in re.findall(r'\b(\d{1,3})\s*\.\s*([A-E])\b', doc[pn - 1].get_text()):
            n = int(n)
            if n in key and n == last: n = last + 1          # a number printed twice: it is the next one
            key[n] = 'ABCDE'.index(a); last = n
    return key
def pg_section(first, last, keypages, fid, name):
    qs = pdf_numbered(pg_rows(first, last), ore=r'^([A-E])\s*\.\s*(.*)$', seq=True); key = pg_key(keypages); items, bad, seen = [], 0, set()
    for c in qs:
        o = [x for x, _ in c['o'] if x]
        if c['n'] in seen or c['n'] not in key or len(o) < 2 or len(o) > 5 or key[c['n']] >= len(o): bad += 1; continue
        seen.add(c['n']); items.append({'q': c['q'].strip(), 'o': o, 'a': [key[c['n']]]})
    save(fid, items, name, bad)
    return qs, key
qs1, k1 = pg_section(3, 35, [61, 62], 'prep-type', 'Preparatory Guide: Aircraft Type B737')
qs2, k2 = pg_section(36, 60, [63, 64], 'prep-gen', 'Preparatory Guide: Air Law / General Paper')

# ---- NCAA QUESTIONS 2 (scanned, answers marked by hand): typed from the page images into ncaa2.json
nc = json.load(open(os.path.join(H, 'ncaa2.json'), encoding='utf-8'))
save('ncaa2', [x for x in nc if 'o' in x], 'NCAA QUESTIONS 2.pdf (scan)')

# ---- study cards: a question and its written answer
cards = []
def card(q, a, src):
    q, a = ' '.join(q.split()).strip(), ' '.join(a.split()).strip()
    if q and a: cards.append({'q': q, 'a': a, 'src': src})
cur, ans, last = None, None, None
for r in pdf_lines(S('CABIN CREW REVIEW QUESTIONS.pdf')):
    t = r['t']; mq = re.match(r'^(\d{1,3})\s*\.\s*(.+)$', t); ma = re.match(r'^Ans\s*[\.,:]\s*(.*)$', t, re.I)
    if ma and cur is not None: ans = ma.group(1); last = 'a'
    elif mq and (ans is not None or cur is None or last == 'a'):
        if cur is not None and ans is not None: card(cur, ans, 'Cabin Crew Review Questions')
        cur, ans, last = mq.group(2), None, 'q'
    elif cur is not None:
        if last == 'a': ans += ' ' + t
        else: cur += ' ' + t
if cur is not None and ans is not None: card(cur, ans, 'Cabin Crew Review Questions')
n_review = len(cards)
q = None
for x in docx_paras(S('Revision Questions B737 345 - 10_08_2021.docx')):
    m = re.match(r'^Ans\s*[:\.]\s*(.*)$', x['t'], re.I)
    if m and q: card(q, m.group(1), 'Revision Questions B737'); q = None
    elif not m: q = x['t'] if q is None or q.endswith('?') is False and False else x['t']
n_rev = len(cards) - n_review
for x in nc:
    if 'card' in x: card(x['q'], x['card'], 'NCAA Questions 2')
json.dump(cards, open(os.path.join(OUT, 'cabin-cards.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
report['study cards'] = {'Cabin Crew Review Questions': n_review, 'Revision Questions B737': n_rev, 'NCAA Questions 2': len(cards) - n_review - n_rev}

json.dump(report, open(os.path.join(H, 'report.json'), 'w', encoding='utf-8'), indent=1)
for k, v in report.items(): print(f'{v["questions"]:4} questions  {v["skipped"]:3} skipped   {k}' if 'questions' in v else f'study cards: {v}')
