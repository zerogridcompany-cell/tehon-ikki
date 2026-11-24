# カメラの逆算（絵の重ね合わせ）：手本のコマとうちの静止画（RefBare＝見出しなし）の線の地図を重ね、
# 「うちの絵を何倍して・どれだけずらせば手本に重なるか」(s, dx, dy) をコマごとに出す → World.tsx の CORR（画角×s・向きを dx,dy だけ振る）
# 使い方: python3 tools/kamera_fit.py <静止画フォルダ> <出す json> [コマ,...]   （コマ＝手本の 60fps のコマ番号）
# 線の地図＝270x480 に縮めて Canny → ぼかし（σ3）。字幕の帯と上の見出しの帯（手本の英字の札が乗る所）は伏せる
import glob as _g, os as _o
REF = _o.environ.get('REF') or sorted(_g.glob('ref/*.mp4'))[0]   # 手本（作業フォルダの ref/ の mp4）
import sys, json, cv2, numpy as np
d, out = sys.argv[1], sys.argv[2]
fs = [int(x) for x in (sys.argv[3] if len(sys.argv) > 3 else open('rikai/sabun_frames.txt').read().strip()).split(',')]
cap = cv2.VideoCapture(REF); want = set(fs); got = {}; n = 0
while len(got) < len(want):
    ok, fr = cap.read()
    if not ok: break
    if n in want: got[n] = fr
    n += 1
w, h = 270, 480
def emap(img, top=0.0):
    g = cv2.cvtColor(cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    e = cv2.Canny(cv2.GaussianBlur(g, (3, 3), 0), 30, 90).astype(np.float32)
    e[int(h * 0.728):int(h * 0.855)] = 0
    if top: e[:int(h * top)] = 0
    e = cv2.GaussianBlur(e, (0, 0), 3); e -= e.mean(); return e
def xcorr(A, B):
    P = np.zeros((h * 2, w * 2), np.float32); Q = P.copy(); P[:h, :w] = A; Q[:h, :w] = B
    c = np.fft.irfft2(np.fft.rfft2(P) * np.conj(np.fft.rfft2(Q)), s=P.shape)
    lim_y, lim_x = int(h * 0.3), int(w * 0.3)
    c2 = np.full_like(c, -1e9); c2[:lim_y, :lim_x] = c[:lim_y, :lim_x]; c2[-lim_y:, :lim_x] = c[-lim_y:, :lim_x]; c2[:lim_y, -lim_x:] = c[:lim_y, -lim_x:]; c2[-lim_y:, -lim_x:] = c[-lim_y:, -lim_x:]
    iy, ix = np.unravel_index(np.argmax(c2), c2.shape); v = c2[iy, ix]
    if iy > h: iy -= 2 * h
    if ix > w: ix -= 2 * w
    return v, ix, iy
res = []
for f in fs:
    u = cv2.imread(f'{d}/u{f:05d}.png')
    if u is None or f not in got: continue
    A = emap(got[f], 0.16); B0 = emap(u, 0.16); nA = np.linalg.norm(A)
    best = None
    for s in np.geomspace(0.55, 1.9, 61):
        M = np.array([[s, 0, (1 - s) * w / 2], [0, s, (1 - s) * h / 2]], np.float32)
        B = cv2.warpAffine(B0, M, (w, h)); v, ix, iy = xcorr(A, B); sc = v / (nA * np.linalg.norm(B) + 1e-6)
        if best is None or sc > best[0]: best = (sc, float(s), ix / w, iy / h)
    v0, _, _ = xcorr(A, B0); s0 = v0 / (nA * np.linalg.norm(B0) + 1e-6)
    v1 = float((A * B0).sum() / (nA * np.linalg.norm(B0) + 1e-6))
    res.append(dict(f=f, t=round(f / 60, 3), s=round(best[1], 3), dx=round(best[2], 3), dy=round(best[3], 3), score=round(float(best[0]), 3), score_now=round(v1, 3)))
    print(res[-1])
json.dump(res, open(out, 'w'), indent=1)
