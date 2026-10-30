"""hold.py  手本が止まっとるコマ（3コマ打ちの2・3コマ目・25fps→30fps の重ね・止め絵）を見つけて「このコマはどのコマの絵を出すか」の表を作る（51 の hold.py の汎用版・差は自分で測る）。
使い方：python3 hold.py <作業> [--th 0.3] [--out proj/src/hold.json]
入れる物：手本（<作業>/ref/*.mp4）。320x180 の灰で前のコマとの明るさの差の平均を全コマ測る（軽い）
出す物：[H0, H1, …]（コマ f で出す絵のコマ番号。動いたコマ＝f・止まったコマ＝前の動いたコマ）。止めの数・一番長い止め・3コマ打ちらしい塊（止め2が続く所）も出す
  🔴 Remotion 側で、描く層（Green・Cards・字の動き）の「今のコマ」を H[f] に置き換える所が要る（CAMERA_LOOK_README.md「hold」）。土台の動画（base.mp4）には使わん
効いた数字（51）：3コマ打ちの段の始まりを hold.json の止めコマから取る（目で読んだコマ番号を段の頭にして v33 で1段遅れた）。手本の pts の跳び（2715→2716）から後を1コマ遅らせて動きの波 0.931→0.957
採る条件：止めのコマが全体の 5% 以上か、3コマ打ちの塊がある手本だけ。描く層が毎コマ動いとって、手本は止まっとる所（persec の d＝0 の所）で動きの波が下がっとる時に効く
"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path, gray

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--th", type=float, default=0.3); ap.add_argument("--out")
a = ap.parse_args()
F = gray(ref_path(a.w), 0, 10 ** 7, 320, 180)
N = len(F); mr = np.r_[99.0, [float(np.abs(F[i].astype(np.int16) - F[i - 1]).mean()) for i in range(1, N)]]
H = [0] * N
for f in range(1, N):
    H[f] = f if mr[f] > a.th else H[f - 1]
stop = [f for f in range(N) if H[f] != f]
runs = {}
f = 0
while f < N:
    if H[f] != f:
        g = f
        while g < N and H[g] == H[f]:
            g += 1
        runs[g - f] = runs.get(g - f, 0) + 1; f = g
    else:
        f += 1
out = a.out or os.path.join(a.w, "proj", "src", "hold.json")
json.dump(H, open(out, "w"))
print(f"コマ {N}  止め {len(stop)}（{100 * len(stop) / N:.1f}%）  一番長い止め {max([f - H[f] for f in range(N)])} コマ  止めの長さ別の数 {dict(sorted(runs.items())[:8])}")
print("3コマ打ちらしい（止め2の塊）", runs.get(2, 0), "・書いた", out)
