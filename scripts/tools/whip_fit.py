"""whip_fit.py  手本の横振り（whip pan）を「左の絵と右の絵を D px ずらしてつないだ1枚の地図」を流す形で当てる（51 の whip_fit.py の汎用版・D の自動測りは cam_v2.py の重なり）。
使い方：python3 whip_fit.py <作業> <f0> <f1> <左の止まったコマ> <右の止まったコマ> [--D px] [--out whip.json]
入れる物：手本（<作業>/ref/*.mp4）。左右のコマ＝振りの前と後の止まったコマ
出す物：{"D","left","right","rows":[{"f","s","L","err"}]}（画面の画素・s＝地図の左から何 px の所を映すか 0→D・L＝横ぶれの箱の幅）。既定 <作業>/shirabe/whip_<f0>.json
  --D 無し＝右のコマの左 1/4 の帯を左のコマの中で探す（matchTemplate）＝D
測り方：幅 480 の灰で総当たり（s は 1px 刻み・L は 1〜51 の 10段）・上下の端（字幕・黒帯）を外して縦 18〜89% の帯で差の平均
効いた数字（51）：振りの13コマ 0.59〜0.78→0.87〜0.89（D 1036・s 164/412/624/872・L 92/124/124/92）。2枚の重ね溶け＋全方向ぼかしより良い
採る条件：err が止まったコマ同士の err の 2倍以内に収まるコマだけ地図で流す。外れるコマは振りの中で別の物が映っとる＝絵を足す
🔴 Remotion に地図を流す部品が要る（CAMERA_LOOK_README.md「whip」）。ぶれは横だけ（feGaussianBlur stdDeviation="σ 0"・σ＝L×0.29）
"""
import argparse, json, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path, probe, gray

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("f0", type=int); ap.add_argument("f1", type=int)
ap.add_argument("lf", type=int); ap.add_argument("rf", type=int); ap.add_argument("--D", type=int); ap.add_argument("--out")
a = ap.parse_args()
src = ref_path(a.w); W, H, _, _ = probe(src); w = 480; h = int(round(w * H / W / 2)) * 2; k = W / w
rd = lambda f: gray(src, f, 1, w, h)[0].astype(np.float32)
A, B = rd(a.lf), rd(a.rf)
y0, y1 = int(h * 0.18), int(h * 0.89)
if a.D is None:
    t = B[y0:y1, : w // 4]
    r = cv2.matchTemplate(A, t, cv2.TM_CCOEFF_NORMED); _, mv, _, ml = cv2.minMaxLoc(r)
    Dk = ml[0]; print(f"D を測った：{Dk * k:.0f}px（一致 {mv:.3f}・縦のずれ {(ml[1] - y0) * k:+.0f}px）")
    if mv < 0.5:
        print("🔴 一致が 0.5 未満＝左右の絵が重なっとらん。--D を手で入れるか、振りの中の絵を足す")
else:
    Dk = int(round(a.D / k))
comp = np.zeros((h, w + Dk), np.float32); comp[:, :w] = A; comp[:, Dk:] = B
Ls = [1, 3, 5, 9, 13, 17, 23, 31, 41, 51]
blurs = {L: (comp if L == 1 else cv2.blur(comp, (L, 1))) for L in Ls}
R = gray(src, a.f0, a.f1 - a.f0 + 1, w, h).astype(np.float32)
rows = []
for i, f in enumerate(range(a.f0, a.f1 + 1)):
    r = R[i]; best = None
    for L in Ls:
        c = blurs[L]
        for s in range(0, Dk + 1):
            e = float(np.mean(np.abs(c[y0:y1, s:s + w] - r[y0:y1])))
            if best is None or e < best[0]:
                best = (e, s, L)
    rows.append({"f": f, "err": round(best[0], 2), "s": round(best[1] * k), "L": round(best[2] * k)}); print(rows[-1], flush=True)
out = a.out or os.path.join(a.w, "shirabe", f"whip_{a.f0}.json")
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
json.dump({"D": round(Dk * k), "left": a.lf, "right": a.rf, "rows": rows}, open(out, "w")); print("書いた", out)
