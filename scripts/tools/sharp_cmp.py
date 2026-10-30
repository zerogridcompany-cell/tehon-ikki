"""sharp_cmp.py  手本とうちの鋭さ（全画面の横の差の平均・ラプラシアンの分散）をコマごとに並べる＝うちが手本より鋭すぎる場面を探す（51 の sharp_cmp.py の汎用版）。
使い方：python3 sharp_cmp.py <作業> <うち.mp4> <コマ,コマ,…>
入れる物：手本・うちの書き出し（手本の大きさに直して測る）
出す物：1行ずつ「コマ（秒） 横の差 手本・うち（倍）・ラプラシアン 手本・うち（倍）」
効いた数字（51）：手本（TikTok の圧縮）はうちの絵より 1.6〜3倍やわらかかった→場面ごとに「横の差＝手本」になる σ をかけて SSIM 0.6923→0.7013・余計な切り替え 28→21
採る条件：測るだけ。横の差が 1.2倍を超えるカットは look_shot.py のぼかしが効く候補（直すのは look_shot＝SSIM が上がる時だけ採る）
"""
import argparse, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path, probe, one

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("ours"); ap.add_argument("frames")
a = ap.parse_args()
ref = ref_path(a.w); W, H, fps, _ = probe(ref)
for f in [int(v) for v in a.frames.split(",") if v]:
    x = one(ref, f, True); y = one(a.ours, f, True, (W, H))
    if x is None or y is None:
        print(f, "コマが無い"); continue
    x = x.astype(np.float32); y = y.astype(np.float32)
    sa, sb = np.abs(np.diff(x, axis=1)).mean(), np.abs(np.diff(y, axis=1)).mean()
    la, lb = cv2.Laplacian(x, cv2.CV_32F).var(), cv2.Laplacian(y, cv2.CV_32F).var()
    print(f"{f}({f / fps:.2f}秒) 横の差 手本 {sa:.2f} うち {sb:.2f}（{sb / max(sa, 1e-6):.2f}倍）  ラプラシアン 手本 {la:.0f} うち {lb:.0f}（{lb / max(la, 1e-6):.2f}倍）")
