"""見つけた原本の写真をカットに入れる（10/28 r2）：背景で重ねる → 色をそろえる → 手本の1コマずつへ流れ（フロー）で形を寄せる → look 込みで今より良いコマだけ入れる。
手本の作り手は写真を AI で動かし（顔の向き・笑い）、外側を AI で描き足しとる（10 の左右・5 の右・3 の左右）。原本を置くだけやと顔が二重になる＝動きは手本から写す。
python3 genpon.py <作業> <カット> <写真> --frames a-b [--flow 1] [--write]
- 重ね：SIFT（相似）→ 足りん時は型合わせ → 射影の ECC で詰める。写真の外（描き足しの所）は今のカットのまま
- 流れ：手本と置いた絵（どちらも 1/2・ぼかした白黒）で DIS → 流れを強くならす（σ 12px）→ 置いた絵を曲げる。--flow 0 で流れ無し
- 入れる：look 込みの SSIM が今より上がる、または 0.01 以内の下がりでエッジの比が 1 に近づくコマ。前の物は .bak_gp
"""
import argparse, glob, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from retime import rd, looks, post_f, pre_f
W, H, FPS = 1280, 720, 29.97
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut"); ap.add_argument("img"); ap.add_argument("--frames", required=True)
ap.add_argument("--flow", type=int, default=1); ap.add_argument("--loose", type=float, default=0.01); ap.add_argument("--write", action="store_true"); ap.add_argument("--sheet", default="")
a = ap.parse_args(); w = os.path.abspath(a.w)
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{a.cut}:")][0]
c0 = round(float(seg.split(":")[1].split("-")[0]) * FPS)
cp = f"{w}/cuts/{a.cut}.mp4"; C = rd(cp).copy()
fa, fb = map(int, a.frames.split("-"))
R = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(fa, fb)); LK = looks(w, fa, len(R))
im = cv2.imread(a.img); s0 = 1600 / max(im.shape[:2]); im = cv2.resize(im, None, fx=min(1, s0), fy=min(1, s0), interpolation=cv2.INTER_AREA)
gi = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
mask = np.full((H, W), 255, np.uint8); mask[300:420] = 0
g6 = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (640, 360), interpolation=cv2.INTER_AREA)
sf = cv2.SIFT_create(5000); ki, di = sf.detectAndCompute(gi, None)
dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)


def edge(g):
    g = g.astype(np.float32); return float(np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)).mean())


def place(r):
    """写真→手本の 3x3（射影）。SIFT → 型合わせ → ECC"""
    kr, dr = sf.detectAndCompute(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY), mask); Hm = None
    if dr is not None:
        mm = [x for x, y in (q for q in cv2.BFMatcher().knnMatch(di, dr, k=2) if len(q) == 2) if x.distance < 0.8 * y.distance]
        if len(mm) >= 12:
            A, inl = cv2.estimateAffinePartial2D(np.float32([ki[x.queryIdx].pt for x in mm]), np.float32([kr[x.trainIdx].pt for x in mm]), method=cv2.RANSAC, ransacReprojThreshold=4.0)
            if A is not None and inl.sum() >= 10: Hm = np.vstack([A, [0, 0, 1]]).astype(np.float32)
    if Hm is None:
        gr = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY); t = cv2.resize(gr[40:290, 200:1080], (440, 125)); best = (0.5, None)
        for sc in np.geomspace(0.15, 3.0, 50):
            q = cv2.resize(gi, None, fx=sc / 2, fy=sc / 2, interpolation=cv2.INTER_AREA)
            if q.shape[0] < t.shape[0] or q.shape[1] < t.shape[1]: continue
            _, v, _, p = cv2.minMaxLoc(cv2.matchTemplate(q, t, cv2.TM_CCOEFF_NORMED))
            if v > best[0]: best = (v, np.float32([[sc, 0, 200 - p[0] * 2], [0, sc, 40 - p[1] * 2], [0, 0, 1]]))
        Hm = best[1]
        if Hm is None: return None
    S = np.float32([[0.5, 0, 0], [0, 0.5, 0], [0, 0, 1]])
    gr = cv2.GaussianBlur(g6(r).astype(np.float32), (0, 0), 1.5)
    wi = cv2.GaussianBlur(cv2.warpPerspective(gi, S @ Hm, (640, 360)).astype(np.float32), (0, 0), 1.5)
    mk = (cv2.warpPerspective(np.full(gi.shape, 255, np.uint8), S @ Hm, (640, 360)) > 0).astype(np.uint8) * 255; mk[150:210] = 0
    def sc(H_):  # 置いた絵の SSIM（写真の中だけ）
        x = cv2.warpPerspective(gi, S @ H_, (640, 360)); mm = cv2.warpPerspective(np.full(gi.shape, 255, np.uint8), S @ H_, (640, 360)) > 0
        if mm.sum() < 0.05 * 640 * 360: return -1
        y = g6(r).copy(); y[~mm] = 0; x[~mm] = 0; return ssim(y, x)
    best = (sc(Hm), Hm)
    for mode in (cv2.MOTION_AFFINE, cv2.MOTION_HOMOGRAPHY):  # 外れる事がある＝点が上がった時だけ使う
        try:
            M0 = np.eye(3, dtype=np.float32) if mode == cv2.MOTION_HOMOGRAPHY else np.eye(2, 3, dtype=np.float32)
            _, M = cv2.findTransformECC(gr, wi, M0, mode, (3, 150, 1e-6), mk, 5)
            M3 = M if mode == cv2.MOTION_HOMOGRAPHY else np.vstack([M, [0, 0, 1]]).astype(np.float32)
            H2 = np.linalg.inv(S) @ np.linalg.inv(M3) @ S @ Hm; s2 = sc(H2)
            if s2 > best[0]: best = (s2, H2)
        except (cv2.error, np.linalg.LinAlgError):
            pass
    return best[1]


def colmatch(x, r, m):
    y = x.astype(np.float32).copy()
    for c in range(3):
        xs, ys = x[..., c][m].astype(np.float32), r[..., c][m].astype(np.float32)
        k = float(np.clip(ys.std() / max(xs.std(), 1e-3), 0.6, 1.8)); y[..., c] = (y[..., c] - xs.mean()) * k + ys.mean()
    return np.clip(y, 0, 255).astype(np.uint8)


def flowto(x, r):
    """x を r の形へ寄せる（流れは 1/2 でならしてから 1280 へ）"""
    a = cv2.GaussianBlur(g6(r), (0, 0), 2); b = cv2.GaussianBlur(g6(x), (0, 0), 2)
    fl = dis.calc(a, b, None)  # r の各点が x のどこから来たか
    fl = cv2.GaussianBlur(fl, (0, 0), 12)
    fl = cv2.resize(fl, (W, H)) * 2
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    return cv2.remap(x, gx + fl[..., 0], gy + fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


SH = []
n_in = 0
for i, f in enumerate(range(fa, fb + 1)):
    j = f - c0
    if j < 0 or j >= len(C): continue
    r = R[i]; lk = LK[i]; Hm = place(r)
    if Hm is None: print(f, "重ならん"); continue
    wp = cv2.warpPerspective(im, Hm, (W, H), flags=cv2.INTER_CUBIC)
    m = cv2.erode(cv2.warpPerspective(np.full(im.shape[:2], 255, np.uint8), Hm, (W, H), flags=cv2.INTER_NEAREST), np.ones((7, 7), np.uint8)) > 0
    if m.sum() < 0.05 * W * H: print(f, "重なりが小さい"); continue
    cur = post_f(C[j], lk)
    new = cur.copy(); new[m] = colmatch(wp, r, m & (mask > 0))[m]
    if a.flow: new = flowto(new, r)
    gr = g6(r); sn = ssim(gr, g6(cur))
    cands = [(ssim(gr, g6(x)), x) for x in (cv2.GaussianBlur(new, (0, 0), b) if b else new for b in (0, 1, 1.5, 2, 3))]
    top = max(c[0] for c in cands); er0 = edge(gr)
    sc, new = min([c for c in cands if c[0] >= top - 0.01], key=lambda c: abs(np.log(max(edge(g6(c[1])) / er0, 1e-3))))  # くっきり優先（0.01 以内）
    er = edge(gr); en, ec = edge(g6(new)) / er, edge(g6(cur)) / er
    # --loose＝くっきりが手本に近づくなら、点の下がりをここまで許す（SSIM はずれた中身をぼかすほど上がる＝r2 8：今 0.77 は横が欠けてぼかし 4）
    ok = en > 0.05 and (sc > sn + 0.003 or (sc >= sn - a.loose and abs(np.log(en)) < abs(np.log(max(ec, 1e-3))) - 0.1))
    print(f"{f} 今 {sn:.3f}（エッジ比 {ec:.2f}）→ 原本 {sc:.3f}（{en:.2f}）{'入れる' if ok else ''}", flush=True)
    if a.sheet: SH.append(np.hstack([cv2.resize(x, (320, 180)) for x in (r, cur, new)]))
    if ok:
        C[j] = pre_f(new, lk) if (lk[0] != 1).any() or lk[1].any() else new; n_in += 1
if a.write and n_in:
    if not os.path.exists(cp + ".bak_gp"): shutil.copy(cp, cp + ".bak_gp")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", cp], stdin=subprocess.PIPE)
    p.stdin.write(C.tobytes()); p.stdin.close(); p.wait(); print("書いた", cp, n_in, "コマ")
if a.sheet and SH: cv2.imwrite(a.sheet, np.vstack(SH))
