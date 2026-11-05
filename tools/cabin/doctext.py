"""Plain text of an old Word .doc (Word 97-2003) without Word: reads the piece table from the file.
Text only (no colours or bold). Paragraphs end in \\r, table cells in \\x07.
  python -I doctext.py file.doc"""
import struct, sys, olefile


def doc_text(path):
    ole = olefile.OleFileIO(path)
    wd = ole.openstream('WordDocument').read()
    flags = struct.unpack_from('<H', wd, 0x000A)[0]
    table = ole.openstream('1Table' if flags & 0x0200 else '0Table').read()
    fc_clx, lcb_clx = struct.unpack_from('<II', wd, 0x01A2)
    clx = table[fc_clx:fc_clx + lcb_clx]
    i = 0
    while clx[i] == 0x01:                      # Prc entries (formatting), skipped
        i += 3 + struct.unpack_from('<H', clx, i + 1)[0]
    assert clx[i] == 0x02, 'no piece table'
    lcb = struct.unpack_from('<I', clx, i + 1)[0]
    plc = clx[i + 5:i + 5 + lcb]
    n = (lcb - 4) // 12
    cps = struct.unpack_from(f'<{n + 1}I', plc, 0)
    out = []
    for k in range(n):
        pcd = plc[4 * (n + 1) + 8 * k: 4 * (n + 1) + 8 * k + 8]
        fc = struct.unpack_from('<I', pcd, 2)[0]
        length = cps[k + 1] - cps[k]
        if fc & 0x40000000:                    # 8-bit text
            start = (fc & ~0x40000000) // 2
            out.append(wd[start:start + length].decode('cp1252', 'replace'))
        else:                                  # UTF-16
            out.append(wd[fc:fc + 2 * length].decode('utf-16-le', 'replace'))
    text = ''.join(out)
    # drop field codes: \x13 code \x14 result \x15 -> result
    res, depth, skip = [], 0, []
    for ch in text:
        if ch == '\x13': skip.append(True); continue
        if ch == '\x14' and skip: skip[-1] = False; continue
        if ch == '\x15' and skip: skip.pop(); continue
        if skip and skip[-1]: continue
        res.append(ch)
    return ''.join(res)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print(doc_text(sys.argv[1]).replace('\r', '\n').replace('\x07', ' | '))
