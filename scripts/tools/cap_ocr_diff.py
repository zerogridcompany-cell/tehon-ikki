# 手本の文字読み取り（txt/ocr_raw.tsv）とうちの字幕（caps.json）を、字幕に出てくる語だけでコマごとに突き合わせる
import json, re, collections
C = json.load(open('proj/src/caps.json'))
norm = lambda s: re.sub(r"[^a-z0-9']", "", s.lower().replace('’', "'"))
vocab = {norm(c['w']) for c in C}
T = {}
for l in open('txt/ocr_raw.tsv'):
    p = l.rstrip('\n').split('\t'); f = int(p[0].split('.')[0]) - 1
    T[f] = [norm(w) for w in (p[1].split() if len(p) > 1 else []) if norm(w) in vocab]
N = max(T) + 1; bad = collections.defaultdict(list)
for f in range(N):
    t = collections.Counter(T.get(f, [])); o = collections.Counter(norm(c['w']) for c in C if c['f0'] <= f <= c['f1'])
    for w in (t - o): bad[('手本だけ', w)].append(f)
    for w in (o - t): bad[('うちだけ', w)].append(f)
rows = []
for k, fs in bad.items():
    s = p = None
    for f in fs + [None]:
        if f is not None and s is not None and f == p + 1: p = f; continue
        if s is not None and p - s >= 3: rows.append((s, p, k[0], k[1]))
        s = p = f
rows.sort(); print('4コマ以上の食い違い', len(rows))
for r in rows: print(r)
