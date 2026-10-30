"""一枚の写真を手本どおり「一定の速さで寄せる（Ken Burns）」カットにする（10/28 r2 138：手本は写真を 2124→2156 で 1.000→1.022 に等速で寄せるだけ・顔は動かん。うちは止まってから跳ぶ＋σ3 のぼけ）。
python3 photo_zoom.py <作業> <カット> <写真> [--write]
- 全コマで 手本→写真 を SIFT→ECC（1/4）→流れの中央値で詰め、ホモグラフィの8つの数を時間で直線にならす（＝等速）。写真の外は今のカットの絵で埋める
- 色は Lab の平均と幅を手本へ（カット全体で1つ）。ぼかしは手本と同じ鋭さになる σ（0〜2）
"""
import argparse, glob, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from retime import rd, looks, post_f
FPS = 29.97
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut"); ap.add_argument("photo"); ap.add_argument("--write", action="store_true"); ap.add_argument("--nosmooth", action="store_true", help="等速にならさず1コマずつの合わせのまま")
a = ap.parse_args(); w = os.path.abspath(a.w); c = a.cut
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{c}:")][0]
s0, s1 = map(float, seg.split(":")[1].split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS)
R = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(f0, f1 - 1)); n = len(R); LK = looks(w, f0, n); H, W = R.shape[1:3]
P = cv2.imread(os.path.join(w, a.photo))
band = np.ones((H, W), np.uint8); band[int(H * .416):int(H * .583)] = 0
SIFT = cv2.SIFT_create(4000); BF = cv2.BFMatcher()


def fit(r):
    """手本→写真のホモグラフィ：SIFT → ECC（1/4 の大きさ）→ 流れの中央値で平行移動を2回詰める"""
    gr = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY); gp = cv2.cvtColor(P, cv2.COLOR_BGR2GRAY)
    k1, d1 = SIFT.detectAndCompute(gr, band * 255); k2, d2 = SIFT.detectAndCompute(gp, None)
    mt = [m for m, n_ in BF.knnMatch(d1, d2, k=2) if m.distance < 0.8 * n_.distance]
    Hm, inl = cv2.findHomography(np.float32([k1[m.queryIdx].pt for m in mt]), np.float32([k2[m.trainIdx].pt for m in mt]), cv2.RANSAC, 3.0)
    Hm = Hm.astype(np.float32); sc = 0.25
    try:
        a_ = cv2.GaussianBlur(cv2.resize(gr, None, fx=sc, fy=sc).astype(np.float32), (0, 0), 2); b_ = cv2.GaussianBlur(cv2.resize(gp, None, fx=sc, fy=sc).astype(np.float32), (0, 0), 2)
        Hs = np.diag([sc, sc, 1]).astype(np.float32) @ Hm @ np.diag([1 / sc, 1 / sc, 1]).astype(np.float32)
        _, Hs = cv2.findTransformECC(a_, b_, Hs, cv2.MOTION_HOMOGRAPHY, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), cv2.resize(band, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST), 5)
        Hm = np.diag([1 / sc, 1 / sc, 1]).astype(np.float32) @ Hs @ np.diag([sc, sc, 1]).astype(np.float32)
    except cv2.error: pass
    for _ in range(2):
        x = cv2.cvtColor(cv2.warpPerspective(P, Hm, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP), cv2.COLOR_BGR2GRAY)
        fl = DIS.calc(gr, x, None); dx = float(np.median(fl[..., 0][band > 0])); dy = float(np.median(fl[..., 1][band > 0]))
        Hm = (Hm @ np.float32([[1, 0, dx], [0, 1, dy], [0, 0, 1]])).astype(np.float32)
    return Hm / Hm[2, 2], int(inl.sum())


js = [1, n // 2, n - 2]
DIS = cv2.DISOpticalFlow_create(2)
fits = [fit(R[j]) for j in range(n)]
print("目印", [f[1] for f in fits][:6], "…")
Hs_all = np.stack([f[0].ravel()[:8] for f in fits]); t = np.arange(n, dtype=float)
coef = [np.polyfit(t, Hs_all[:, i], 1) for i in range(8)]  # 等速＝8つの数を時間で直線に
out = []; VM = []
for j in range(n):
    A = fits[j][0].astype(np.float32) if a.nosmooth else np.append([np.polyval(cf, j) for cf in coef], 1.0).reshape(3, 3).astype(np.float32)
    out.append(cv2.warpPerspective(P, A, (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT))
    vm = cv2.warpPerspective(np.full(P.shape[:2], 255, np.uint8), A, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderValue=0)
    VM.append(cv2.GaussianBlur(cv2.erode(vm, np.ones((9, 9), np.uint8)), (0, 0), 6).astype(np.float32) / 255)
out = np.stack(out)
CUR = rd(f"{w}/cuts/{c}.mp4")[:n]  # 写真が足りん所（写真の外）は今のカットの絵で埋める
# 色（カット全体で1つ）
m = band > 0
mv = m & (VM[n // 2] > .99)
xl = cv2.cvtColor(out[n // 2], cv2.COLOR_BGR2LAB).astype(np.float32); rl = cv2.cvtColor(R[n // 2], cv2.COLOR_BGR2LAB).astype(np.float32)
k_ = [(rl[..., ch][mv].std() / max(xl[..., ch][mv].std(), 1e-3), rl[..., ch][mv].mean(), xl[..., ch][mv].mean()) for ch in range(3)]
for j in range(n):
    x = cv2.cvtColor(out[j], cv2.COLOR_BGR2LAB).astype(np.float32)
    for ch in range(3): x[..., ch] = (x[..., ch] - k_[ch][2]) * k_[ch][0] + k_[ch][1]
    x = cv2.cvtColor(np.clip(x, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR).astype(np.float32)
    out[j] = (x * VM[j][..., None] + CUR[j].astype(np.float32) * (1 - VM[j][..., None])).astype(np.uint8)
def edge(img):
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.0)
    e = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)); return float(np.percentile(e[m], 90))
re_ = np.mean([edge(R[j]) for j in js]); best = (9, 0)
for sg in (0, 0.4, 0.7, 1.0, 1.4, 2.0):
    e = np.mean([edge(post_f(cv2.GaussianBlur(out[j], (0, 0), sg) if sg else out[j], LK[j])) for j in js]) / re_
    if abs(np.log(e)) < best[0]: best = (abs(np.log(e)), sg, e)
if best[1]: out = np.stack([cv2.GaussianBlur(x, (0, 0), best[1]) for x in out])
gg = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (640, 360), interpolation=cv2.INTER_AREA)
cp = f"{w}/cuts/{c}.mp4"; C = rd(cp)[:n]
sb = np.mean([ssim(gg(R[j]), gg(post_f(C[j], LK[j]))) for j in range(n)]); sa = np.mean([ssim(gg(R[j]), gg(post_f(out[j], LK[j]))) for j in range(n)])
eb = np.mean([edge(post_f(C[j], LK[j])) for j in js]) / re_
print(f"σ{best[1]}・鋭さ比 {eb:.2f}→{best[2]:.2f}・点 {sb:.4f}→{sa:.4f}")
dst = cp if a.write else f"{w}/tmp/zoom_{c}.mp4"
if a.write and not os.path.exists(cp + ".bak_zoom"): shutil.copy(cp, cp + ".bak_zoom")
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100", "-i", "-", "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", dst], stdin=subprocess.PIPE)
p.stdin.write(out.tobytes()); p.stdin.close(); p.wait(); print("書いた", dst)
