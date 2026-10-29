"""Pressurised airframe exam PDFs: numbered questions, lettered options, answer shown in red text or a highlight.
Usage: python parse_pma_pdf.py in.pdf out.json"""
import pymupdf, re, sys, json, unicodedata
sys.stdout.reconfigure(encoding='utf-8')
d = pymupdf.open(sys.argv[1])
Q_RE = re.compile(r'^(\d{1,3})\s*[.)]\s*(.*)$')
O_RE = re.compile(r'^(?:Option\s+)?\(?([a-iA-I])\s*[.)]\s+(.*)$')
ANS_RE = re.compile(r'^Correct Answer is\.?\s*(.*)$', re.I)
ROMAN_RE = re.compile(r'^(i{1,3}|iv|v)\.\s')
SKIP_RE = re.compile(r'^(Page \d+ of \d+|NCAA/AMEL.*|AIRCRAFT MAINTENANCE ENGINEERS LICENCE.*|PRESSURI[SZ]ED METAL AIRFRAME\s*)$', re.I)

def clean(t):
    t = unicodedata.normalize('NFC', t.replace(' ', ' ').replace('ǀ', '|'))
    return re.sub(r'\s+', ' ', t).strip()

lines = []
for pn, p in enumerate(d):
    if pn == 0: continue                      # cover page with instructions
    hl = [pymupdf.Rect(a.rect) for a in p.annots() if a.type[1] in ('Highlight', 'Underline', 'Squiggly', 'StrikeOut')]
    for b in p.get_text('dict', sort=True)['blocks']:
        for l in b.get('lines', []):
            t = clean(''.join(s['text'] for s in l['spans']))
            if not t or SKIP_RE.match(t): continue
            r = pymupdf.Rect(l['bbox'])
            red = any(s['color'] == 0xff0000 and s['text'].strip() for s in l['spans'])
            h = any((r & x).get_area() > 0.3 * r.get_area() for x in hl)
            lines.append({'t': t, 'm': red or h, 'p': pn + 1})

qs, cur, sect = [], None, 1
for l in lines:
    mq, mo, ma = Q_RE.match(l['t']), O_RE.match(l['t']), ANS_RE.match(l['t'])
    if ma and cur is not None:
        cur['ans_text'] = ma.group(1); cur['in_ans'] = True; continue
    if cur is not None and cur.get('in_ans') and not mq:
        cur['ans_text'] += ' ' + l['t']; continue
    if cur is not None and not cur['o'] and (ROMAN_RE.match(l['t'])):
        cur['q'] = (cur['q'] + '\n' + l['t']).strip(); continue
    if cur is not None and len(cur['o']) >= 3 and not mo and not mq and re.search(r'[?:;]$', l['t']) and l['t'][:1].isupper():
        cur = {'n': cur['n'], 'sect': sect, 'q': l['t'], 'o': [], 'p': l['p'], 'qm': l['m'], 'extra': True}
        qs.append(cur); continue
    if mq:
        n = int(mq.group(1))
        if cur and n < cur['n'] - 5: sect += 1      # numbering restarts in a new paper
        cur = {'n': n, 'sect': sect, 'q': mq.group(2), 'o': [], 'p': l['p'], 'qm': l['m']}
        qs.append(cur)
    elif mo and cur is not None:
        cur['o'].append({'t': mo.group(2), 'm': l['m']})
    elif cur is not None:
        if cur['o']: cur['o'][-1]['t'] += ' ' + l['t']
        elif '\n' in cur['q'] and not ROMAN_RE.match(l['t']) and cur['q'].split('\n')[-1][:1] in 'iv': cur['q'] += ' ' + l['t']
        else: cur['q'] = (cur['q'] + ' ' + l['t']).strip()
out = []
for q in qs:
    ans = [i for i, o in enumerate(q['o']) if o['m']]
    if not ans and q.get('ans_text'):
        k = lambda t: re.sub(r'[^a-z0-9]', '', t.lower())
        ans = [i for i, o in enumerate(q['o']) if k(o['t']) == k(q['ans_text']) or (len(k(q['ans_text'])) > 3 and k(o['t']).startswith(k(q['ans_text'])))]
    out.append({'src_n': q['n'], 'sect': q['sect'], 'page': q['p'], 'q': '\n'.join(clean(x) for x in q['q'].split('\n')), 'o': [clean(o['t']) for o in q['o']], 'a': ans})
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
bad = [x for x in out if len(x['a']) != 1 or len(x['o']) not in (3, 4) or not x['q']]
print(len(out), 'questions;', 'sections', max(x['sect'] for x in out), '; odd', len(bad))
for x in bad[:40]: print('  p%d s%d #%d a=%s |%s| %s' % (x['page'], x['sect'], x['src_n'], x['a'], x['q'][:60], [o[:25] for o in x['o']]))
