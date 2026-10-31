"""AIRFRAME QUESTION - JULY 2019.docx -> in/july.json
Every question in this file has exactly three options, in one of three layouts:
  question / Option A. / Option B. / Option C. / Correct Answer is. ... (/ Explanation.)
  question / three plain lines, the right one in red
  question / a) b) c), the right one in red
So it is read strictly: a question line, then exactly three options. A question whose answer isn't marked is still
stepped over as a block of four, so the next question stays aligned.
Not questions: red one-line notes ("... – answer") and the three options after line 266, whose question text is lost.
Usage: python -I july2.py <docx>"""
import docx, sys, os, re, json
sys.stdout.reconfigure(encoding='utf-8')
H = os.path.dirname(os.path.abspath(__file__))
k = lambda t: re.sub(r'[^a-z0-9]', '', t.lower())
clean = lambda t: re.sub(r'\s+', ' ', t.replace('\xa0', ' ')).strip()
RED = ('ff0000', 'c00000', 'ee0000', '00b050')
d = docx.Document(sys.argv[1])
def is_red(p): return any(r.text.strip() and r.font.color is not None and r.font.color.type is not None and str(r.font.color.rgb).lower() in RED for r in p.runs)
raw = []
for p in d.paragraphs:
    t = clean(p.text)
    if not t: continue
    if raw and p.text[:1] == '\t' and len(t) < 25 and not raw[-1][0].startswith(('Option', 'Correct')): raw[-1] = (raw[-1][0] + ' ' + t, raw[-1][1]); continue   # "\tDrop?"
    raw.append((t, is_red(p)))

def tidy(t):
    t = re.sub(r'^\d+\.\s*', '', t); t = re.sub(r'\?\.$', '?', t)
    return t[:-1] if t.endswith('.') and not re.search(r'(\d|etc|[A-Z])\.$', t) else t
out, skipped, i = [], [], 0
while i < len(raw):
    t, r = raw[i]
    if t.startswith(('Correct Answer', 'Explanation')):
        if re.search(r'\S\s{2,}\S.*\?$', raw[i][0]) or raw[i][0].endswith('markings?'):   # a question glued onto the answer line: its text is lost
            skipped.append(('question text lost', raw[i + 1][0] if i + 1 < len(raw) else '')); i += 4; continue
        i += 1; continue
    if r and ' – ' in t: skipped.append(('note, not a question', t)); i += 1; continue
    if re.match(r'^[.…\s]+$', t): skipped.append(('question text missing in file', t)); i += 4; continue
    if i + 1 < len(raw) and raw[i + 1][0].startswith('Option A'):
        opts, ans, j = [], None, i + 1
        while j < len(raw) and re.match(r'^Option [A-D]\.', raw[j][0]):
            opts.append(re.sub(r'^Option [A-D]\.\s*', '', raw[j][0])); ans = len(opts) - 1 if raw[j][1] else ans; j += 1
            while j < len(raw) and not re.match(r'^(Option [A-D]\.|Correct Answer)', raw[j][0]) and len(opts) < 3 and not re.search(r'[?:]$', raw[j][0]):
                opts[-1] += ' ' + raw[j][0]; j += 1        # option that wraps onto the next line
        if j < len(raw) and raw[j][0].startswith('Correct Answer'):
            at = re.sub(r'^Correct Answer is\s*[A-D]?\.?\s*', '', raw[j][0]); m = re.match(r'^Correct Answer is\s*([A-D])\b', raw[j][0])
            hits = [n for n, o in enumerate(opts) if k(o) == k(at)] or [n for n, o in enumerate(opts) if k(at) and (k(o).startswith(k(at)) or k(at).startswith(k(o)))]
            ans = hits[0] if len(hits) == 1 else ('ABCD'.index(m.group(1)) if m else ans)
            if not re.search(r'\S\s{2,}\S.*\?$', raw[j][0]) and not raw[j][0].endswith('markings?'): j += 1
        if j < len(raw) and raw[j][0].startswith('Explanation'): j += 1
    else:
        block = raw[i + 1:i + 4]; j = i + 4
        opts = [re.sub(r'^[a-d]\)\s*', '', b[0]) for b in block]; reds = [n for n, b in enumerate(block) if b[1]]
        ans = reds[0] if len(reds) == 1 else None
        if len(block) < 3 or any(b[0].startswith('Option') for b in block): skipped.append(('not a full question', t)); i += 1; continue
    if ans is None: skipped.append(('no answer marked', t))
    else: out.append({'q': tidy(t), 'o': [tidy(o) for o in opts], 'a': [ans]})
    i = j
print(len(out), 'questions')
for s in skipped: print('  not used:', s[0], '|', s[1][:90])
json.dump(out, open(os.path.join(H, 'in', 'july.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
