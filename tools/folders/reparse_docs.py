"""Re-read the two Word .doc files (paragraph dumps) into in/*.q.json. Usage: python -I reparse_docs.py <dir with the .json dumps>"""
import json, sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.stdout.reconfigure(encoding='utf-8')
from docq import parse
H = os.path.dirname(os.path.abspath(__file__)); SRC = sys.argv[1]
L = lambda f: json.load(open(os.path.join(H, 'in', f), encoding='utf-8'))
known = L('ncaa.json') + L('p200.json') + L('ame.json') + L('m11ch.json')
for f in ['PMA 2019 STUDIES-1', 'PRESSURISED METAL AIRFRAME2018']:
    o, b = parse(os.path.join(SRC, f + '.json'), known); print(f, len(o), 'questions')
    for x in b:
        if x[1]: print('  not used:', x[0], '|', x[1][:80])
    for x in o:
        if '\n' in x['q']: print('  MULTI-LINE:', x['q'].replace('\n', ' / ')[:110], '|', x['o'], x['a'])
    json.dump(o, open(os.path.join(H, 'in', f + '.q.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
