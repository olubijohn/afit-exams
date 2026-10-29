"""Minimal Word 97-2003 (.doc) reader: text plus per-character formatting (bold, colour, highlight, underline).
Usage: python readdoc.py in.doc out.json  ->  [{"t": paragraph text, "runs": [[text, bold, color, highlight, underline], ...]}]"""
import olefile, struct, sys, json

ole = olefile.OleFileIO(sys.argv[1])
wd = ole.openstream('WordDocument').read()
flags = struct.unpack_from('<H', wd, 0x0A)[0]
tbl = ole.openstream('1Table' if flags & 0x0200 else '0Table').read()

# FIB: FibRgFcLcb97 starts after csw/fibRgW/cslw/fibRgLw
csw = struct.unpack_from('<H', wd, 32)[0]
p = 34 + csw * 2
cslw = struct.unpack_from('<H', wd, p)[0]
p += 2 + cslw * 4 + 2           # skip rgLw and cbRgFcLcb
fclcb = lambda i: struct.unpack_from('<II', wd, p + i * 8)
fcBteChpx, lcbBteChpx = fclcb(12)
fcClx, lcbClx = fclcb(33)

# piece table
clx = tbl[fcClx:fcClx + lcbClx]
i = 0
while clx[i] == 1:
    i += 3 + struct.unpack_from('<H', clx, i + 1)[0]
assert clx[i] == 2
lcb = struct.unpack_from('<I', clx, i + 1)[0]
pcd = clx[i + 5:i + 5 + lcb]
n = (lcb - 4) // 12
cps = struct.unpack_from('<%dI' % (n + 1), pcd, 0)
pieces = []
for k in range(n):
    fc = struct.unpack_from('<I', pcd, (n + 1) * 4 + k * 8 + 2)[0]
    comp = bool(fc & 0x40000000)
    fc &= 0x3FFFFFFF
    if comp: fc //= 2
    pieces.append((cps[k], cps[k + 1], fc, comp))

# character formatting runs: list of (fcStart, fcEnd, props)
def chpx_props(grpprl):
    pr = {'b': False, 'c': None, 'h': 0, 'u': 0}
    j = 0
    while j + 2 <= len(grpprl):
        sprm = struct.unpack_from('<H', grpprl, j)[0]; j += 2
        spra = sprm >> 13
        size = {0: 1, 1: 1, 2: 2, 3: 4, 4: 2, 5: 2, 7: 3}.get(spra)
        if spra == 6: size = grpprl[j] + 1
        if size is None or j + size > len(grpprl): break
        op = grpprl[j:j + size]
        if sprm == 0x0835: pr['b'] = op[0] in (1, 0x81)
        elif sprm == 0x2A42: pr['c'] = 'ico%d' % op[0]
        elif sprm == 0x6870: pr['c'] = '#%02x%02x%02x' % (op[0], op[1], op[2]) if op[3] == 0 else pr['c']
        elif sprm == 0x2A0C: pr['h'] = op[0]
        elif sprm == 0x2A3E: pr['u'] = op[0]
        j += size
    return pr

runs = []
nb = (lcbBteChpx - 4) // 8
plc = tbl[fcBteChpx:fcBteChpx + lcbBteChpx]
for k in range(nb):
    pn = struct.unpack_from('<I', plc, (nb + 1) * 4 + k * 4)[0] & 0x3FFFFF
    page = wd[pn * 512:(pn + 1) * 512]
    crun = page[511]
    rgfc = struct.unpack_from('<%dI' % (crun + 1), page, 0)
    for r in range(crun):
        off = page[(crun + 1) * 4 + r] * 2
        pr = chpx_props(page[off + 1:off + 1 + page[off]]) if off else chpx_props(b'')
        runs.append((rgfc[r], rgfc[r + 1], pr))
runs.sort()
import bisect
starts = [r[0] for r in runs]
def props_at(fc):
    k = bisect.bisect_right(starts, fc) - 1
    if k >= 0 and runs[k][0] <= fc < runs[k][1]: return runs[k][2]
    return {'b': False, 'c': None, 'h': 0, 'u': 0}

chars = []   # (char, props)
for cp0, cp1, fc, comp in pieces:
    for cp in range(cp0, cp1):
        if comp:
            b = fc + (cp - cp0); ch = bytes([wd[b]]).decode('cp1252', 'replace')
        else:
            b = fc + (cp - cp0) * 2; ch = wd[b:b + 2].decode('utf-16le', 'replace')
        chars.append((ch, props_at(b)))

paras, cur = [], []
def flush():
    t = ''.join(c for c, _ in cur).strip()
    if t:
        rs = []
        for c, pr in cur:
            key = (pr['b'], pr['c'], pr['h'], pr['u'])
            if rs and tuple(rs[-1][1:]) == key: rs[-1][0] += c
            else: rs.append([c, *key])
        paras.append({'t': t, 'runs': rs})
    cur.clear()
for ch, pr in chars:
    if ch in '\r\x07\x0c': flush()
    elif ch == '\x0b': cur.append(('\n', pr))
    elif ch in '\x01\x08\x13\x14\x15': continue
    else: cur.append((ch, pr))
flush()
json.dump(paras, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False)
print(len(paras), 'paragraphs')
