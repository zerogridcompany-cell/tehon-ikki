"""テレビの場面（29・33・37・38・42）を組む：背景＝Codex の絵、画面の中＝対談の動画、カメラ＝手本から測った動き。

python3 tv_comp.py <作業フォルダ>
- mg/tv/plate.png（Codex）・mg/tv/screens.json（黒い画面の位置：手本の頭のコマと Codex の絵）・mg/tv/track.json（手本の頭のコマ→各コマ）
- 中の動画＝mg/tv/src/baron_2875.mp4（2875秒から）。手本の 9.6秒＝対談の 2876.79秒（音で当てた）
- 中の切り抜き：場面ごとに真ん中のコマで、対談のコマ→手本の画面を SIFT の相似で当てる
- 色：背景と画面の中を分けて、手本の色に2次の式で合わせる（場面ごと）
- 出す物：cuts/<番号>.mp4・cuts/<番号>.json（_all.json にも足す）
"""
import argparse, json, os, subprocess, sys
import cv2
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--off", type=float, default=2876.7928 - 9.6)
g = ap.parse_args()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from geo import geo
_G = geo(g.w); W, H = _G["W"], _G["H"]  # 10/30 geo
FPS, FPS_W = (30000 / 1001, "30000/1001") if abs(_G["FPS"] - 29.97) < 0.01 else (_G["FPS"], _G["FPS_FF"])  # 29.97 の手本は前のまま（30000/1001）
E = {s["i"]: s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"]}
S = json.load(open(f"{g.w}/mg/tv/screens.json"))
TR = {int(k): v for k, v in json.load(open(f"{g.w}/mg/tv/track.json")).items()}
plate = cv2.imread(f"{g.w}/mg/tv/plate.png")
refp = cv2.imread(f"{g.w}/mg/tv/ref_plate.png")
rx, ry, rw, rh = S["ref_screen"]; px, py, pw, ph = S["plate_screen"]
# Codex の絵 → 手本の頭のコマ（画面の箱を揃える）
S0 = np.array([[rw / pw, 0, rx - px * rw / pw], [0, rh / ph, ry - py * rh / ph], [0, 0, 1]])
# 画面の形（手本の頭のコマの黒い所）
g0 = cv2.cvtColor(refp, cv2.COLOR_BGR2GRAY)
scr = np.zeros_like(g0); n, lab, st, _ = cv2.connectedComponentsWithStats((g0 < 18).astype(np.uint8))
k = max(range(1, n), key=lambda k: st[k, cv2.CC_STAT_AREA] if st[k, cv2.CC_STAT_TOP] > 60 else 0)
scr[lab == k] = 255
scr = cv2.morphologyEx(scr, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
cap = cv2.VideoCapture(f"{g.w}/mg/tv/src/baron_2875.mp4")
bfps = cap.get(cv2.CAP_PROP_FPS)


def bframe(t):
    cap.set(cv2.CAP_PROP_POS_MSEC, (t - 2875.0) * 1000)
    ok, im = cap.read()
    return im if ok else None


sift = cv2.SIFT_create(3000)


def feats(x):
    return sift.detectAndCompute(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), None)


def poly(x):
    x = x.reshape(-1, 3).astype(np.float64) / 255
    b, gg, r = x[:, 0], x[:, 1], x[:, 2]
    return np.stack([np.ones_like(b), b, gg, r, b * b, gg * gg, r * r, b * gg, gg * r, r * b], 1)


def fitc(src, dst, m):
    i = np.flatnonzero(m.ravel())
    if len(i) < 500:
        return None
    i = np.random.default_rng(0).choice(i, min(len(i), 30000), replace=False)
    X, Y = poly(src.reshape(-1, 3)[i]), dst.reshape(-1, 3)[i].astype(np.float64) / 255
    c = np.linalg.lstsq(X, Y, rcond=None)[0]
    return c


def applyc(img, c):
    return np.clip(poly(img) @ c * 255, 0, 255).reshape(img.shape).astype(np.uint8)


allp = f"{g.w}/cuts/_all.json"
allr = json.load(open(allp))
for i in (29, 33, 37, 38, 42):
    f0, f1 = int(round(E[i]["t0"] * FPS)), int(round(E[i]["t1"] * FPS))
    frames = [f for f in range(f0, f1) if f in TR]
    mid = frames[len(frames) // 2]
    ref_mid = cv2.imread(f"{g.w}/txt/f/{mid + 1:05d}.jpg")
    M = lambda f: np.vstack([np.array(TR[f]["M"]), [0, 0, 1]])
    # 中の動画：真ん中のコマで 対談→手本の画面 の相似
    bm = bframe(mid / FPS + g.off)
    scr_mid = cv2.warpAffine(scr, (M(mid))[:2], (W, H)) > 0
    # 対談のコマを画面の箱にまず「覆う」大きさで置き、画面の中だけで ECC（顔の明るさの形）で詰める（10/25 SIFT は点が3〜9で外れた）
    ys, xs = np.nonzero(scr_mid)
    bx0, by0, bx1, by1 = xs.min(), ys.min(), xs.max(), ys.max()
    bh_, bw_ = bm.shape[:2]
    sc = max((bx1 - bx0) / bw_, (by1 - by0) / bh_)
    A = np.float32([[sc, 0, (bx0 + bx1) / 2 - bw_ * sc / 2], [0, sc, (by0 + by1) / 2 - bh_ * sc / 2]])
    # 目印（SIFT・画面の中の点だけ）で当てる。合った点が5未満なら「覆う」大きさのまま（ECC は 10/25 に5場面とも外れた）
    k1, d1 = feats(bm); k2, d2 = feats(ref_mid)
    mm = [x for x, y in cv2.BFMatcher().knnMatch(d1, d2, k=2) if x.distance < 0.75 * y.distance]
    mm = [x for x in mm if scr_mid[int(min(H - 1, k2[x.trainIdx].pt[1])), int(min(W - 1, k2[x.trainIdx].pt[0]))]]
    cc = 0
    if len(mm) >= 6:
        A2, inl = cv2.estimateAffinePartial2D(np.float32([k1[x.queryIdx].pt for x in mm]), np.float32([k2[x.trainIdx].pt for x in mm]),
                                              method=cv2.RANSAC, ransacReprojThreshold=3)
        cc = int(inl.sum()) if inl is not None else 0
        if A2 is not None and cc >= 5:
            A = A2
    print(i, "中の当て 点", cc)
    Bm = np.vstack([A, [0, 0, 1]])  # 対談（真ん中のコマ）→ 手本の真ん中のコマ
    outs, refs, masks = [], [], []
    for f in frames:
        Mf = M(f)
        bg = cv2.warpAffine(plate, (Mf @ S0)[:2], (W, H), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
        sm = cv2.warpAffine(scr, Mf[:2], (W, H)) > 127
        b = bframe(f / FPS + g.off)
        inner = cv2.warpAffine(b, (Mf @ np.linalg.inv(M(mid)) @ Bm)[:2], (W, H), flags=cv2.INTER_LANCZOS4)
        outs.append((bg, inner, sm)); refs.append(cv2.imread(f"{g.w}/txt/f/{f + 1:05d}.jpg"))
    # 色：背景（画面の外・字幕の帯の外）と中を分けて合わせる
    band = np.zeros((H, W), bool); band[round(300 * H / 720):round(400 * H / 720)] = True  # 字幕の帯（r2 の行を高さの比で）
    cb = fitc(np.concatenate([o[0][::4, ::4] for o in outs]), np.concatenate([r[::4, ::4] for r in refs]),
              np.concatenate([(~o[2] & ~band)[::4, ::4] for o in outs]))
    ci = fitc(np.concatenate([o[1][::4, ::4] for o in outs]), np.concatenate([r[::4, ::4] for r in refs]),
              np.concatenate([(cv2.erode(o[2].astype(np.uint8), np.ones((9, 9), np.uint8)) > 0)[::4, ::4] & ~band[::4, ::4] for o in outs]))
    os.makedirs(f"{g.w}/cuts", exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", FPS_W,
                          "-i", "-", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", f"{g.w}/cuts/{i}.mp4"], stdin=subprocess.PIPE)
    ss = []
    for (bg, inner, sm), r in zip(outs, refs):
        a = applyc(bg, cb) if cb is not None else bg
        b = applyc(inner, ci) if ci is not None else inner
        soft = cv2.GaussianBlur(sm.astype(np.float32), (0, 0), 1.5)[..., None]
        fr = (a * (1 - soft) + b * soft).astype(np.uint8)
        p.stdin.write(fr.tobytes())
        ga, gb = cv2.cvtColor(cv2.resize(fr, (480, round(480 * H / W))), cv2.COLOR_BGR2GRAY), cv2.cvtColor(cv2.resize(r, (480, round(480 * H / W))), cv2.COLOR_BGR2GRAY)
        ss.append(cv2.matchTemplate(ga, gb, cv2.TM_CCOEFF_NORMED)[0, 0])
    p.stdin.close(); p.wait()
    allr[str(i)] = {"track": 1, "model": "tv_comp", "ssim_color": None, "ncc": round(float(np.mean(ss)), 3), "frames": len(frames)}
    json.dump(allr, open(allp, "w"), indent=1)
    print(i, "コマ", len(frames), "手本との相関（NCC）", round(float(np.mean(ss)), 3))
