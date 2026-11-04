"""GTE General NCAA 1.pdf -> in/gte_ncaa.json (one folder under Gas Turbine Engine; the file has no topics of its own).
A slide deck: page 1 is the title ("365 QUESTIONS BANK FOR LICENCES BY SOLO-P"), then one question per page.
Each paragraph starts with a Wingdings bullet: the first is the question, the rest are the options.
The answer is the option typed in bold green (00B050) with a blue highlight box behind it.
Usage: python -I gte_ncaa.py <pdf> <tools/folders dir>"""
import sys, os, re, json
import pymupdf
sys.stdout.reconfigure(encoding='utf-8')
PDF, T = sys.argv[1:3]
GREEN = 0x00B050
out, bad = [], []
for pn, pg in enumerate(pymupdf.open(PDF)):
    bullets, lines = [], []
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                t = s['text'].replace('\xa0', ' ')
                if not t.strip(): continue
                y = (s['bbox'][1] + s['bbox'][3]) / 2
                if 'Wingdings' in s['font']: bullets.append(y); continue
                lines.append((y, s['bbox'][0], t, s['color'] == GREEN, bool(s['flags'] & 16)))
    if not bullets: continue                                  # title page
    bullets.sort(); lines.sort()
    hl = [d['rect'] for d in pg.get_drawings() if d.get('fill') and d['fill'][2] > .8 and d['fill'][0] < .3 and d['rect'].width > 40]
    groups = [[] for _ in bullets]
    for y, x, t, g, bo in lines:
        k = max([i for i, by in enumerate(bullets) if by <= y + 14] or [0])   # the bullet this line belongs to
        groups[k].append((t, g, bo, y))
    groups = [g for g in groups if g]
    if len(groups) < 3: bad.append((pn + 1, 'not a question page', ' '.join(t for g in groups for t, *_ in g)[:120])); continue
    txt = lambda g: re.sub(r'\s+', ' ', ' '.join(t for t, *_ in g)).strip()
    stem, opts = txt(groups[0]), [txt(g) for g in groups[1:]]
    a = [i for i, g in enumerate(groups[1:]) if any(gr for _, gr, _, _ in g)]
    if len(a) != 1: a = [i for i, g in enumerate(groups[1:]) if all(bo for _, _, bo, _ in g)]
    if len(a) != 1 and hl:                                    # fall back to the blue highlight box
        a = [i for i, g in enumerate(groups[1:]) if any(r.y0 - 4 <= y <= r.y1 + 4 for r in hl for *_, y in g)]
    if len(a) != 1: bad.append((pn + 1, f'{len(a)} marked', stem, opts)); continue
    # "which of these" questions: the numbered statements come first, the last three lines are the real choices
    if len(opts) > 4 or (len(opts) == 5) or (len(opts) > 3 and re.match(r'^\(\d\)', stem)):
        extra, real = opts[:-3], opts[-3:]
        if a[0] < len(extra): bad.append((pn + 1, 'answer is a statement, not a choice', stem, opts)); continue
        if not re.match(r'^\(\d\)', stem): extra = [f'({i}) {x}' for i, x in enumerate(extra, 1)]
        stem, opts, a = stem + ' ' + ' '.join(extra), real, [a[0] - len(extra)]
    # a fourth line that is the author's own note, not an option (e.g. "Torque=force x radius", "sif")
    elif len(opts) == 4 and a[0] != 3 and ('=' in opts[3] or opts[3].lower() in ('sif', 'high marry high')):
        opts = opts[:3]
    out.append({'q': stem, 'o': opts, 'a': a, 'page': pn + 1})
print('pages', pn + 1, '| questions', len(out), '| left out', len(bad))
for b in bad: print('  SKIP page', b[0], '|', b[1], '|', b[2][:100], '|', b[3] if len(b) > 3 else '')
json.dump(out, open(os.path.join(T, 'in', 'gte_ncaa.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
json.dump(bad, open(os.path.join(T, 'in', 'gte_ncaa_unresolved.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
