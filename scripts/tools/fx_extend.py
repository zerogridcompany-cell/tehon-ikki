"""fx_extend.py  一枚絵の最後の2コマの動き（相似＝倍率・回り・ずれ）をくり返して、続きのコマを足す＝溶け（クロスフェード）の間も前の場面を止めん（51 の fx_extend.py の汎用版）。
使い方：python3 fx_extend.py <作業> <id> <足す数> [--write]
入れる物：その絵の最後の2コマ（fx/<id>/<f>.jpg があればそれ・無ければ green/<id>.png を M で置いた絵）
出す物：proj/public/fx/<id>/<last+1…>.jpg。--write で green.json のその絵の f1 を伸ばし、seq に足し、M は最後のコマの M を写す
  🔴 伸ばした範囲が次の絵と重なると Green.tsx は先に見つかった方を出す（GREEN の並び順）＝重なる所は溶けの重ね方を CAMERA_LOOK_README.md「溶け」で
効いた数字（51）：1255〜1275 の動きの差 224→172・動きの波 +0.001（溶けを手本の長さ＝6コマに）
採る条件：手本の切り替えが溶け（2コマ以上かけて混ざる）で、前の場面が溶けの間も動いとる時だけ。切り替えが1コマのカットには要らん
"""
import argparse, json, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path, probe, place

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("id"); ap.add_argument("n", type=int); ap.add_argument("--write", action="store_true")
a = ap.parse_args()
GJ = os.path.join(a.w, "proj", "src", "green.json"); G = json.load(open(GJ)); p = G[a.id]
W, H, _, _ = probe(ref_path(a.w)); last = p["f1"]
D = os.path.join(a.w, "proj", "public", "fx", a.id); os.makedirs(D, exist_ok=True)
pl = cv2.imread(os.path.join(a.w, "proj", "public", "green", f"{a.id}.png"))
def get(f):
    q = f"{D}/{f}.jpg"
    if f in p.get("seq", []) and os.path.exists(q):
        return cv2.imread(q)
    return place(pl, p["M"][str(f)], W, H, p.get("blur", 0))
A, B = get(last - 1), get(last)
orb = cv2.ORB_create(3000); bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
k1, d1 = orb.detectAndCompute(cv2.cvtColor(A, cv2.COLOR_BGR2GRAY), None); k2, d2 = orb.detectAndCompute(cv2.cvtColor(B, cv2.COLOR_BGR2GRAY), None)
m = bf.match(d1, d2) if d1 is not None and d2 is not None else []
M = None
if len(m) >= 20:
    M, _ = cv2.estimateAffinePartial2D(np.float32([k1[x.queryIdx].pt for x in m]), np.float32([k2[x.trainIdx].pt for x in m]), ransacReprojThreshold=3)
if M is None:
    print("🟡 最後の2コマの動きが測れん（点が足りん）＝止めたまま伸ばす"); M = np.eye(2, 3)
M3 = np.vstack([M, [0, 0, 1]]); Kc = np.eye(3)
print("1コマの動き：倍率", round(float(np.hypot(M[0, 0], M[1, 0])), 4), "横", round(float(M[0, 2]), 1), "縦", round(float(M[1, 2]), 1))
for i in range(1, a.n + 1):
    Kc = M3 @ Kc
    cv2.imwrite(f"{D}/{last + i}.jpg", cv2.warpAffine(B, Kc[:2], (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT), [cv2.IMWRITE_JPEG_QUALITY, 92])
print("足した", last + 1, "〜", last + a.n)
if a.write:
    p["seq"] = sorted(set(p.get("seq", [])) | set(range(last + 1, last + a.n + 1)))
    for i in range(1, a.n + 1):
        p["M"][str(last + i)] = p["M"][str(last)]
    p["f1"] = last + a.n; p["ext"] = a.n
    over = [k for k, q in G.items() if k != a.id and q["f0"] <= p["f1"] and q["f1"] >= last + 1]
    json.dump(G, open(GJ, "w")); print("green.json", a.id, "f1 →", p["f1"], ("🔴 重なる絵 " + ",".join(over)) if over else "")
