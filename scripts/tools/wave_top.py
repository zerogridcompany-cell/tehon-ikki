"""wave_top.py  動きの波（mane_check と同じ：10fps・320幅・RGB の前のコマとの差）の相関を、どのコマが一番下げとるかを順に出す（51 の wave_top.py と wave_diff.py を1本に）。
使い方：python3 wave_top.py <作業|手本.mp4> <うち.mp4> [--n 25] [--vs 前の版.mp4]
入れる物：手本・うちの書き出し（長さは短い方にそろえる）
出す物：
  ふつう：相関と、(z手本−zうち)²/2/n の大きい順に「秒・失い・手本とうちの差・前後」＝そこを 30fps で見に行く
  --vs：2つの版で相関を比べ、前の版より相関を下げたコマ（z手本·z今 − z手本·z前 の小さい順）＝直して悪くした所
効いた数字（51）：どこを直すかを数字で決めた（溶けの間に前の場面を止めとった所・寄りの段・3コマ打ち）。手本の pts の跳びを見つけて波 0.931→0.957
採る条件：測るだけ。上位の秒を persec.py・seg_ssim.py で細かく見てから直す
"""
import argparse, os, subprocess, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("ours"); ap.add_argument("--n", type=int, default=25); ap.add_argument("--vs")
a = ap.parse_args()


def fr(p):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-threads", "2", "-i", p, "-an", "-vf", "fps=10,scale=320:180,format=rgb24", "-f", "rawvideo", "-"],
                         capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 180, 320, 3)
    return np.r_[0, [float(np.abs(f[i].astype(np.int16) - f[i - 1]).mean()) for i in range(1, len(f))]]


R = fr(ref_path(a.w)); O = fr(a.ours); B = fr(a.vs) if a.vs else None
n = min(len(R), len(O), len(B) if B is not None else 10 ** 9); R, O = R[:n], O[:n]
z = lambda x: (x - x.mean()) / (x.std() + 1e-9)
print("相関", round(float(np.corrcoef(R, O)[0, 1]), 4), f"（{n / 10:.1f}秒）")
if B is not None:
    B = B[:n]; print("前の版の相関", round(float(np.corrcoef(R, B)[0, 1]), 4))
    d = z(R) * z(O) - z(R) * z(B)
    for i in np.argsort(d)[:a.n]:
        print(f"{i / 10:5.1f}s 下げた {d[i] / n:+.4f}  手本 {R[i]:6.1f}  今 {O[i]:6.1f}  前 {B[i]:6.1f}")
else:
    c = (z(R) - z(O)) ** 2 / 2 / n
    for i in np.argsort(-c)[:a.n]:
        print(f"{i / 10:5.1f}s 失い {c[i]:.4f}  手本 {R[i]:6.1f} うち {O[i]:6.1f}  前後 手本 {R[max(0, i - 1)]:.0f},{R[min(n - 1, i + 1)]:.0f} うち {O[max(0, i - 1)]:.0f},{O[min(n - 1, i + 1)]:.0f}")
