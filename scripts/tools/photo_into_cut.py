"""見つけた元の写真を、手本の決まったコマに SIFT（相似）で重ねて、写真の所だけカットに差し替える（モンタージュ・枠の中の写真・10/28 r2 71/72）。
python3 photo_into_cut.py <作業> <カット番号> <写真> --frames a-b [--min 0.003] [--write]
- 手本のコマ（字幕の帯を外す）と写真を SIFT → RANSAC の相似（拡大・回転・移動）。目印 12 未満のコマは飛ばす
- 写真の外枠の内側（4px 縮める）だけを差し替える。色は色ごとの1次（手本に合わせる）・ぼかし 0〜2 の良い方
- 比べる時も書く時も Remotion の look（コマごと）を通す。look 込みの SSIM が --min 以上上がったコマだけ入れる。前の物は .bak_pic
"""
import argparse, glob, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from retime import rd, looks, post_f, pre_f
W, H, FPS = 1280, 720, 29.97
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut"); ap.add_argument("img"); ap.add_argument("--frames", required=True)
ap.add_argument("--min", type=float, default=0.003); ap.add_argument("--write", action="store_true")
a = ap.parse_args(); w = os.path.abspath(a.w)
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{a.cut}:")][0]
c0 = round(float(seg.split(":")[1].split("-")[0]) * FPS)
cp = f"{w}/cuts/{a.cut}.mp4"; C = rd(cp).copy()
fa, fb = map(int, a.frames.split("-"))
R = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(fa, fb))
LK = looks(w, fa, len(R))
im = cv2.imread(a.img); s0 = 1200 / max(im.shape[:2]); im = cv2.resize(im, None, fx=s0, fy=s0, interpolation=cv2.INTER_AREA)
sf = cv2.SIFT_create(4000); bf = cv2.BFMatcher()
ki, di = sf.detectAndCompute(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), None)
mask = np.full((H, W), 255, np.uint8); mask[300:420] = 0
g = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (640, 360))
def tmpl_fit(r):
    """手本のコマ（字幕の帯を外した中ほど）を型に、写真を拡大率ごとに縮めて matchTemplate。一番合う所の相似変換を返す（一致 0.6 未満は None）"""
    gr = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY); gi = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    t = cv2.resize(gr[60:280, 240:1040], (400, 110)); best = (0.6, None)  # 手本の上の帯（字幕より上）を 1/2 で
    for sc in np.geomspace(0.15, 2.5, 40):  # 写真 1px が手本の sc px
        q = cv2.resize(gi, None, fx=sc / 2, fy=sc / 2, interpolation=cv2.INTER_AREA)
        if q.shape[0] < t.shape[0] or q.shape[1] < t.shape[1]: continue
        res = cv2.matchTemplate(q, t, cv2.TM_CCOEFF_NORMED); _, v, _, p = cv2.minMaxLoc(res)
        if v > best[0]: best = (v, np.float32([[sc, 0, 240 - p[0] * 2], [0, sc, 60 - p[1] * 2]]))
    return best[1]


def ecc_ref(r, A):
    """相似のまま ECC で詰める（1/2 の白黒・字幕の帯を外す）。うまくいかん時は元の A"""
    try:
        gr = cv2.resize(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY), (640, 360)).astype(np.float32)
        S = np.float32([[0.5, 0, 0], [0, 0.5, 0], [0, 0, 1]]); A3 = np.vstack([A, [0, 0, 1]]).astype(np.float32)
        wi = cv2.warpAffine(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (S @ A3)[:2], (640, 360)).astype(np.float32)
        mk = np.full((360, 640), 255, np.uint8); mk[150:210] = 0
        _, M = cv2.findTransformECC(gr, wi, np.eye(2, 3, dtype=np.float32), cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 80, 1e-5), mk, 5)
        Mi = cv2.invertAffineTransform(M); M3 = np.vstack([Mi, [0, 0, 1]]).astype(np.float32)
        return (np.linalg.inv(S) @ M3 @ S @ A3)[:2]
    except cv2.error:
        return A


n_in = 0
for f in range(fa, fb + 1):
    j = f - c0; r = R[f - fa]; lk = LK[f - fa]
    if j < 0 or j >= len(C): continue
    kr, dr = sf.detectAndCompute(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY), mask)
    if dr is None: print(f, "目印なし"); continue
    mm = [x for x, y in (q for q in bf.knnMatch(di, dr, k=2) if len(q) == 2) if x.distance < 0.75 * y.distance]
    A = None
    if len(mm) >= 12:
        A, inl = cv2.estimateAffinePartial2D(np.float32([ki[x.queryIdx].pt for x in mm]), np.float32([kr[x.trainIdx].pt for x in mm]), method=cv2.RANSAC, ransacReprojThreshold=3.0)
        if A is not None and inl.sum() < 12: A = None
    if A is None:  # 目印が足りん（大きく切り抜き・ぼけ）＝手本の枠を型にして写真の中を拡大率ごとに総当たり（10/28 r2 72）
        A = tmpl_fit(r); inl = np.zeros(1)
        if A is None: print(f, "重ならん"); continue
    A = ecc_ref(r, A)
    wp = cv2.warpAffine(im, A, (W, H), flags=cv2.INTER_CUBIC)
    m = cv2.erode(cv2.warpAffine(np.full(im.shape[:2], 255, np.uint8), A, (W, H), flags=cv2.INTER_NEAREST), np.ones((9, 9), np.uint8)) > 0
    sel = m & (mask > 0)
    fit = wp.astype(np.float32)
    if sel.sum() < 2000: print(f, "重なりが小さい"); continue
    for c in range(3):  # 平均と散らばりをそろえる（polyfit は中身がずれると薄める・10/28）
        x, y = wp[..., c][sel].astype(np.float32), r[..., c][sel].astype(np.float32)
        k = float(np.clip(y.std() / max(x.std(), 1e-3), 0.6, 1.8)); fit[..., c] = (wp[..., c] - x.mean()) * k + y.mean()
    cur = post_f(C[j], lk); best = None
    for bl in (0, 0.7, 1.2, 2):
        fb_ = np.clip(cv2.GaussianBlur(fit, (0, 0), bl) if bl else fit, 0, 255).astype(np.uint8)
        new = cur.copy(); new[m] = fb_[m]
        sc = ssim(g(r), g(new))
        if best is None or sc > best[0]: best = (sc, new)
    s_now = ssim(g(r), g(cur)); ok = best[0] > s_now + a.min
    print(f, "目印", int(inl.sum()), "今", round(float(s_now), 3), "写真", round(float(best[0]), 3), "入れた" if ok else "そのまま", flush=True)
    if ok:
        C[j] = pre_f(best[1], lk) if lk[1].any() or (lk[0] != 1).any() else best[1]; n_in += 1
if n_in and a.write:
    if not os.path.exists(cp + ".bak_pic"): shutil.copy(cp, cp + ".bak_pic")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", cp], stdin=subprocess.PIPE)
    p.stdin.write(C.tobytes()); p.stdin.close(); p.wait(); print("書いた", cp, n_in, "コマ")
