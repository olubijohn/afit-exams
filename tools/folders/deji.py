"""General to use (Deji).docx -> paragraph dump (text + run colour) without topic headings, then questions via docq.parse.
Answers are the red option. Usage: python -I deji.py <docx> <tools/folders dir>"""
import docx, sys, json, os, re
sys.stdout.reconfigure(encoding='utf-8')
d = docx.Document(sys.argv[1]); T = sys.argv[2]
sys.path.insert(0, T); from docq import parse
P = [{'t': 'title', 'runs': []}]
heads = []
for p in d.paragraphs:
    t = p.text.strip()
    if not t: continue
    runs = [[r.text, bool(r.bold), ('#' + str(r.font.color.rgb).lower()) if r.font.color is not None and r.font.color.type is not None and r.font.color.rgb is not None else ''] for r in p.runs]
    bu = all((r.bold and r.underline) for r in p.runs if r.text.strip())
    if bu and len(t) < 60: heads.append(t); continue          # topic heading (kept as one folder, not split)
    # "a.  only No. 1 is true" style option labels
    P.append({'t': re.sub(r'^[a-dA-D][\.\)]\s+', '', t), 'runs': runs})
json.dump(P, open(os.path.join(T, 'in', 'deji_paras.json'), 'w', encoding='utf-8'), ensure_ascii=False)
B = json.load(open(os.path.join(T, 'in', 'base.json'), encoding='utf-8'))
known = [q for q in B['questions']] + json.load(open(os.path.join(T, 'in', 'gp.json'), encoding='utf-8'))
o, bad = parse(os.path.join(T, 'in', 'deji_paras.json'), known)
print('headings skipped:', heads)
print(len(o), 'questions', len(bad), 'skipped', {n: sum(len(x['o']) == n for x in o) for n in (2, 3, 4)})
for b in bad: print('  SKIP', b[0], '|', b[1][:90])
json.dump(o, open(os.path.join(T, 'in', 'deji.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
