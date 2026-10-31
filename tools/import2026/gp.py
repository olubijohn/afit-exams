import sys, re, json
sys.stdout.reconfigure(encoding='utf-8')
L = [l.strip() for l in open(sys.argv[1], encoding='utf-8').read().split('\n') if l.strip()]
out, bad, cur = [], [], None
def flush():
    if cur:
        o = [re.sub(r'\s+', ' ', x).strip() for x in cur['o']]
        if cur['a'] is not None and 0 <= cur['a'] < len(o) and len(o) >= 2: out.append({'n': cur['n'], 'q': re.sub(r'\s+', ' ', cur['q']).strip(), 'o': o, 'a': [cur['a']]})
        else: bad.append(cur)
for s in L:
    m = re.match(r'^(\d+)\s*[\.\)]\s*(.*)$', s)
    # next question: after an answer, or (when a question has no answer line) the next number with options already read
    if m and (cur is None or cur['a'] is not None or (len(cur['o']) >= 2 and 0 < int(m.group(1)) - cur['n'] <= 3)):
        flush(); cur = {'n': int(m.group(1)), 'q': m.group(2), 'o': [], 'a': None}; continue
    if cur is None: continue
    m = re.search(r'ANSWER\s*[:\.]?\s*\(?([A-Da-d])\b', s)   # also "D. ANSWER: B"
    if m: cur['a'] = 'ABCD'.index(m.group(1).upper()); continue
    if re.match(r'^ANSWER\s*[:\.]?\s*$', s): cur['a'] = -1; continue
    m = re.match(r'^([A-D])\s*[\.\)]\s*(.*)$', s)
    if m and 'ABCD'.index(m.group(1)) == len(cur['o']): cur['o'].append(m.group(2)); continue
    if cur['o']: cur['o'][-1] += ' ' + s
    else: cur['q'] += ' ' + s
flush()
print(len(out), 'ok', len(bad), 'bad'); [print(' BAD', json.dumps(b, ensure_ascii=False)[:250]) for b in bad[:10]]
print('figure refs:', [x['n'] for x in out if re.search(r'figure|diagram|shown', x['q'], re.I)])
json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
