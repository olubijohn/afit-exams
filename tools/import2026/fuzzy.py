import json, re, sys, difflib
sys.stdout.reconfigure(encoding='utf-8')
k = lambda t: re.sub(r'[^a-z0-9]', '', t.lower())
def sim(a, b): return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
def osig(q): return ' '.join(sorted(k(o)[:30] for o in q['o']))
def match(new, old, thr=0.88):
    """returns list of (newq, best old q or None, ratio)"""
    idx = [(k(o['q']), osig(o), o) for o in old]
    res = []
    for q in new:
        kq, so = k(q['q']), osig(q); best, br = None, 0
        for ko, oo, o in idx:
            if abs(len(ko) - len(kq)) > 0.3 * max(len(kq), 1) + 5: continue
            if difflib.SequenceMatcher(None, kq, ko, autojunk=False).quick_ratio() < thr: continue
            r = sim(kq, ko)
            if r >= thr:
                r2 = sim(so, oo)
                if r * 0.6 + r2 * 0.4 > br: best, br = o, r * 0.6 + r2 * 0.4
        res.append((q, best, br))
    return res
