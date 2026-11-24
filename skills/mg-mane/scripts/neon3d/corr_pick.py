# 場面ごとに「重なり（score_now）の平均」が高い方の直し（corr）を選ぶ：python3 tools/corr_pick.py <corrA> <fitA> <corrB> <fitB> <出す corr>
import glob as _g, os as _o
REF = _o.environ.get('REF') or sorted(_g.glob('ref/*.mp4'))[0]   # 手本（作業フォルダの ref/ の mp4）
import sys, json
cA, fA, cB, fB, out = [sys.argv[i] for i in range(1, 6)]
cA, fA, cB, fB = [json.load(open(x)) for x in (cA, fA, cB, fB)]
SC = json.load(open('rikai/scenes.json'))
def sc(t):
    for k, (a, b, n) in enumerate(SC):
        if t < b: return str(k)
    return str(len(SC) - 1)
mA, mB = {}, {}
for r in fA: mA.setdefault(sc(r['t']), []).append(r['score_now'])
for r in fB: mB.setdefault(sc(r['t']), []).append(r['score_now'])
o = {}; pick = {}
for k in sorted(set(mA) | set(mB), key=int):
    a = sum(mA.get(k, [0])) / len(mA.get(k, [1])); b = sum(mB.get(k, [0])) / len(mB.get(k, [1]))
    src = cB if b > a else cA; pick[k] = ('B' if b > a else 'A', round(a, 3), round(b, 3))
    if k in src: o[k] = src[k]
json.dump(o, open(out, 'w'), indent=0); print(pick)
