"""手本のコマ→元の秒の対応表で、元の動画のコマをそのまま使ってカットを作る（10/28 r2 21・55・56：係 hunt20 が1コマずつ当てた表）。ぼかさん・止めん。
python3 map_fit.py <作業> <カット> <元.mp4> --map '{"168":3.147,...}' [--start 秒 --rate 1.0] [--frames 168-176] [--color mean|cur|none] [--write]
- --map が無い時は --start（手本の最初のコマ）と --rate（元の速さ÷手本の速さ）で秒を出す
- 位置：1コマ目は SIFT（元→手本・相似）→ 全コマ ECC（ホモグラフィ・手本の半分の大きさ＝r2 は 640）で手本へ詰める（前のコマの答えから始める）
- 色：Lab の平均と幅を手本へ（コマごと・3コマでならす）。--color none で触らん
- ぼかし：手本と同じ鋭さ（σ1 後の輪郭 90%点の比が 1 に近い σ）を 0〜2 から
- 表に無いコマ（切り替えのコマ）は今のカットのまま。前の物は .bak_map
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from retime import rd, looks, post_f
import retime
from geo import geo, half

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut"); ap.add_argument("src")
ap.add_argument("--map"); ap.add_argument("--start", type=float); ap.add_argument("--rate", type=float, default=1.0); ap.add_argument("--frames")
ap.add_argument("--color", default="mean"); ap.add_argument("--write", action="store_true")
a = ap.parse_args(); w = os.path.abspath(a.w); c = a.cut
retime.use_geo(w); GG = geo(w); FPS = GG["FPS"]; MW, MH = half(w)
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{c}:")][0]
s0, s1 = map(float, seg.split(":")[1].split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS)
R = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(f0, f1 - 1)); n = len(R); LK = looks(w, f0, n)
cp = f"{w}/cuts/{c}.mp4"; C = rd(cp)[:n].copy() if os.path.exists(cp) else np.zeros_like(R)
H, W = R.shape[1:3]
if a.map: M = {int(k): float(v) for k, v in json.loads(a.map).items()}
else:
    fa, fb = map(int, a.frames.split("-")) if a.frames else (f0, f1 - 1)
    M = {f: a.start + (f - fa) / FPS * a.rate for f in range(fa, fb + 1)}
cap = cv2.VideoCapture(os.path.join(w, a.src)); sfps = cap.get(5)
def src_at(t):
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(t * sfps)); ok, f = cap.read(); return f
band = np.ones((H, W), bool); band[int(H * .416):int(H * .583)] = False
g640 = lambda x: cv2.cvtColor(cv2.resize(x, (MW, MH), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
m640 = cv2.resize(band.astype(np.uint8), (MW, MH), interpolation=cv2.INTER_NEAREST)
SIFT = cv2.SIFT_create(3000); BF = cv2.BFMatcher()


def edge(img):
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.0)
    m = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1)); return float(np.percentile(m[band], 90))


def lab_match(x, r):
    xl = cv2.cvtColor(x, cv2.COLOR_BGR2LAB).astype(np.float32); rl = cv2.cvtColor(r, cv2.COLOR_BGR2LAB).astype(np.float32)
    for ch in range(3):
        a_, b_ = xl[..., ch][band], rl[..., ch][band]
        xl[..., ch] = (xl[..., ch] - a_.mean()) * (b_.std() / max(a_.std(), 1e-3)) + b_.mean()
    return cv2.cvtColor(np.clip(xl, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


Hm = None; out = C.copy(); rep = []
for f in sorted(M):
    j = f - f0
    if not (0 <= j < n): continue
    s = src_at(M[f]); sh, sw = s.shape[:2]
    # 元を半分の座標へ（縦横比のまま高さ MH＝r2 は 360）
    fs = MH / sh; sm = cv2.resize(s, (round(sw * fs), MH), interpolation=cv2.INTER_AREA)
    gr = g640(R[j]); gs = cv2.cvtColor(sm, cv2.COLOR_BGR2GRAY).astype(np.float32)
    if Hm is None:
        k1, d1 = SIFT.detectAndCompute(gr.astype(np.uint8), m640); k2, d2 = SIFT.detectAndCompute(gs.astype(np.uint8), None)
        mt = [m for m, n_ in BF.knnMatch(d1, d2, k=2) if m.distance < 0.75 * n_.distance]
        P1 = np.float32([k1[m.queryIdx].pt for m in mt]); P2 = np.float32([k2[m.trainIdx].pt for m in mt])
        A, inl = cv2.estimateAffinePartial2D(P1, P2, ransacReprojThreshold=3.0)
        Hm = np.vstack([A, [0, 0, 1]]).astype(np.float32); print("SIFT 目印", int(inl.sum()), flush=True)
    try:
        _, Hm = cv2.findTransformECC(cv2.GaussianBlur(gr, (0, 0), 1.0), cv2.GaussianBlur(gs, (0, 0), 1.0), Hm, cv2.MOTION_HOMOGRAPHY,
                                     (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), m640, 5)
        ok = True
    except cv2.error:
        ok = False
    # 原寸：手本(W,H) → 640 → Hm → 元640 → 元原寸
    Mf = np.diag([1 / fs, 1 / fs, 1]) @ Hm.astype(np.float64) @ np.diag([MW / W, MH / H, 1])
    al = cv2.warpPerspective(s, Mf, (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    if a.color == "mean": al = lab_match(al, R[j])
    elif a.color == "cur": al = lab_match(al, C[j])  # 今のカットの色（色合わせ済み）に寄せる
    out[j] = al; rep.append((f, M[f], ok))
# ぼかしは手本と同じ鋭さで
js = [f - f0 for f in M if 0 <= f - f0 < n]
re_ = np.mean([edge(R[j]) for j in js])
best = (9, 0)
for sg in (0, 0.4, 0.7, 1.0, 1.4, 2.0):
    e = np.mean([edge(cv2.GaussianBlur(out[j], (0, 0), sg) if sg else out[j]) for j in js]) / re_
    if abs(np.log(e)) < best[0]: best = (abs(np.log(e)), sg, e)
sg = best[1]
if sg:
    for j in js: out[j] = cv2.GaussianBlur(out[j], (0, 0), sg)
g = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (MW, MH), interpolation=cv2.INTER_AREA)
sb = np.mean([ssim(g(R[j]), g(post_f(C[j], LK[j]))) for j in js]); sa = np.mean([ssim(g(R[j]), g(post_f(out[j], LK[j]))) for j in js])
eb = np.mean([edge(post_f(C[j], LK[j])) for j in js]) / re_; ea = np.mean([edge(post_f(out[j], LK[j])) for j in js]) / re_
print(f"カット {c}：表のコマ {len(js)}・ECC {sum(r[2] for r in rep)}/{len(rep)}・ぼかし σ{sg}・点 {sb:.4f}→{sa:.4f}・鋭さ比 {eb:.2f}→{ea:.2f}")
dst = cp if a.write else f"{w}/tmp/map_{c}.mp4"
if a.write and os.path.exists(cp) and not os.path.exists(cp + ".bak_map"): shutil.copy(cp, cp + ".bak_map")
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", GG["FPS_FF"], "-i", "-",
                      "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", dst], stdin=subprocess.PIPE)
p.stdin.write(out.tobytes()); p.stdin.close(); p.wait(); print("書いた", dst)
