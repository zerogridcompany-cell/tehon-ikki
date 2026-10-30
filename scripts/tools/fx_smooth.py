"""fx_smooth.py  動きの写し（fx＝flow_tx・flow_variants で曲げたコマ）の揺れを時間でならす（51 の fx_gsmooth.py と fx_tsmooth.py を1本に）。
使い方：python3 fx_smooth.py <作業> <id> --sigma 1.2 [--a f --b f]   （ガウス・σ はコマ）
        python3 fx_smooth.py <作業> <id> --tap 0.25 [--a f --b f]    （3コマ：(1−2w)·f＋w·(前＋後)＝跳ね1コマの所に）
入れる物：proj/public/fx/<id>/<f>.jpg
出す物：同じ所に上書き。元は <作業>/arai/fx_bak/<id>/ に1回目だけ残す（2回目からはそこから作り直す＝何度回しても同じ）。--sigma 0 で元に戻る
  fx のコマが飛び飛び（flow_tx の seq）の時は、続いとる塊の中だけでならす（端は端のコマを伸ばす）
効いた数字（51）：fx は曲げの揺れと JPEG の粒で手本の 2〜3倍動く＝sunset 2565 の動きの比 2.46→1.03・suit 2.28→0.99・SSIM 0.732→0.733。--tap は手本に無い切れ目が出る1コマに
採る条件：先に persec.py で手本とうちの「d（前のコマとの差）」をその範囲で比べ、うちが手本の 1.5倍以上動く時だけ。σ は 比が 1.0 前後になる一番小さい値（大きいと本当の動きも消える）
"""
import argparse, glob, os, shutil
import cv2
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("id"); ap.add_argument("--sigma", type=float); ap.add_argument("--tap", type=float)
ap.add_argument("--a", type=int); ap.add_argument("--b", type=int)
a = ap.parse_args()
if (a.sigma is None) == (a.tap is None):
    raise SystemExit("--sigma か --tap のどちらか1つ")
D = os.path.join(a.w, "proj", "public", "fx", a.id); K = os.path.join(a.w, "arai", "fx_bak", a.id)
if not os.path.exists(K):
    os.makedirs(os.path.dirname(K), exist_ok=True); shutil.copytree(D, K)
fs = sorted(int(os.path.basename(p)[:-4]) for p in glob.glob(f"{K}/*.jpg"))
lo = a.a if a.a is not None else fs[0]; hi = a.b if a.b is not None else fs[-1]
fs = [f for f in fs if lo <= f <= hi]
runs, cur = [], []
for f in fs:
    if cur and f != cur[-1] + 1:
        runs.append(cur); cur = []
    cur.append(f)
if cur:
    runs.append(cur)
n = 0
for run in runs:
    X = {f: cv2.imread(f"{K}/{f}.jpg").astype(np.float32) for f in run}; r0, r1 = run[0], run[-1]
    at = lambda f: X[min(r1, max(r0, f))]
    if a.sigma is not None:
        s = a.sigma; r = int(np.ceil(3 * s)) if s > 0 else 0
        kk = np.exp(-0.5 * (np.arange(-r, r + 1) / max(s, 1e-3)) ** 2); kk /= kk.sum()
    for f in run:
        if a.sigma is not None:
            o = X[f] if a.sigma <= 0 else sum(kk[j] * at(f + j - r) for j in range(len(kk)))
        else:
            o = (1 - 2 * a.tap) * X[f] + a.tap * (at(f - 1) + at(f + 1))
        cv2.imwrite(f"{D}/{f}.jpg", np.clip(o, 0, 255).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 92]); n += 1
print("ならした", a.id, n, "コマ", len(runs), "塊", f"σ={a.sigma}" if a.sigma is not None else f"w={a.tap}")
