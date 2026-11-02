"""2023 GENERALS.docx -> in/g23.json (one folder under General, in the file's own order).
The file's picture is damaged (python-docx refuses it), so the text is read straight from word/document.xml.
The answer is the option in red/green, or (in a few blocks typed in blue) the option in bold.
Options typed on one line ("A. 3/32 inch   B. 1/16 inch   C. 3/8 inch") are split; the red one is the answer.
Then questions are read strictly (walk.py): a question line, then its options, one of them marked. Usage: python -I g23.py <docx> <tools/folders dir>"""
import zipfile, sys, json, os, re
from lxml import etree
sys.stdout.reconfigure(encoding='utf-8')
T = sys.argv[2]; sys.path.insert(0, T); from walk import walk
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
MARK = ('ff0000', 'c00000', 'ee0000', '00b050', '008000')
x = etree.fromstring(zipfile.ZipFile(sys.argv[1]).read('word/document.xml'))
# "15." / "44.The" / "." (number lost) / "A." / "b)" / "a." labels; not "1.98ºC" and not "A.D.F."
LABEL = r'^\s*(?:\d+\s*[.)](?=\s|$|[A-Za-z])|\.(?=\s)|[A-Da-d]\s*[.)](?![A-Z]\.))?\s*'
P = [{'t': 'title', 'runs': []}]
def add(t, ans):
    t = re.sub(r'\s+', ' ', re.sub(LABEL, '', t, count=1)).strip()
    if t: P.append({'t': t, 'runs': [[t, False, '#ff0000' if ans else '']]})
skipped, notes = [], {}
for p in x.iter(W + 'p'):
    runs = []
    for r in p.iter(W + 'r'):
        t = ''.join(n.text or '' for n in r.iter(W + 't'))
        if not t: continue
        c = r.find(f'{W}rPr/{W}color'); b = r.find(f'{W}rPr/{W}b')
        bold = b is not None and b.get(W + 'val') not in ('0', 'false')
        runs.append((t, (c.get(W + 'val') or '').lower() in MARK if c is not None else False, bold))
    t = ''.join(r[0] for r in runs)
    if not re.search(r'[A-Za-z0-9]', t): continue          # a stray quote mark on its own line
    if re.match(r'^\s*Ans\s*[;:]', t, re.I): skipped.append(('answer written, no options', t)); P.pop(); continue   # a question with a written answer only
    marked = [i for i, r in enumerate(runs) if r[1] and r[0].strip()]
    ans = bool(marked) or all(r[2] for r in runs if r[0].strip())
    # options on one line: A. ... B. ... C. ...
    if re.match(r'^\s*A\s*\.', t) and re.search(r'\sB\s*\.\s*\S', t) and re.search(r'\sC\s*\.\s*\S', t):
        cuts = [m.start() for m in re.finditer(r'(?:^|\s)[A-D]\s*\.(?=\s*\S)', t)]
        pos, red = 0, set()
        for tt, mk, _ in runs:
            if mk and tt.strip(): red.update(range(pos, pos + len(tt)))
            pos += len(tt)
        for n, s in enumerate(cuts):
            e = cuts[n + 1] if n + 1 < len(cuts) else len(t)
            add(t[s:e], any(i in red for i in range(s, e) if not t[i].isspace()))
        continue
    if t.rstrip().endswith('#'): t, ans = t.rstrip()[:-1], True        # "Complementary #": the file marks this answer with #
    # a bold note typed after the three options (two questions): it explains the answer, it is not a fourth option
    if ans and len(P) >= 4 and sum(q['runs'][0][2] == '#ff0000' for q in P[-3:]) == 1 and not any(q['runs'][0][2] for q in P[-4:-3]) \
            and re.match(r'^(density varies inversely|Effectiveness of any control in the slipstream)', t.strip()):
        notes[len(P)] = re.sub(r'\s+', ' ', t).strip(); continue
    add(t, ans)
json.dump(P, open(os.path.join(T, 'in', 'g23_paras.json'), 'w', encoding='utf-8'), ensure_ascii=False)
# numbered statements "(i) ... (viii)" belong to the question above them
Q = []
for p in P[1:]:
    if re.match(r'^\(?[ivx]{1,4}\)\s', p['t']) and Q: Q[-1] = dict(Q[-1], t=Q[-1]['t'] + '\n' + p['t'])
    else: Q.append(p)
o, bad = walk(Q, lambda p: p['runs'][0][2] == '#ff0000')
bad = [b for b in bad if not re.match(r'(?i)ans\b', b[1])]
for at, note in notes.items():          # the note belongs to the question whose options end just before it
    q = next(q for q in o if q['o'][-1] == P[at - 1]['t']); q['x'] = note
print(len(o), 'questions', len(bad), 'skipped', {n: sum(len(q['o']) == n for q in o) for n in (2, 3, 4)})
for b in skipped + bad: print('  SKIP', b[0], '|', b[1][:100])
json.dump(o, open(os.path.join(T, 'in', 'g23.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
