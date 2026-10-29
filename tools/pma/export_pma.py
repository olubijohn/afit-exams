"""Add the merged pressurised metal airframe questions to NCAT's data/questions.json as subject 'pma'.
Usage: python export_pma.py merged.json data/questions.json"""
import json, sys, re
sys.stdout.reconfigure(encoding='utf-8')
items = json.load(open(sys.argv[1], encoding='utf-8'))
k = lambda t: re.sub(r'[^a-z0-9]', '', t.lower())

# copies of the same question disagree and the right answer can't be confirmed: leave them out
DROP = ['positive pressure signals from', 'mixing chamber ha', 'identification of the horn for the landing gear', 'over pressure is usually caused by']
# copies disagree; this is the standard answer
FIX = {'generally the first step in removing an accumulator from a hydraulic': 'relie'}
out, dropped = [], []
for it in items:
    ql = it['q'].lower()
    if any(x in ql for x in DROP) or 'Option A.' in it['q']: dropped.append(it['q']); continue
    # the source prints the same option twice: keep one, and keep the answer pointing at it
    seen_o, opts, remap = {}, [], {}
    for i, o in enumerate(it['o']):
        if k(o) in seen_o: remap[i] = seen_o[k(o)]; continue
        seen_o[k(o)] = remap[i] = len(opts); opts.append(o)
    it['o'], it['a'] = opts, [remap[it['a'][0]]]
    for key, ans in FIX.items():
        if key in ql:
            it['a'] = [next(i for i, o in enumerate(it['o']) if o.lower().startswith(ans))]
    out.append(it)

bank = json.load(open(sys.argv[2], encoding='utf-8'))
bank['questions'] = [q for q in bank['questions'] if q['s'] != 'pma']
bank['subjects'] = [s for s in bank['subjects'] if s['id'] != 'pma']
for n, it in enumerate(out, 1):
    bank['questions'].append({'id': f'pma-{n}', 's': 'pma', 'n': n, 'q': it['q'], 'o': it['o'], 'a': it['a']})
bank['subjects'].append({'id': 'pma', 'name': 'Pressurised Metal Airframe', 'count': len(out)})
bank['source'] = 'GENERAL PAPER (NCAT); SLIDE ON PISTON AND SYSTEMS; PRESSURISED METAL AIRFRAME (NCAA papers, 200+ licence exam, PMA 2019 studies, 2018 exams)'
json.dump(bank, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('pma questions:', len(out), '| dropped:', len(dropped), '| total bank:', len(bank['questions']))
for x in dropped: print('  dropped:', x[:90])
