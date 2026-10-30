"""zoom_meas.py  コマごとの寄り（相似の倍率・ずれ）を ORB で測る＝手本が本当に寄っとるか・どのコマから寄るかを見る（51 の zoom_meas.py の汎用版）。
使い方：python3 zoom_meas.py <作業|mp4> <f0> <f1> [--out zoom.json]
入れる物：手本（<作業>/ref/*.mp4）か mp4。範囲 f0〜f1
出す物：1行ずつ「コマ 倍率（前のコマ比）・横・縦（画面の px）・差の平均・合った点」。切れ目（合う点 30 未満）は「切れ目」。--out で json
効いた数字（51）：短い差し替えの動物の場面（2544〜2555）は手本は 1.000＝寄らん、と分かって寄りを外した＝84.8秒の切り替えが合った。ボクシングの寄りは「止まって 2271 で寄る」（毎コマ寄せとった）
採る条件：測るだけ。倍率が 1.000±0.002 が続く所は寄せん・段で跳ぶ所（3コマ打ち）は hold.py の止めコマとそろえる
"""
import argparse, json, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path, probe, gray

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("f0", type=int); ap.add_argument("f1", type=int); ap.add_argument("--out")
a = ap.parse_args()
src = ref_path(a.w); W, H, _, _ = probe(src); w = 960; h = int(round(w * H / W / 2)) * 2; k = W / w
F = gray(src, a.f0, a.f1 - a.f0 + 1, w, h)
orb = cv2.ORB_create(2000); bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True); rows = []
for i in range(len(F) - 1):
    x, y = F[i], F[i + 1]; mad = float(np.abs(x.astype(int) - y).mean()); f = a.f0 + i + 1
    k1, d1 = orb.detectAndCompute(x, None); k2, d2 = orb.detectAndCompute(y, None)
    m = bf.match(d1, d2) if d1 is not None and d2 is not None else []
    if len(m) < 30:
        print(f, "切れ目", len(m), f"差 {mad:.1f}"); rows.append({"f": f, "cut": True, "mad": round(mad, 2)}); continue
    p1 = np.float32([k1[q.queryIdx].pt for q in m]); p2 = np.float32([k2[q.trainIdx].pt for q in m])
    M, inl = cv2.estimateAffinePartial2D(p1, p2)
    if M is None or inl.sum() < 20:
        print(f, "切れ目?", f"差 {mad:.1f}"); rows.append({"f": f, "cut": True, "mad": round(mad, 2)}); continue
    s = float(np.hypot(M[0, 0], M[1, 0]))
    print(f, f"倍率 {s:.4f}  横 {M[0, 2] * k:+.1f}  縦 {M[1, 2] * k:+.1f}  差 {mad:.1f}  点 {int(inl.sum())}")
    rows.append({"f": f, "s": round(s, 4), "dx": round(float(M[0, 2] * k), 1), "dy": round(float(M[1, 2] * k), 1), "mad": round(mad, 2)})
if a.out:
    json.dump(rows, open(a.out, "w")); print("書いた", a.out)
