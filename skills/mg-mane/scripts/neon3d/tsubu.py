# 金の粒を数える：手本とうちを同じ手本の秒で。黄の小さい四角（面積 6〜900px・縦横比 0.5〜2）を字幕の帯と上 12% を伏せて数える
# 使い方: python3 tools/tsubu.py <うちの動画> [秒,秒,...]
import sys, json, cv2, numpy as np
import glob, os
REF = os.environ.get('REF') or sorted(glob.glob('ref/*.mp4'))[0]
R2O = json.load(open('rikai/ref2out_sec.json')) if os.path.exists('rikai/ref2out_sec.json') else None
ts = [float(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 else [6.2,7.0,8.0,11.5,12.5,15.0,17.5,20.0,22.0,24.5,27.0,30.0,33.0,36.0,41.0,43.5,46.0,47.5,51.0,53.7,56.5,58.7,61.0,63.5]
def grab(p, idx):
    cap = cv2.VideoCapture(p); out = {}; n = 0; w = set(idx)
    while len(out) < len(w):
        ok, f = cap.read()
        if not ok: break
        if n in w: out[n] = f
        n += 1
    return [out.get(i) for i in idx]
def blobs(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV); m = ((hsv[..., 0] >= 15) & (hsv[..., 0] <= 34) & (hsv[..., 1] > 70) & (hsv[..., 2] > 80)).astype(np.uint8)
    m[1380:1660] = 0; m[:230] = 0
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8); A = []; ys = []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if 6 <= a <= 900 and 0.5 <= w / max(1, h) <= 2.0 and a >= 0.45 * w * h: A.append(a); ys.append(y)
    return A
R = grab(REF, [round(t * 60) for t in ts])
U = [cv2.imread(f'{sys.argv[1][7:]}/u{round(t * 60):05d}.png') for t in ts] if sys.argv[1].startswith('stills:') else grab(sys.argv[1], [round((R2O[round(t * 60)] if R2O else t) * 60) for t in ts])
ra, ua = [], []
for t, r, u in zip(ts, R, U):
    a, b = blobs(r), blobs(u); ra.append(a); ua.append(b)
    print(f'{t:5} 手本 {len(a):3}個 面積中央 {np.median(a) if a else 0:5.0f} | うち {len(b):3}個 {np.median(b) if b else 0:5.0f}')
f = lambda L: (np.median([len(x) for x in L]), np.median([v for x in L for v in x]) if any(L) else 0, np.percentile([v for x in L for v in x], 90) if any(L) else 0)
print('手本 数中央 %.0f 面積中央 %.0f 90%% %.0f' % f(ra)); print('うち 数中央 %.0f 面積中央 %.0f 90%% %.0f' % f(ua))
