# 手本とうちを同じ「手本の秒」で数字で比べる（カットごと）→ JSON と md の表
# 使い方:
#   python3 tools/sabun2.py <うちの動画 | stills:<フォルダ>> <出す json> [--md rikai/sabun2.md] [--times 1.0,2.5,...]
#   stills:<フォルダ> … proj の Ref（手本の秒そのまま・60fps）の静止画 u{f:05d}.png（f＝round(t*60)）
# 測る物（字幕の帯 y 1400〜1640 は伏せる＝英語と日本語で中身が違う）
#   ① 物の位置・大きさ：明るい所（灰 >70・2px の小さい点は消す）の重心 cx,cy（画面の %）と広がり（座標の標準偏差＝画面の %）・主軸の角度
#   ② 形：線の地図（Canny→細線）の一致 F（距離 1.2% 以内を一致）
#   ③ 線の太さ・光：明るい画素の明るさの形＝上位 1% の明るさ・>40 の画素÷>150 の画素（にじみの広さ）
#   ④ 色：Lab の平均の ΔE（CIE76）
import glob as _g, os as _o
REF = _o.environ.get('REF') or sorted(_g.glob('ref/*.mp4'))[0]   # 手本（作業フォルダの ref/ の mp4）
import sys, json, os, cv2, numpy as np
a = sys.argv[1:]; md = None; times = None
if '--md' in a: i = a.index('--md'); md = a[i + 1]; del a[i:i + 2]
if '--times' in a: i = a.index('--times'); times = [float(x) for x in a[i + 1].split(',')]; del a[i:i + 2]
src, out = a[0], a[1]
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R2O = json.load(open(f'{ROOT}/rikai/ref2out_sec.json'))
SC = json.load(open(f'{ROOT}/rikai/scenes.json'))   # [[始め, 終わり, 名前], ...]
if times is None:
    times = []
    for s0, s1, _ in SC:
        d = s1 - s0
        for u in ([0.5] if d < 1.2 else [0.2, 0.5, 0.85]): times.append(round(s0 + d * u, 2))
W, H = 1080, 1920

def frames(path, idx):
    want = sorted(set(idx)); cap = cv2.VideoCapture(path); got = {}; n = 0; j = 0
    while j < len(want):
        ok, fr = cap.read()
        if not ok: break
        if n == want[j]:
            got[n] = fr
            while j < len(want) and want[j] == n: j += 1
        n += 1
    return [got.get(i) for i in idx]

def feat(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    g[1400:1640] = 0; img = img.copy(); img[1400:1640] = 0
    m = (g > 70).astype(np.uint8); m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    ys, xs = np.nonzero(m)
    if len(xs) < 50: return None
    cx, cy = xs.mean() / W * 100, ys.mean() / H * 100
    sx, sy = xs.std() / W * 100, ys.std() / H * 100
    c = np.cov(np.stack([xs / W, ys / H])); ev, evec = np.linalg.eigh(c); v = evec[:, 1]; ang = float(np.degrees(np.arctan2(v[1], v[0]))) % 180
    e = cv2.Canny(cv2.GaussianBlur(g.astype(np.uint8), (5, 5), 0), 40, 110); e[1400:1640] = 0
    hi = float(np.percentile(g[g > 20], 99)) if (g > 20).sum() > 100 else 0
    halo = float((g > 40).sum() / max(1, (g > 150).sum()))
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32).mean(0)
    lab = [lab[0] * 100 / 255, lab[1] - 128, lab[2] - 128]
    return dict(cx=cx, cy=cy, sx=sx, sy=sy, ang=ang, edge=e, hi=hi, halo=halo, lab=lab, fill=float(m.mean() * 100))

def edgeF(e1, e2, tol=13):
    if e1.sum() == 0 or e2.sum() == 0: return 0.0
    d1 = cv2.distanceTransform((e1 == 0).astype(np.uint8), cv2.DIST_L2, 3)
    d2 = cv2.distanceTransform((e2 == 0).astype(np.uint8), cv2.DIST_L2, 3)
    p = (d1[e2 > 0] <= tol).mean(); r = (d2[e1 > 0] <= tol).mean()
    return float(2 * p * r / max(1e-6, p + r))

ref = frames(REF, [int(round(t * 60)) for t in times])
if src.startswith('stills:'):
    d = src[7:]; ours = [cv2.imread(f'{d}/u{int(round(t * 60)):05d}.png') for t in times]
else:
    ours = frames(src, [int(round(R2O[min(len(R2O) - 1, int(round(t * 60)))] * 60)) for t in times])

def sceneof(t):
    for k, (s0, s1, n) in enumerate(SC):
        if t < s1: return k, n
    return len(SC) - 1, SC[-1][2]

def judge(name, v):
    th = {'pos': (2, 5), 'size': (3, 10), 'ang': (3, 8), 'F': (None, None), 'hi': (8, 20), 'halo': (25, 60), 'dE': (3, 6)}
    if v is None: return '⚪'
    if name == 'F': return '🟢' if v >= 0.55 else '🟡' if v >= 0.35 else '🔴'
    g, y = th[name]; v = abs(v); return '🟢' if v <= g else '🟡' if v <= y else '🔴'

rows = []
for t, r, u in zip(times, ref, ours):
    k, n = sceneof(t)
    if r is None or u is None: continue
    fr, fu = feat(r), feat(u)
    if fr is None or fu is None: rows.append(dict(t=t, k=k, name=n, skip=True)); continue
    dpos = float(np.hypot(fu['cx'] - fr['cx'], fu['cy'] - fr['cy']))
    dsize = float((np.hypot(fu['sx'], fu['sy']) / np.hypot(fr['sx'], fr['sy']) - 1) * 100)
    dang = float(((fu['ang'] - fr['ang'] + 90) % 180) - 90)
    F = edgeF(fr['edge'], fu['edge'])
    dhi = float((fu['hi'] / max(1, fr['hi']) - 1) * 100); dhalo = float((fu['halo'] / max(0.1, fr['halo']) - 1) * 100)
    dE = float(np.linalg.norm(np.array(fu['lab']) - np.array(fr['lab'])))
    v = dict(pos=dpos, size=dsize, ang=dang, F=F, hi=dhi, halo=dhalo, dE=dE)
    rows.append(dict(t=t, k=k, name=n, ref=dict((x, fr[x]) for x in ['cx', 'cy', 'sx', 'sy', 'ang', 'hi', 'halo', 'fill']),
                     ours=dict((x, fu[x]) for x in ['cx', 'cy', 'sx', 'sy', 'ang', 'hi', 'halo', 'fill']), d=v, j={x: judge(x, v[x]) for x in v}))
json.dump(rows, open(out, 'w'), ensure_ascii=False, indent=1)
cnt = {'🔴': 0, '🟡': 0, '🟢': 0}
for r in rows:
    for x in r.get('j', {}).values(): cnt[x] = cnt.get(x, 0) + 1
print(out, len(rows), '行', cnt)
if md:
    L = ['| 秒 | 場面 | 位置 Δ% | 大きさ Δ% | 角度 Δ° | 線 F | 光の芯 Δ% | にじみ Δ% | 色 ΔE |', '|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        if r.get('skip'): L.append(f"| {r['t']} | {r['name']} | 暗いコマ（比べん） |||||||"); continue
        d, j = r['d'], r['j']
        L.append(f"| {r['t']} | {r['name']} | {j['pos']}{d['pos']:.1f} | {j['size']}{d['size']:+.0f} | {j['ang']}{d['ang']:+.0f} | {j['F']}{d['F']:.2f} | {j['hi']}{d['hi']:+.0f} | {j['halo']}{d['halo']:+.0f} | {j['dE']}{d['dE']:.1f} |")
    L.append(f"\n数：🔴{cnt['🔴']}・🟡{cnt['🟡']}・🟢{cnt['🟢']}")
    open(md, 'w').write('\n'.join(L) + '\n'); print(md)
