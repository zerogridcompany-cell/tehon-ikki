"""今の書き出しから、カットごとに「ぼかし（σ）か くっきり（unsharp）」を足したら SSIM が上がるかを見込む（640 白黒・mane_check と同じ物差し）。
python3 blur_refit.py <作業> <書き出し.mp4> [--min 0.004] [--write]
--write で shot_look の blur（既存に足す）／sharp を書く。前は shot_look.json.bak_blur
"""
import glob
import argparse, json, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import frames, ssim
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("out"); ap.add_argument("--min", type=float, default=0.004); ap.add_argument("--write", action="store_true")
a = ap.parse_args(); w = os.path.abspath(a.w)
R = frames(glob.glob(f"{w}/ref/*.mp4")[0]); V = frames(os.path.join(w, a.out)); n = min(len(R), len(V))
segs = []
for l in open(f"{w}/eye/segs.txt"):
    if ":" in l:
        k, v = l.split(":"); s0, s1 = map(float, v.split("-")); segs.append((k.strip(), round(s0 * 29.97), min(n, round(s1 * 29.97))))
SL = json.load(open(f"{w}/proj/src/shot_look.json")); tot = 0; ch = []
for k, f0, f1 in segs:
    if f1 - f0 < 2: continue
    idx = range(f0, f1)
    base = np.mean([ssim(R[i], V[i]) for i in idx]); best = (base, None)
    for sg in (0.6, 1.0, 1.5, 2.2):
        s = np.mean([ssim(R[i], cv2.GaussianBlur(V[i], (0, 0), sg)) for i in idx])
        if s > best[0]: best = (s, ("blur", sg))
    for amt in (0.5, 1.0):
        def sh(x): b = cv2.GaussianBlur(x, (0, 0), 1.0).astype(np.float32); return np.clip(x * (1 + amt) - b * amt, 0, 255).astype(np.uint8)
        s = np.mean([ssim(R[i], sh(V[i])) for i in idx])
        if s > best[0]: best = (s, ("sharp", amt))
    if best[1] and best[0] > base + a.min:
        tot += (best[0] - base) * (f1 - f0); ch.append((k, f1 - f0, round(float(base), 3), round(float(best[0]), 3), best[1]))
for c in sorted(ch, key=lambda t: -(t[3] - t[2]) * t[1]): print(c)
print("カット", len(ch), "全体の見込み +", round(tot / n, 4))
