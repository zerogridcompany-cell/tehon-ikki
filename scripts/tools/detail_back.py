"""ぼかしすぎたカットに、くっきりの元の動画から「細かい所」だけを位置を合わせて足し戻す（10/28 r2：fit_cut が SSIM 最大でぼかしを選び 34 カットが σ3.0。138 は元 2831→カット 9）。
python3 detail_back.py <作業> <カット> [--src src/hi/<カット>.mp4] [--start <元の秒>] [--write]
- 今のカット（色・大きさ・時刻の直しが全部入った物）は崩さん：出来 = 今のコマ + λ×(元を合わせた絵 − そのぼかし)
- 元のコマ選び：今のコマの番号から見込んだ秒の ±1.2 秒を、元を同じだけぼかして 160x90 で相関（retime で速さが変わっても拾う）
- 位置：今のコマ（ぼけ）に、ぼかした元を ECC（アフィン）で合わせる → 同じ変換を鋭い元にかける
- λ：手本の鋭さ（σ1 でぼかした後の輪郭の強さ 90%点・字幕の帯を外す）に合う値（0〜1.6）。見た目の点（look 込みの SSIM）が 0.01 より下がるコマは λ を半分ずつ下げる
- 前の物は .bak_detail
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from retime import rd, looks, post_f
import retime
from geo import geo, half

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut"); ap.add_argument("--src"); ap.add_argument("--start", type=float)
ap.add_argument("--hf", type=float, default=2.0, help="細かい所を取るぼかしの σ"); ap.add_argument("--write", action="store_true")
a = ap.parse_args(); w = os.path.abspath(a.w); c = a.cut
retime.use_geo(w); GG = geo(w); FPS = GG["FPS"]; MW, MH = half(w)
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{c}:")][0]
s0, s1 = map(float, seg.split(":")[1].split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS)
R = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(f0, f1 - 1)); n = len(R); LK = looks(w, f0, n)
cp = f"{w}/cuts/{c}.mp4"; C = rd(cp)[:n]
src = a.src or f"{w}/src/hi/{c}.mp4"
meta = {}
jp = f"{w}/src/hi/{c}.json"
if os.path.exists(jp): meta = json.load(open(jp))
st = a.start if a.start is not None else float(meta.get("start", 0.0))
cap = cv2.VideoCapture(src); sfps = cap.get(5) or 30.0; S = []
while True:
    ok, f = cap.read()
    if not ok: break
    S.append(f)
S = np.stack(S); print("元", src, S.shape, "fps", round(sfps, 3), "start", st)
H, W = C.shape[1:3]
band = np.ones((H, W), bool); band[int(H * .416):int(H * .583)] = False; band[:16] = band[-16:] = False; band[:, :16] = band[:, -16:] = False


def edge(img):
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.0)
    m = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    return float(np.percentile(m[band], 90))


tiny = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (GG["SW"] // 2, GG["SH"] // 2), interpolation=cv2.INTER_AREA).astype(np.float32)
# 元の全コマを今のカットの大きさに（まず縦横比を保って全体を入れる＝ECC が後で合わせる）
sh, sw = S.shape[1:3]
out = C.copy(); rep = []; Wprev = None
SIFT = cv2.SIFT_create(2000); BF = cv2.BFMatcher(); fs = MH / sh
small = lambda x: cv2.resize(x, (round(sw * fs), MH), interpolation=cv2.INTER_AREA)
g640 = lambda x: cv2.cvtColor(cv2.resize(x, (MW, MH), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)


def sift_aff(gc, gs):
    k1_, d1 = SIFT.detectAndCompute(gc, None); k2_, d2 = SIFT.detectAndCompute(gs, None)
    if d1 is None or d2 is None or len(k1_) < 8 or len(k2_) < 8: return None, 0
    mt = [m for m, n_ in BF.knnMatch(d1, d2, k=2) if m.distance < 0.75 * n_.distance]
    if len(mt) < 6: return None, 0
    P1 = np.float32([k1_[m.queryIdx].pt for m in mt]); P2 = np.float32([k2_[m.trainIdx].pt for m in mt])
    A1, inl = cv2.estimateAffinePartial2D(P1, P2, ransacReprojThreshold=3.0)
    return (A1.astype(np.float32) if A1 is not None else None), int(inl.sum()) if inl is not None else 0


# 真ん中のコマで、元のどのコマか・どこに写っとるかを特徴点で決める（黒い縁・寄せがあっても拾う）
jm = n // 2; gcm = g640(C[jm]); tm = st + jm / FPS
cands = range(max(0, int((tm - 1.5) * sfps)), min(len(S), int((tm + 1.5) * sfps) + 1), 2)
km, M0, best_in = None, None, 0
for k in cands:
    A1, ni = sift_aff(gcm, cv2.cvtColor(small(S[k]), cv2.COLOR_BGR2GRAY))
    if ni > best_in: km, M0, best_in = k, A1, ni
print("真ん中のコマ", jm, "→ 元", km, "特徴点", best_in, flush=True)
if M0 is None: sys.exit("元が当たらん")
rate = sfps / FPS


def ncc_al(gc, x, Wm):
    al = cv2.warpAffine(cv2.cvtColor(small(x), cv2.COLOR_BGR2GRAY), Wm, (MW, MH), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderValue=0).astype(np.float32)
    a_ = cv2.GaussianBlur(al, (0, 0), 2.5); b_ = cv2.GaussianBlur(gc.astype(np.float32), (0, 0), 2.5)
    a_ = a_ - a_.mean(); b_ = b_ - b_.mean(); return float((a_ * b_).sum() / (np.sqrt((a_ * a_).sum() * (b_ * b_).sum()) + 1e-6))


for j in range(n):
    cur = C[j]; gc = g640(cur); Wuse = Wprev if Wprev is not None else M0
    ke = km + (j - jm) * rate
    best = (-2, int(round(ke)))
    for k in range(max(0, int(ke - 0.6 * sfps)), min(len(S), int(ke + 0.6 * sfps) + 1)):
        sc = ncc_al(gc, S[k], Wuse)
        if sc > best[0]: best = (sc, k)
    k = best[1]
    # 位置合わせ：元を縦横比のまま 360 の高さに → ぼかして SIFT で大まかに → ECC で詰める（W は 今640→元640 の向き）
    sharp_full = S[k]
    sm = small(sharp_full)
    g_cur = gc
    g_src = cv2.GaussianBlur(cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY), (0, 0), 1.5)
    Wm = Wuse.copy()
    try:
        _, Wm = cv2.findTransformECC(cv2.GaussianBlur(g_cur, (0, 0), 1.0).astype(np.float32), g_src.astype(np.float32), Wm, cv2.MOTION_AFFINE,
                                     (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
        okecc = True; Wprev = Wm
    except cv2.error:
        okecc = False
    Wf = np.vstack([Wm, [0, 0, 1]]).astype(np.float64)
    M = np.diag([1 / fs, 1 / fs, 1]) @ Wf @ np.diag([MW / W, MH / H, 1])  # 今(原寸)→元(原寸)
    al = cv2.warpAffine(sharp_full, M[:2], (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
    hf = al - cv2.GaussianBlur(al, (0, 0), a.hf)
    r_e = edge(R[j]); base = ssim(cv2.cvtColor(R[j], cv2.COLOR_BGR2GRAY), cv2.cvtColor(post_f(cur, LK[j]), cv2.COLOR_BGR2GRAY))
    lam_best = (abs(edge(post_f(cur, LK[j])) / r_e - 1), 0.0, base)
    for lam in (0.25, 0.5, 0.75, 1.0, 1.3, 1.6):
        y = np.clip(cur.astype(np.float32) + lam * hf, 0, 255).astype(np.uint8)
        yp = post_f(y, LK[j]); d = abs(edge(yp) / r_e - 1)
        s = ssim(cv2.cvtColor(R[j], cv2.COLOR_BGR2GRAY), cv2.cvtColor(yp, cv2.COLOR_BGR2GRAY))
        if s < base - 0.01: continue
        if d < lam_best[0]: lam_best = (d, lam, s)
    lam = lam_best[1]
    out[j] = np.clip(cur.astype(np.float32) + lam * hf, 0, 255).astype(np.uint8)
    e_before = edge(post_f(cur, LK[j])) / r_e; e_after = edge(post_f(out[j], LK[j])) / r_e
    rep.append({"j": j, "src_k": k, "corr": round(best[0], 3), "ecc": okecc, "lam": lam, "edge_before": round(e_before, 2), "edge_after": round(e_after, 2), "ssim_before": round(base, 4), "ssim_after": round(lam_best[2], 4)})
    print(j, "元", k, "相関", round(best[0], 3), "ecc", okecc, "λ", lam, "鋭さ比", round(e_before, 2), "→", round(e_after, 2), "点", round(base, 3), "→", round(lam_best[2], 3), flush=True)
os.makedirs(f"{w}/shirabe/detail", exist_ok=True)
json.dump(rep, open(f"{w}/shirabe/detail/{c}.json", "w"), ensure_ascii=False, indent=1)
dst = cp if a.write else f"{w}/tmp/detail_{c}.mp4"
if a.write and not os.path.exists(cp + ".bak_detail"): shutil.copy(cp, cp + ".bak_detail")
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", GG["FPS_FF"], "-i", "-",
                      "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", dst], stdin=subprocess.PIPE)
p.stdin.write(out.tobytes()); p.stdin.close(); p.wait(); print("書いた", dst)
