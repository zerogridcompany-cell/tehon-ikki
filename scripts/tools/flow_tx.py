"""flow_tx.py <作業> [--only c1_0,c2_0]  動きの写し（51 flowtx51 の汎用版）。手本の画素は使わず「動きの場」だけ測って、うちの一枚絵を毎コマ曲げる。
1枚の絵（proj/public/green/<id>.png＝色を当て済み）ごとに：
  B_k＝絵を基準のコマ k（その絵の一番合うコマ）の行列 M[k] で画面に置いてぼかした絵
  手本のコマ f → k の DIS フロー（640x360・σ2 でならす）＝ f の画素が k のどこにあったか
  候補 A＝今まで通り（M[f] で置く）／候補 B＝B_k をフローで曲げる → コマごとに手本との SSIM が高い方
出す物：proj/public/fx/<id>/<f>.jpg（画面の大きさ・ぼかし込み）・green.json の各絵に "seq": [B を使ったコマ]
🔴 Green.tsx は seq に入っとるコマだけ fx の絵を変形なしで出す（ぼかしも掛けん）
"""
import argparse, glob, json, os
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

cv2.setNumThreads(2)
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--only", default=""); ap.add_argument("--min-gain", type=float, default=0.005); ap.add_argument("--force", action="store_true", help="手本が動いとるコマは、SSIM が 0.01 以内の下がりなら曲げた絵を使う（静止画のまま止めん・10/28 依頼者「画像を動かしとるのを全部なくす」）")
a = ap.parse_args()
W_ = a.w; ref = glob.glob(f"{W_}/ref/*.mp4")[0]
GJ = f"{W_}/proj/src/green.json"; G = json.load(open(GJ))
cap = cv2.VideoCapture(ref); W, H = int(cap.get(3)), int(cap.get(4)); w2 = 640; h2 = int(round(w2 * H / W))
dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
YS, XS = np.mgrid[0:H, 0:W].astype(np.float32)
only = set(x for x in a.only.split(",") if x)
tot = []
for pid, p in G.items():
    if only and pid not in only:
        continue
    f0, f1 = p["f0"], p["f1"]
    if f1 - f0 < 2:
        continue
    img = cv2.imread(f"{W_}/proj/public/green/{pid}.png")
    cap.set(cv2.CAP_PROP_POS_FRAMES, f0); R = []
    for _ in range(f0, f1 + 1):
        ok, im = cap.read(); R.append(im if ok else R[-1])
    def place(f):
        M = np.array(p["M"][str(f)], np.float32).reshape(2, 3)
        o = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        s = p.get("blur", 0) * float(np.sqrt(abs(np.linalg.det(M[:, :2]))))
        return cv2.GaussianBlur(o, (0, 0), s) if s > 0.3 else o
    g = lambda im: cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (w2, h2))
    A = [place(f) for f in range(f0, f1 + 1)]
    sa = [ssim(g(A[i]), g(R[i]), data_range=255) for i in range(len(R))]
    k = int(np.argmax(sa)); s0 = float(np.mean(sa))
    GR = [g(x) for x in R]; O = {k: A[k]}
    def warp(src, i, j):  # 手本 i の画素が j のどこにあったか → src（j に合った絵）を曲げる
        fl = cv2.GaussianBlur(dis.calc(GR[i], GR[j], None), (0, 0), 2)
        fl = cv2.resize(fl, (W, H)) * (W / w2)
        return cv2.remap(src, XS + fl[..., 0], YS + fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    seq, outs = [], {}
    # 基準のコマ k から外へ1コマずつ：候補＝置くだけ／k の絵を曲げる／隣（k 側）の出来た絵を曲げる
    for i in list(range(k + 1, len(R))) + list(range(k - 1, -1, -1)):
        j = i - 1 if i > k else i + 1
        cs = [(sa[i], A[i], 0), None, None]
        for n, (src, jj) in enumerate(((A[k], k), (O[j], j)), 1):
            Bw = warp(src, i, jj); cs[n] = (ssim(g(Bw), GR[i], data_range=255), Bw, n)
        best = max(cs, key=lambda c: c[0])
        cs2 = [c for c in cs[1:] if c]
        if a.force and cs2:
            bw = max(cs2, key=lambda c: c[0])
            if bw[0] >= sa[i] - 0.01 and float(np.mean(cv2.absdiff(GR[i], GR[j]))) > 0.6: best = bw
        if best[2] and (best[0] > sa[i] + a.min_gain or a.force):
            seq.append(f0 + i); outs[f0 + i] = best[1]; sa[i] = best[0]; O[i] = best[1]
        else:
            O[i] = A[i]
    od = f"{W_}/proj/public/fx/{pid}"; os.makedirs(od, exist_ok=True)
    for f in glob.glob(f"{od}/*.jpg"):
        os.remove(f)
    for f, im in outs.items():
        cv2.imwrite(f"{od}/{f}.jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 95])
    p["seq"] = sorted(seq); p["ssim_fx"] = round(float(np.mean(sa)), 4)
    tot.append((pid, s0, p["ssim_fx"], len(seq), len(R)))
    print(pid, f"{s0:.3f}→{p['ssim_fx']:.3f}", f"曲げ {len(seq)}/{len(R)}", flush=True)
json.dump(G, open(GJ, "w"))
if tot:
    n = sum(t[4] for t in tot)
    print("コマ平均", round(sum(t[1] * t[4] for t in tot) / n, 4), "→", round(sum(t[2] * t[4] for t in tot) / n, 4))
