"""カットのファイルを、Remotion の shot_look（g・o・blur）をかけた形で手本と比べる（640 白黒 SSIM・カットの平均）。
python3 cut_eval.py <作業> <カット番号> <ファイル> [<ファイル2> ...]
"""
import glob, json, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from retime import rd, looks, post_f
import retime
from geo import geo, half
w, cut = os.path.abspath(sys.argv[1]), sys.argv[2]
retime.use_geo(w); FPS = geo(w)["FPS"]; MW, MH = half(w)
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{cut}:")][0]
s0, s1 = map(float, seg.split(":")[1].split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS)
R = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(f0, f1 - 1)); n = len(R)
LK = looks(w, f0, n)
g = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (MW, MH))
for p in sys.argv[3:]:
    C = rd(p)[:n]
    print(p, round(float(np.mean([ssim(g(R[k]), g(post_f(C[k], LK[k]))) for k in range(min(n, len(C)))])), 4))
