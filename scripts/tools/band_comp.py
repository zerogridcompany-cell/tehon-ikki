"""背景の動画に「縦の帯」で別の動画を重ねる切り替え（10/28 r2 55：Figure BotQ の較正部屋の壁＋帯の中で Figure 03 の後ろ姿がだんだんくっきり）を、元の動画2本から作る。
python3 band_comp.py <作業> <カット> --bg <元.mp4> --bg_t <手本の最初のコマの元の秒> --fg <元.mp4> --fg_t <同> [--fg_rate 1] [--write]
- 位置：背景・帯の中身とも、手本のコマに SIFT→ECC（帯の外／帯の中だけの印で）
- コマごとに 帯の左右 x0・x1・ふち・帯の中のぼかし σ・明るさ（掛け・足し）を手本へ総当たり＋細かく（640 白黒の差の二乗）
- 色は Lab の平均と幅を手本へ。手本の画素は使わん（位置と数だけ）
"""
import argparse, glob, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from retime import rd, looks, post_f
import retime
from geo import geo, half
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut")
ap.add_argument("--bg"); ap.add_argument("--bg_t", type=float); ap.add_argument("--fg"); ap.add_argument("--fg_t", type=float); ap.add_argument("--fg_rate", type=float, default=1.0)
ap.add_argument("--fg_align_frame", type=int, help="帯の中身を合わせる手本のコマ（はっきり写っとるコマ・隣のカットでも可）"); ap.add_argument("--fg_align_t", type=float)
ap.add_argument("--write", action="store_true")
a = ap.parse_args(); w = os.path.abspath(a.w); c = a.cut
retime.use_geo(w); G = geo(w); FPS, SW, SH = G["FPS"], G["SW"], G["SH"]; MW, MH = half(w)
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{c}:")][0]
s0, s1 = map(float, seg.split(":")[1].split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS)
R = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(f0, f1 - 1)); n = len(R); LK = looks(w, f0, n); H, W = R.shape[1:3]
SIFT = cv2.SIFT_create(4000); BF = cv2.BFMatcher()


def grab(p, t):
    cap = cv2.VideoCapture(os.path.join(w, p)); cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, round(t * cap.get(5)))); ok, f = cap.read(); return f


def align(src, ref, mask):
    """src を ref の座標へ（ホモグラフィ）。mask＝ref で印を取る所"""
    gs = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY); gr = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY)
    k1, d1 = SIFT.detectAndCompute(gr, mask.astype(np.uint8) * 255); k2, d2 = SIFT.detectAndCompute(gs, None)
    mt = [m for m, n_ in BF.knnMatch(d1, d2, k=2) if m.distance < 0.75 * n_.distance]
    P1 = np.float32([k1[m.queryIdx].pt for m in mt]); P2 = np.float32([k2[m.trainIdx].pt for m in mt])
    A, inl = cv2.estimateAffinePartial2D(P1, P2, ransacReprojThreshold=3.0)
    Hm = np.vstack([A, [0, 0, 1]]).astype(np.float32)
    try:
        _, Hm = cv2.findTransformECC(cv2.GaussianBlur(gr.astype(np.float32), (0, 0), 1), cv2.GaussianBlur(gs.astype(np.float32), (0, 0), 1), Hm, cv2.MOTION_HOMOGRAPHY,
                                     (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-7), mask.astype(np.uint8), 5)
    except cv2.error: pass
    return Hm, int(inl.sum())


def lab_to(x, r, m):
    xl = cv2.cvtColor(x, cv2.COLOR_BGR2LAB).astype(np.float32); rl = cv2.cvtColor(r, cv2.COLOR_BGR2LAB).astype(np.float32)
    for ch in range(3):
        a_, b_ = xl[..., ch][m], rl[..., ch][m]; xl[..., ch] = (xl[..., ch] - a_.mean()) * (b_.std() / max(a_.std(), 1e-3)) + b_.mean()
    return cv2.cvtColor(np.clip(xl, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


cap_band = np.ones((H, W), bool); cap_band[int(H * .416):int(H * .583)] = False
outside = cap_band.copy(); outside[:, int(W * .33):int(W * .67)] = False
inside = cap_band.copy(); inside[:, :int(W * .40)] = False; inside[:, int(W * .60):] = False
# 背景：最後のコマ（帯が細い）で合わせる・帯の中身：一番くっきりのコマで合わせる
bg0 = grab(a.bg, a.bg_t); Hb, ib = align(bg0, R[0], outside)
if a.fg_align_frame is not None:
    RA = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(a.fg_align_frame, a.fg_align_frame))[0]
    Hf, ifg = align(grab(a.fg, a.fg_align_t), RA, cap_band)
else:
    fgL = grab(a.fg, a.fg_t + (n - 1) / FPS * a.fg_rate); Hf, ifg = align(fgL, R[n - 1], inside)
print("合わせ 背景", ib, "帯の中", ifg, flush=True)
xs = np.arange(W, dtype=np.float32)[None, :]
g = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (SW, SH), interpolation=cv2.INTER_AREA).astype(np.float32)
out = np.zeros_like(R); rows = []
for j in range(n):
    B = cv2.warpPerspective(grab(a.bg, a.bg_t + j / FPS), Hb, (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    F = cv2.warpPerspective(grab(a.fg, a.fg_t + j / FPS * a.fg_rate), Hf, (W, H), flags=cv2.INTER_LANCZOS4 | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    B = lab_to(B, R[j], outside)
    gr = g(R[j]); best = (1e18,)
    Bs = g(B); Fs0 = cv2.resize(F, (SW, SH), interpolation=cv2.INTER_AREA); xs_s = np.arange(SW, dtype=np.float32)[None, :]
    for sg in (0, 1, 2, 4, 8):
        Fb = cv2.GaussianBlur(Fs0, (0, 0), sg) if sg else Fs0
        Fg = cv2.cvtColor(Fb, cv2.COLOR_BGR2GRAY).astype(np.float32)
        for x0 in range(96, 170, 3):
            for x1 in range(160, 232, 3):
                if x1 <= x0 + 6: continue
                for fe in (1, 3, 6, 12):
                    m = np.repeat(np.clip(np.minimum(xs_s - x0, x1 - xs_s) / fe + .5, 0, 1), SH, 0)
                    inn = m > .9
                    if inn.sum() < 200: continue
                    gain = gr[inn].std() / max(Fg[inn].std(), 1e-3); off = gr[inn].mean() - Fg[inn].mean() * gain
                    y = Bs * (1 - m) + (Fg * gain + off) * m
                    e = float(((y - gr) ** 2).mean())
                    if e < best[0]: best = (e, x0 * W // SW, x1 * W // SW, fe * W // SW, sg * W // SW)
    _, x0, x1, fe, sg = best
    m = np.repeat(np.clip(np.minimum(xs - x0, x1 - xs) / fe + .5, 0, 1), H, 0)
    Fb = cv2.GaussianBlur(F, (0, 0), sg) if sg else F
    Fb = lab_to(Fb, R[j], (m > .9) & cap_band)
    y = (B * (1 - m[..., None]) + Fb * m[..., None]).astype(np.uint8); best = best + (y,)
    out[j] = best[5]; rows.append(best[1:5]); print(j, "帯", best[1], best[2], "ふち", best[3], "σ", best[4], flush=True)
gg = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (MW, MH), interpolation=cv2.INTER_AREA)
print("点", round(float(np.mean([ssim(gg(R[j]), gg(post_f(out[j], LK[j]))) for j in range(n)])), 4))
cp = f"{w}/cuts/{c}.mp4"; dst = cp if a.write else f"{w}/tmp/band_{c}.mp4"
if a.write and os.path.exists(cp) and not os.path.exists(cp + ".bak_band"): shutil.copy(cp, cp + ".bak_band")
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", G["FPS_FF"], "-i", "-", "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", dst], stdin=subprocess.PIPE)
p.stdin.write(out.tobytes()); p.stdin.close(); p.wait(); print("書いた", dst)
