"""手本の放射状のズームぼかし（真ん中から外へ流れる）を、カットのコマに掛ける。強さはコマごとに手本に一番近い物を選ぶ。
python3 zoom_blur.py <作業> <カット番号> --frames a-b [--copy-from n] [--min 0.005]
- 強さ k＝0〜0.20（中心から k 倍まで拡大した絵を 12 枚重ねる）・中心＝画面の真ん中か、明るい所の重心
- --copy-from n：先に手本のコマ n の時のうちの絵（同じカットの中）で置き換えてから掛ける（崩れたコマの差し替え）
- 今より SSIM（640 白黒）が --min 以上上がった時だけ入れる。前の物は .bak_zb
"""
import glob
import argparse, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
W, H, FPS = 1280, 720, 29.97
def rd_range(p, a, b):
    # 手本の a〜b コマだけ読む（全部読むと 1280x720 で約6GB＝16GB の Mac が詰まる）
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"fps=2997/100,select='between(n\\,{a}\\,{b})',scale={W}:{H}", "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    fr = np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3)
    return {a + i: fr[i] for i in range(len(fr))}
def rd(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"fps=2997/100,scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).copy()
def zoom(im, k, cx, cy, n=12):
    acc = np.zeros(im.shape, np.float32)
    for i in range(n):
        s = 1 + k * i / (n - 1)
        M = np.float32([[s, 0, cx - s * cx], [0, s, cy - s * cy]])
        acc += cv2.warpAffine(im, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    return np.clip(acc / n, 0, 255).astype(np.uint8)
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut"); ap.add_argument("--frames", required=True); ap.add_argument("--copy-from", type=int); ap.add_argument("--min", type=float, default=0.005)
a = ap.parse_args(); w = os.path.abspath(a.w)
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{a.cut}:")][0]
c0 = round(float(seg.split(":")[1].split("-")[0]) * FPS)
cutp = f"{w}/cuts/{a.cut}.mp4"; C = rd(cutp)
g = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (640, 360))
f0, f1 = map(int, a.frames.split("-")); n_in = 0
R = rd_range(glob.glob(f"{w}/ref/*.mp4")[0], f0, f1)
for f in range(f0, f1 + 1):
    j = f - c0; r = R[f]; cur = C[j]
    src = C[a.copy_from - c0].copy() if a.copy_from is not None else cur
    gr = cv2.cvtColor(r, cv2.COLOR_BGR2GRAY).astype(np.float32); m = gr > np.percentile(gr, 90)
    ys, xs = np.nonzero(m); cands = [(W / 2, H / 2)] + ([(float(xs.mean()), float(ys.mean()))] if len(xs) else [])
    best = (ssim(g(r), g(cur)), cur, "今")
    for cx, cy in cands:
        for k in (0.0, 0.03, 0.06, 0.1, 0.15, 0.2):
            z = zoom(src, k, cx, cy) if k else src
            s = ssim(g(r), g(z))
            if s > best[0] + a.min: best = (s, z, f"k{k} 中心({cx:.0f},{cy:.0f})")
    print(f, "今", round(float(ssim(g(r), g(cur))), 3), "→", round(float(best[0]), 3), best[2])
    if best[2] != "今": C[j] = best[1]; n_in += 1
if n_in:
    if not os.path.exists(cutp + ".bak_zb"): shutil.copy(cutp, cutp + ".bak_zb")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", cutp], stdin=subprocess.PIPE)
    p.stdin.write(C.tobytes()); p.stdin.close(); p.wait(); print("書いた", n_in, "コマ")
