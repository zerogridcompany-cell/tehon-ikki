# 線の断面（光る線の太さ・にじみの広がり）を手本とうちで測る
# 使い方: python3 tools/sendan.py stills:<フォルダ> [コマ,...]  … 線の芯（明るさの山 >200 の細線）から法線の向きに ±30px の明るさを平均
# 出力：芯の幅（半値幅 px）・にじみが山の 25%/10% に落ちる距離 px・芯の明るさ
import glob as _g, os as _o
REF = _o.environ.get('REF') or sorted(_g.glob('ref/*.mp4'))[0]   # 手本（作業フォルダの ref/ の mp4）
import sys, cv2, numpy as np
d = sys.argv[1][7:]; fs = [int(x) for x in (sys.argv[2] if len(sys.argv) > 2 else open('rikai/sabun_frames.txt').read().strip()).split(',')]
cap = cv2.VideoCapture(REF); want = set(fs); got = {}; n = 0
while len(got) < len(want):
    ok, fr = cap.read()
    if not ok: break
    if n in want: got[n] = fr
    n += 1
def prof(img):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32); g[1400:1640] = 0; g[:330] = 0   # 字幕と上の見出しを伏せる
    gs = cv2.GaussianBlur(g, (0, 0), 1.2); gx = cv2.Sobel(gs, cv2.CV_32F, 1, 0); gy = cv2.Sobel(gs, cv2.CV_32F, 0, 1)
    # 山：明るさ >200 で、法線方向の両どなりより明るい点
    ys, xs = np.nonzero(gs > 200); P = []
    rng = np.random.default_rng(0); idx = rng.choice(len(xs), min(4000, len(xs)), replace=False) if len(xs) else []
    for i in idx:
        x, y = xs[i], ys[i]
        if x < 32 or y < 32 or x > g.shape[1] - 33 or y > g.shape[0] - 33: continue
        # 線の法線＝明るさの勾配が一番大きい向き（近く 5x5 の構造テンソル）
        sx = gx[y - 3:y + 4, x - 3:x + 4]; sy = gy[y - 3:y + 4, x - 3:x + 4]
        J = np.array([[(sx * sx).sum(), (sx * sy).sum()], [(sx * sy).sum(), (sy * sy).sum()]]); w, v = np.linalg.eigh(J); nx, ny = v[:, 1]
        if w[1] < 4 * max(w[0], 1e-3): continue   # 角・点は外す
        t = np.arange(-30, 31); px = (x + nx * t).astype(np.float32); py = (y + ny * t).astype(np.float32)
        s = cv2.remap(g, px.reshape(1, -1), py.reshape(1, -1), cv2.INTER_LINEAR)[0]
        k = int(np.argmax(s[25:36])) + 25
        if abs(k - 30) > 2: continue
        s = np.roll(s, 30 - k); P.append(s)
    if not P: return None
    m = np.median(np.array(P), 0); pk = m[30]; base = np.median(m[[0, 1, 2, 58, 59, 60]])
    def wid(fr):
        lv = base + (pk - base) * fr; L = 30
        while L > 0 and m[L] > lv: L -= 1
        R = 30
        while R < 60 and m[R] > lv: R += 1
        return (R - L)
    return dict(n=len(P), peak=float(pk), fwhm=wid(0.5), w25=wid(0.25), w10=wid(0.10), prof=m)
A = []; B = []
for f in fs:
    u = cv2.imread(f'{d}/u{f:05d}.png')
    if f not in got or u is None: continue
    a, b = prof(got[f]), prof(u)
    if a and b: A.append(a); B.append(b)
for name, X in [('手本', A), ('うち', B)]:
    print(name, '本数', sum(x['n'] for x in X), '芯の幅(半値) px', np.median([x['fwhm'] for x in X]), '25% 幅', np.median([x['w25'] for x in X]), '10% 幅', np.median([x['w10'] for x in X]), '芯', round(float(np.median([x['peak'] for x in X])), 1))
pa = np.median(np.array([x['prof'] for x in A]), 0); pb = np.median(np.array([x['prof'] for x in B]), 0)
print('断面 手本', ' '.join(f'{v:.0f}' for v in pa[18:43])); print('断面 うち', ' '.join(f'{v:.0f}' for v in pb[18:43]))
