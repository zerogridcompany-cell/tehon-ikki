"""seg_ssim.py  手本の f0〜f1 とうちの同じ所の SSIM（mane_check と同じ 320 幅・灰・ガウス 11）を出す＝1つの直しが効いたかを、全部書き出さずに範囲だけで見る（51 の seg_ssim.py の汎用版）。
使い方：python3 seg_ssim.py <作業|手本.mp4> <うち.mp4> <f0> <f1> [--off 0] [--each]
  --off＝うちの mp4 の頭が手本の何コマ目か（範囲だけ書き出した試しの mp4 を比べる時）・--each＝コマごとにも出す
出す物：平均の SSIM（と --each でコマごと）
効いた数字（51）：場面ごとの直し（カメラの測り直し・描き分け・二層）を、その範囲だけの試し書き出しで +0.01〜0.03 を確かめてから全体に入れた
採る条件：測るだけ。直す前と後をこれで比べて、上がった直しだけ残す
"""
import argparse, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path, gray, ssim_fast

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("ours"); ap.add_argument("f0", type=int); ap.add_argument("f1", type=int)
ap.add_argument("--off", type=int, default=0); ap.add_argument("--each", action="store_true")
a = ap.parse_args()
n = a.f1 - a.f0 + 1
R = gray(ref_path(a.w), a.f0, n, 320, 180); O = gray(a.ours, a.f0 - a.off, n, 320, 180)
s = [ssim_fast(R[i], O[i]) for i in range(min(len(R), len(O)))]
if not s:
    raise SystemExit("コマが取れん（範囲か --off を見る）")
if a.each:
    for i, v in enumerate(s):
        print(a.f0 + i, round(v, 3))
print(f"{os.path.basename(a.ours)} {a.f0}-{a.f1} SSIM {np.mean(s):.3f}（{len(s)} コマ・最低 {min(s):.3f}）")
