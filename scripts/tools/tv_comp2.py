"""テレビの場面（29・33・37・38・42）の組み直し 2版。tv_comp.py（1版）は残す。

python3 tv_comp2.py <作業フォルダ> [--only 29,33] [--off 秒]
1版から変えた所（10/25 v6 で見た弱い所）：
- 背景の置き方：手本の頭のコマで測った動き（track.json）を始まりにして、1コマずつ ECC（アフィン）で Codex の絵を手本に合わせる
- 画面の形：Codex の絵の黒い画面から取ってなめらかにする（1版は手本の頭のコマの黒い所＝縁がギザギザ）
- 背景の色：色の2次式に「画面の中の位置（x・y の2次）」を足す＝窓の青・ランプの暖かさの場所の違い
- 字幕は白い画素を探して外す（1版は 300〜400 の帯）
出す物：cuts/<番号>.mp4（前の物は cuts/<番号>_tv1.mp4 に控え）・_all.json（model tv_comp2）
"""
import argparse, json, os, shutil, subprocess, sys
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--only"); ap.add_argument("--off", type=float, default=2876.7928 - 9.6)
g = ap.parse_args()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from geo import geo
_G = geo(g.w); W, H = _G["W"], _G["H"]  # 10/30 geo
FPS, FPS_W = (30000 / 1001, "30000/1001") if abs(_G["FPS"] - 29.97) < 0.01 else (_G["FPS"], _G["FPS_FF"])  # 29.97 の手本は前のまま（30000/1001）
E = {s["i"]: s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"]}
S = json.load(open(f"{g.w}/mg/tv/screens.json"))
TR = {int(k): v for k, v in json.load(open(f"{g.w}/mg/tv/track.json")).items()}
plate = cv2.imread(f"{g.w}/mg/tv/plate.png")
rx, ry, rw, rh = S["ref_screen"]; px, py, pw, ph = S["plate_screen"]
S0 = np.array([[rw / pw, 0, rx - px * rw / pw], [0, rh / ph, ry - py * rh / ph], [0, 0, 1]])

# 画面の形（Codex の絵の黒い所・真ん中を含む塊）をなめらかに
pg = cv2.cvtColor(plate, cv2.COLOR_BGR2GRAY)
n, lab, st, _ = cv2.connectedComponentsWithStats((pg < 16).astype(np.uint8))
k = lab[py + ph // 2, px + pw // 2]
pscr = (lab == k).astype(np.uint8) * 255
pscr = cv2.morphologyEx(pscr, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
# 上の角の出っ張り（10/25 見えた）を消す：大きめに開いてから凸包
pscr = cv2.morphologyEx(pscr, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (45, 45)))
cs, _ = cv2.findContours(pscr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
pscr = np.zeros_like(pscr); cv2.fillPoly(pscr, [cv2.convexHull(max(cs, key=cv2.contourArea))], 255)
pscr = (cv2.GaussianBlur(pscr, (0, 0), 6) > 127).astype(np.uint8) * 255

cap = cv2.VideoCapture(f"{g.w}/mg/tv/src/baron_2875.mp4")
def bframe(t):
    cap.set(cv2.CAP_PROP_POS_MSEC, (t - 2875.0) * 1000); ok, im = cap.read(); return im if ok else None
def ref(f):
    return cv2.imread(f"{g.w}/txt/f/{f + 1:05d}.jpg")
def capmask(im):
    f = im.astype(np.int16); mx = f.max(2); mn = f.min(2)
    m = ((mx > 200) & (mx - mn < 45)).astype(np.uint8); m[:150] = 0; m[600:] = 0
    return cv2.dilate(m, np.ones((17, 17), np.uint8)) > 0

YY, XX = np.mgrid[0:H, 0:W]
def poly(x, pos=None):
    x = x.reshape(-1, 3).astype(np.float64) / 255
    b, gg, r = x[:, 0], x[:, 1], x[:, 2]
    cols = [np.ones_like(b), b, gg, r, b * b, gg * gg, r * r, b * gg, gg * r, r * b]
    if pos is not None:
        u, v = pos
        cols += [u, v, u * u, v * v, u * v, b * u, gg * u, r * u, b * v, gg * v, r * v]
    return np.stack(cols, 1)
def fitc(srcs, dsts, masks, spatial):
    X, Y = [], []
    rng = np.random.default_rng(0)
    for s, d, m in zip(srcs, dsts, masks):
        i = np.flatnonzero(m.ravel()); i = rng.choice(i, min(len(i), 6000), replace=False)
        pos = ((XX.ravel()[i] / W - 0.5), (YY.ravel()[i] / H - 0.5)) if spatial else None
        X.append(poly(s.reshape(-1, 3)[i], pos)); Y.append(d.reshape(-1, 3)[i].astype(np.float64) / 255)
    X = np.concatenate(X); Y = np.concatenate(Y)
    return np.linalg.lstsq(X, Y, rcond=None)[0]
def applyc(img, c, spatial):
    pos = ((XX / W - 0.5).ravel(), (YY / H - 0.5).ravel()) if spatial else None
    return np.clip(poly(img, pos) @ c * 255, 0, 255).reshape(img.shape).astype(np.uint8)

def fitc1(srcs, dsts, masks):
    # 中の対談：チャンネルごとの2次だけ（混ぜ項で明るい窓が青くまだらに崩れた＝10/25）
    K = []
    for ch in range(3):
        xs = np.concatenate([s[..., ch][m] for s, m in zip(srcs, masks)]).astype(np.float64) / 255
        ys = np.concatenate([d[..., ch][m] for d, m in zip(dsts, masks)]).astype(np.float64) / 255
        K.append(np.linalg.lstsq(np.stack([xs * xs, xs, np.ones_like(xs)], 1), ys, rcond=None)[0])
    return K
def applyc1(img, K):
    f = img.astype(np.float32) / 255; o = np.zeros_like(f)
    for ch in range(3):
        o[..., ch] = K[ch][0] * f[..., ch] ** 2 + K[ch][1] * f[..., ch] + K[ch][2]
    return np.clip(o * 255, 0, 255).astype(np.uint8)

def ecc(tmpl, inp, M, mask):
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 150, 1e-6)
    M = M.astype(np.float32).copy()
    for s in (0.25, 0.5, 1.0):
        a = cv2.resize(inp, None, fx=s, fy=s); b = cv2.resize(tmpl, (int(W * s), int(H * s)))
        mk = cv2.resize(mask.astype(np.uint8), (b.shape[1], b.shape[0]), interpolation=cv2.INTER_NEAREST)
        Ms = M.copy(); Ms[:, 2] *= s
        mki = cv2.warpAffine(mk, Ms, (a.shape[1], a.shape[0]), flags=cv2.INTER_NEAREST)  # マスクは入力（絵）側の大きさ
        try:
            _, Ms = cv2.findTransformECC(b, a, Ms, cv2.MOTION_AFFINE, crit, mki, 5)
            M = Ms.copy(); M[:, 2] /= s
        except cv2.error as e:
            print("  ECC 失敗", s, str(e)[:80], flush=True)
    return M
def gray(x):
    return cv2.cvtColor(x, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255

allp = f"{g.w}/cuts/_all.json"; allr = json.load(open(allp))
only = [int(x) for x in g.only.split(",")] if g.only else [29, 33, 37, 38, 42]
for i in only:
    f0, f1 = int(round(E[i]["t0"] * FPS)), int(round(E[i]["t1"] * FPS))
    frames = [f for f in range(f0, f1) if f in TR]
    mid = frames[len(frames) // 2]
    R = {f: ref(f) for f in frames}
    # 背景：始まり＝track（手本の頭のコマ→このコマ）∘ S0（絵→手本の頭のコマ）。ECC は 画面→絵 の向き
    P = {}
    for f in sorted(frames, key=lambda f: abs(f - mid)):
        near = min(P, key=lambda m: abs(m - f), default=None)
        if near is None:
            fw = np.vstack([np.array(TR[f]["M"]), [0, 0, 1]]) @ S0
            M0 = np.linalg.inv(fw)[:2]
        else:
            M0 = P[near]
        scr_f = cv2.warpAffine(pscr, M0, (W, H), flags=cv2.WARP_INVERSE_MAP) > 0
        mk = ~cv2.dilate(scr_f.astype(np.uint8), np.ones((25, 25), np.uint8)).astype(bool) & ~capmask(R[f])
        P[f] = ecc(gray(R[f]), gray(plate), M0, mk)  # ECC は明るさの1次の違いに強い＝色を当てる前の絵のまま
    # 中の対談：真ん中のコマで 対談→画面 を決める（1版と同じ：覆う大きさ→SIFT が5点以上なら置き換え）
    bm = bframe(mid / FPS + g.off)
    scr_mid = cv2.warpAffine(pscr, P[mid], (W, H), flags=cv2.WARP_INVERSE_MAP) > 0
    ys, xs = np.nonzero(scr_mid); bx0, by0, bx1, by1 = xs.min(), ys.min(), xs.max(), ys.max()
    bh_, bw_ = bm.shape[:2]; sc = max((bx1 - bx0) / bw_, (by1 - by0) / bh_)
    A = np.float32([[sc, 0, (bx0 + bx1) / 2 - bw_ * sc / 2], [0, sc, (by0 + by1) / 2 - bh_ * sc / 2]])
    sift = cv2.SIFT_create(3000)
    k1, d1 = sift.detectAndCompute(cv2.cvtColor(bm, cv2.COLOR_BGR2GRAY), None)
    k2, d2 = sift.detectAndCompute(cv2.cvtColor(R[mid], cv2.COLOR_BGR2GRAY), None)
    mm = [x for x, y in cv2.BFMatcher().knnMatch(d1, d2, k=2) if x.distance < 0.75 * y.distance]
    mm = [x for x in mm if scr_mid[int(min(H - 1, k2[x.trainIdx].pt[1])), int(min(W - 1, k2[x.trainIdx].pt[0]))]]
    cc = 0
    if len(mm) >= 6:
        A2, inl = cv2.estimateAffinePartial2D(np.float32([k1[x.queryIdx].pt for x in mm]), np.float32([k2[x.trainIdx].pt for x in mm]),
                                              method=cv2.RANSAC, ransacReprojThreshold=3)
        cc = int(inl.sum()) if inl is not None else 0
        if A2 is not None and cc >= 5:
            # 目印の置き方と覆う大きさを、真ん中のコマの画面の中で比べて良い方（29 は 6点で外れ、38・42 は 7点で当たった）
            inside = cv2.erode(scr_mid.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
            def corr(AA):
                w_ = cv2.cvtColor(cv2.warpAffine(bm, AA, (W, H)), cv2.COLOR_BGR2GRAY).astype(np.float32)[inside]
                r_ = cv2.cvtColor(R[mid], cv2.COLOR_BGR2GRAY).astype(np.float32)[inside]
                return float(np.corrcoef(w_, r_)[0, 1]) if w_.std() > 1 else -1
            if corr(np.float32(A2)) > corr(A):
                A = A2
    # 候補3：元の対談が2人並び（左＝イーロン x20-630 y144-576）の時は、左の枠だけを画面に覆う大きさで置く（29）
    lx0, ly0, lx1, ly1 = 20, 144, 630, 576
    sc2 = max((bx1 - bx0) / (lx1 - lx0), (by1 - by0) / (ly1 - ly0))
    A3 = np.float32([[sc2, 0, (bx0 + bx1) / 2 - (lx0 + lx1) / 2 * sc2], [0, sc2, (by0 + by1) / 2 - (ly0 + ly1) / 2 * sc2]])
    inside = cv2.erode(scr_mid.astype(np.uint8), np.ones((15, 15), np.uint8)) > 0
    def corr2(AA):
        w_ = cv2.cvtColor(cv2.warpAffine(bm, AA, (W, H)), cv2.COLOR_BGR2GRAY).astype(np.float32)[inside]
        r_ = cv2.cvtColor(R[mid], cv2.COLOR_BGR2GRAY).astype(np.float32)[inside]
        return float(np.corrcoef(w_, r_)[0, 1]) if w_.std() > 1 else -1
    if corr2(A3) > corr2(np.float32(A)):
        A = A3; cc = "左の枠"
    Bm = np.vstack([A, [0, 0, 1]])
    Fmid = np.linalg.inv(np.vstack([P[mid], [0, 0, 1]]))  # 絵→画面（真ん中）
    outs = []
    for f in frames:
        Ff = np.linalg.inv(np.vstack([P[f], [0, 0, 1]]))
        bg = cv2.warpAffine(plate, Ff[:2], (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
        sm = cv2.warpAffine(pscr, Ff[:2], (W, H), flags=cv2.INTER_LINEAR).astype(np.float32) / 255
        b = bframe(f / FPS + g.off)
        inner = cv2.warpAffine(b, (Ff @ np.linalg.inv(Fmid) @ Bm)[:2], (W, H), flags=cv2.INTER_LANCZOS4)
        outs.append((bg, inner, sm))
    rs = [R[f] for f in frames]
    cms = [capmask(r) for r in rs]
    cb = fitc([o[0] for o in outs], rs, [(o[2] < 0.02) & ~c for o, c in zip(outs, cms)], True)
    ci = fitc1([o[1] for o in outs], rs, [(cv2.erode((o[2] > 0.98).astype(np.uint8), np.ones((9, 9), np.uint8)) > 0) & ~c for o, c in zip(outs, cms)])
    if os.path.exists(f"{g.w}/cuts/{i}.mp4") and not os.path.exists(f"{g.w}/cuts/{i}_tv1.mp4"):
        shutil.copy(f"{g.w}/cuts/{i}.mp4", f"{g.w}/cuts/{i}_tv1.mp4")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", FPS_W,
                          "-i", "-", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", f"{g.w}/cuts/{i}.mp4"], stdin=subprocess.PIPE)
    ss = []
    for (bg, inner, sm), r in zip(outs, rs):
        a = applyc(bg, cb, True); b = applyc1(inner, ci)
        soft = cv2.GaussianBlur(sm, (0, 0), 1.2)[..., None]
        fr = (a * (1 - soft) + b * soft).astype(np.uint8)
        p.stdin.write(fr.tobytes())
        ss.append(ssim(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), cv2.cvtColor(r, cv2.COLOR_BGR2GRAY)))
    p.stdin.close(); p.wait()
    allr[str(i)] = {"track": 1, "model": "tv_comp2", "ssim_color": None, "ssim": round(float(np.mean(ss)), 3), "frames": len(frames), "inner_pts": cc}
    json.dump(allr, open(allp, "w"), indent=1)
    print(i, "コマ", len(frames), "中の当て 点", cc, "SSIM", round(float(np.mean(ss)), 3), flush=True)
