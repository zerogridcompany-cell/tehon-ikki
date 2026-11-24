# kamera_fit の結果 → proj/src/rg/corr.json（場面ごとの [t, s, dx, dy]）。前の corr.json に掛け合わせる（何回でも重ねて詰める）
# 使い方: python3 tools/corr_make.py <fit.json> [--min-gain 0.04] [--only 3,7] [--skip 6,13]
import glob as _g, os as _o
REF = _o.environ.get('REF') or sorted(_g.glob('ref/*.mp4'))[0]   # 手本（作業フォルダの ref/ の mp4）
import sys, json, os
a = sys.argv[1:]; fit = json.load(open(a[0])); g = 0.04; only = None; skip = set()
if '--min-gain' in a: g = float(a[a.index('--min-gain') + 1])
if '--only' in a: only = set(int(x) for x in a[a.index('--only') + 1].split(','))
if '--skip' in a: skip = set(int(x) for x in a[a.index('--skip') + 1].split(','))
SC = json.load(open('rikai/scenes.json')); P = 'proj/src/rg/corr.json'
cur = json.load(open(P)) if os.path.exists(P) else {}
def sc(t):
    for k, (s0, s1, _) in enumerate(SC):
        if t < s1: return k
    return len(SC) - 1
def at(rows, t):   # 今の直し（近い鍵の線形）
    if not rows: return [1, 0, 0]
    rows = sorted(rows)
    if t <= rows[0][0]: return rows[0][1:]
    if t >= rows[-1][0]: return rows[-1][1:]
    for r0, r1 in zip(rows, rows[1:]):
        if r0[0] <= t <= r1[0]:
            u = (t - r0[0]) / (r1[0] - r0[0]); return [r0[j] + (r1[j] - r0[j]) * u for j in (1, 2, 3)]
new = {}
for r in fit:
    k = sc(r['t'])
    if (only and k not in only) or k in skip: continue
    ok = r['score'] - r['score_now'] >= g and 0.7 <= r['s'] <= 1.7 and abs(r['dx']) <= 0.22 and abs(r['dy']) <= 0.22
    base = at(cur.get(str(k), []), r['t'])
    if ok:   # 重ねる：倍率は掛け算・ずれは今の倍率で割って足す（近似）
        new.setdefault(str(k), []).append([r['t'], round(base[0] * r['s'], 4), round(base[1] + r['dx'], 4), round(base[2] + r['dy'], 4)])
for k, rows in new.items(): cur[k] = sorted(rows if len(rows) == len([1 for r in fit if sc(r['t']) == int(k)]) or not cur.get(k) else rows + [x for x in cur[k] if all(abs(x[0] - y[0]) > 0.05 for y in rows)])
json.dump(cur, open(P, 'w'), indent=0); print(P, {k: len(v) for k, v in cur.items()})
