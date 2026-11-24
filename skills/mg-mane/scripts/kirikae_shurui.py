# 手本の切り替えの種類（光る＝白が乗る / ずれ＝横の帯がずれる / ただの切り替え）を 1 コマずつの明るさと帯の境目の数で決める
# 使い方: python3 kirikae_shurui.py <手本.mp4> <切り替えの表.json [[名,頭のコマ],…]> <出力.json>
#  光る＝頭の 3 コマで明るさが +60 以上（白を重ねて 0.92→0.58→0.25 で消える形が多い）/ ずれ＝隣の行との差が大きい行が 6 本以上
import cv2, sys, json, numpy as np
cap = cv2.VideoCapture(sys.argv[1]); F = []
while True:
    ok, im = cap.read()
    if not ok: break
    F.append(cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (480, 270)).astype(np.float32))
CUT = [tuple(x) for x in json.load(open(sys.argv[2]))]
def bands(g):  # 横の帯のずれ＝隣の行との差が大きい行の数（帯の境目）
    d = np.abs(np.diff(g, axis=0)).mean(1); return int((d > 18).sum())
out = {}
for nm, c in CUT[1:]:
    rows = []
    for f in range(c - 2, min(len(F), c + 7)):
        rows.append(dict(f=f - c, luma=round(float(F[f].mean()), 1), bands=bands(F[f])))
    lu = [r['luma'] for r in rows]; mx = max(lu[0:5]); lo = min(lu[0], lu[-1]); nb = max(r['bands'] for r in rows[2:6])
    kind = 'flash' if mx - lo > 60 and mx > 150 else ('glitch' if nb >= 6 else 'cut')  # 表の頭が 1〜2 コマずれても拾えるように c-2..c+2 の山と前後の谷で見る
    out[nm] = dict(at=c, kind=kind, rows=rows); print(nm, c, kind, [(r['f'], r['luma'], r['bands']) for r in rows])
json.dump(out, open(sys.argv[3], 'w'), indent=0)
