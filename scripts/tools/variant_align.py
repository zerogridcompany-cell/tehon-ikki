"""variant_align.py  同じ構図で中身だけ違う描き分け（Codex に描かせた N 枚）を、元の一枚絵に「動かん所」で位置合わせし、色を元の絵にそろえる（51 の sub_variants.py の汎用版）。
使い方：python3 variant_align.py <作業> <id> <描き分け1.png> [<描き分け2.png> …] [--rows 0,0.55] [--mask 動かん所.png]
入れる物：proj/public/green/<id>.png（green_fit で色を当て済みの元の絵）・描き分けの絵（大きさは問わん＝元の絵の大きさに直す）
  動かん所＝--rows（上から下の割合の帯・既定 0〜0.55＝天井や照明など）か --mask（白＝動かん所・元の絵の大きさ）
出す物：proj/public/green/<id>_v<k>.png（ORB 4000点＋射影 RANSAC 3px で元の絵に合わせ・Lab の平均と幅を元の絵へ）・green.json のその絵に "imgs": ["<id>_v1", …]
  → 毎コマどれを出すかは flow_variants.py が選ぶ
効いた数字（51）：地下鉄（中の人が動く）を6枚描き分けて毎コマ選んだ＝カット 91→94・1秒の動きの相関 0.977→0.981（SSIM は −0.0003）
採る条件：四隅のずれが 40px 未満・合った点 50 以上の絵だけ使う（外れは "imgs" に入れん）。SSIM が下がって動きが上がる＝取り合い（flow_variants の λ で決める）
"""
import argparse, json, os, sys
import cv2
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("id"); ap.add_argument("vars", nargs="+")
ap.add_argument("--rows", default="0,0.55"); ap.add_argument("--mask"); ap.add_argument("--max-corner", type=float, default=40); ap.add_argument("--min-inl", type=int, default=50)
a = ap.parse_args()
gd = os.path.join(a.w, "proj", "public", "green"); GJ = os.path.join(a.w, "proj", "src", "green.json"); G = json.load(open(GJ))
base = cv2.imread(os.path.join(gd, f"{a.id}.png")); hh, ww = base.shape[:2]; g0 = cv2.cvtColor(base, cv2.COLOR_BGR2GRAY)
if a.mask:
    m0 = cv2.resize(cv2.imread(a.mask, 0), (ww, hh), interpolation=cv2.INTER_NEAREST); m0 = (m0 > 127).astype(np.uint8) * 255
else:
    r0, r1 = map(float, a.rows.split(",")); m0 = np.zeros_like(g0); m0[int(hh * r0):int(hh * r1)] = 255
orb = cv2.ORB_create(4000); bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
k0, d0 = orb.detectAndCompute(g0, m0)
L0 = cv2.cvtColor(base, cv2.COLOR_BGR2LAB).astype(np.float32).reshape(-1, 3); bm, bs = L0.mean(0), L0.std(0)
names = []
for n, pth in enumerate(a.vars, 1):
    im = cv2.resize(cv2.imread(pth), (ww, hh)); g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    k1, d1 = orb.detectAndCompute(g, m0)
    if d1 is None or d0 is None:
        print(n, "目印が無い", pth); continue
    mt = sorted(bf.match(d1, d0), key=lambda m: m.distance)[:600]
    if len(mt) < 8:
        print(n, "合う点が足りん", pth); continue
    Hm, inl = cv2.findHomography(np.float32([k1[m.queryIdx].pt for m in mt]), np.float32([k0[m.trainIdx].pt for m in mt]), cv2.RANSAC, 3.0)
    if Hm is None:
        print(n, "射影が出ん", pth); continue
    c = np.array([[0, 0, 1], [ww, 0, 1], [0, hh, 1], [ww, hh, 1]], float).T; q = Hm @ c; q = q[:2] / q[2]; corner = float(np.abs(q - c[:2]).max())
    wv = cv2.warpPerspective(im, Hm, (ww, hh), borderMode=cv2.BORDER_REFLECT)
    L = cv2.cvtColor(wv, cv2.COLOR_BGR2LAB).astype(np.float32); lm, ls = L.reshape(-1, 3).mean(0), L.reshape(-1, 3).std(0)
    o = cv2.cvtColor(np.clip((L - lm) / (ls + 1e-6) * bs + bm, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
    ok = corner < a.max_corner and int(inl.sum()) >= a.min_inl
    nm = f"{a.id}_v{n}"
    if ok:
        cv2.imwrite(os.path.join(gd, f"{nm}.png"), o); names.append(nm)
    print(n, "合った点", int(inl.sum()), "四隅のずれ px", round(corner, 1), "→", "使う" if ok else "外す", nm if ok else pth)
G[a.id]["imgs"] = names; json.dump(G, open(GJ, "w")); print("green.json", a.id, "imgs", names)
