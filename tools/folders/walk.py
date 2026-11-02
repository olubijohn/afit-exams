"""Strict reader for files laid out as: question line, then its options, the right option marked (red/bold).
Used for 2023 GENERALS: steps a question at a time and only accepts a block when the next question lines up after it."""
import re
stemish = lambda t: bool(re.search(r'[?:]\s*$', t))
def walk(P, mark):
    m = lambda j: j < len(P) and mark(P[j])
    out, bad = [], []
    def marked_q(j):            # j starts a question with exactly one marked option: return its option count
        if j >= len(P) or m(j): return None
        ok = []
        for n in (3, 2, 4):
            if j + n >= len(P) + 1: continue
            if sum(m(x) for x in range(j + 1, j + n + 1)) != 1: continue
            if any(stemish(P[x]['t']) for x in range(j + 1, j + n + 1)): continue     # "...:" / "...?" is a question, not an option
            if j + n + 1 < len(P) and m(j + n + 1): continue
            if n != 3 and not starts(j + n + 1, 1): continue
            ok.append(n)
        # prefer the count after which a line that reads like a question follows
        return next((n for n in ok if j + n + 1 >= len(P) or stemish(P[j + n + 1]['t'])), ok[0] if ok else None)
    def starts(j, depth):       # a question (marked, or an unmarked block that is followed by one) starts at j
        if j >= len(P): return True
        if marked_q(j): return True
        return depth > 0 and any(not any(m(x) for x in range(j, j + k)) and starts(j + k, depth - 1) for k in (4, 3, 5, 2))
    i = 0
    while i < len(P):
        n = marked_q(i)
        if n and starts(i + n + 1, 2):
            out.append({'q': P[i]['t'], 'o': [P[x]['t'] for x in range(i + 1, i + n + 1)], 'a': [[m(x) for x in range(i + 1, i + n + 1)].index(True)]})
            i += n + 1; continue
        # a question with no marked answer (stem + its options): step over it when the next question lines up after it
        k = next((k for k in (4, 3, 5, 2) if i + k <= len(P) and not any(m(x) for x in range(i, i + k)) and starts(i + k, 1)), None)
        if k:
            bad.append(('no answer marked', P[i]['t'])); i += k; continue
        bad.append(('not read', P[i]['t'])); i += 1
    return out, bad
