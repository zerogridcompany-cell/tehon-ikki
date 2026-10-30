"""flow_variants.py  描き分け（green.json の "imgs"）がある一枚絵で、毎コマ「どの絵を出すか」を選んで fx の絵を作る（51 の flowtx51.py の v46〜v48＝imgs の所だけ。曲げ方は flow_tx.py と同じ）。
使い方：/usr/bin/python3 flow_variants.py <作業> --only <id>[,<id>…] [--lam 0.004]
入れる物：green.json の絵（M・blur・"imgs"＝variant_align.py が書く）・proj/public/green/<id>.png と <id>_v<k>.png・手本
1コマずつ：候補＝元の絵と描き分け全部について {M[f] で置くだけ／基準のコマ k に置いた絵を手本 f→k の DIS フロー（640幅・σ2）で曲げる}
  点＝SSIM（640幅の灰）− λ×｜うちの前のコマとの差 − 手本の前のコマとの差｜（320幅）。一番高い候補を出す
  🔴 SSIM だけで選ぶと元の1枚ばかり選ぶ（動きが消える）＝動きの差を引く（51 v48・λ 0.004）
出す物：proj/public/fx/<id>/<f>.jpg（全部のコマ・画面の大きさ・ぼかし込み）・green.json のその絵の "seq"＝全部のコマ・"pick"＝選んだ絵の番号の列（0＝元の絵）
  → Green.tsx は今のまま読める（seq のコマは fx の絵を変形なしで出す）
効いた数字（51）：地下鉄 6枚の描き分け＝カット 91→94・1秒の動きの相関 0.977→0.981（SSIM は −0.0003）
採る条件：書き出して mane_check の「動きの波」かカットが上がって、SSIM が 0.002 より下がらん時だけ。下がるなら λ を下げるか描き分けを外す（flow_tx.py に戻す）
"""
import argparse, glob, json, os
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

cv2.setNumThreads(2)
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--only", required=True); ap.add_argument("--lam", type=float, default=0.004)
a = ap.parse_args()
W_ = a.w; ref = sorted(glob.glob(f"{W_}/ref/*.mp4"))[0]
GJ = f"{W_}/proj/src/green.json"; G = json.load(open(GJ))
cap = cv2.VideoCapture(ref); W, H = int(cap.get(3)), int(cap.get(4)); w2 = 640; h2 = int(round(w2 * H / W))
dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
YS, XS = np.mgrid[0:H, 0:W].astype(np.float32)
for pid in [x for x in a.only.split(",") if x]:
    p = G[pid]; f0, f1 = p["f0"], p["f1"]
    names = [pid] + list(p.get("imgs", []))
    if len(names) < 2:
        print(pid, "描き分けが無い（variant_align.py を先に）＝flow_tx.py を使う"); continue
    imgs = [cv2.imread(f"{W_}/proj/public/green/{n}.png") for n in names]
    # 🔴 OpenCV の seek は不正確なことがある＝f0 に合わせてから順に読む（flow_tx と同じ）
    cap.set(cv2.CAP_PROP_POS_FRAMES, f0); R = []
    for _ in range(f0, f1 + 1):
        ok, im = cap.read(); R.append(im if ok else R[-1])
    def place(img, f):
        M = np.array(p["M"][str(f)], np.float32).reshape(2, 3)
        o = cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderValue=0)
        s = p.get("blur", 0) * float(np.sqrt(abs(np.linalg.det(M[:, :2]))))
        return cv2.GaussianBlur(o, (0, 0), s) if s > 0.3 else o
    g = lambda im: cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (w2, h2))
    q = lambda im: cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (320, int(round(320 * H / W))), interpolation=cv2.INTER_AREA).astype(np.float32)
    GR = [g(x) for x in R]; QR = [q(x) for x in R]
    base_s = [ssim(g(place(imgs[0], f0 + i)), GR[i], data_range=255) for i in range(len(R))]
    k = int(np.argmax(base_s)); Ak = [place(im, f0 + k) for im in imgs]
    od = f"{W_}/proj/public/fx/{pid}"; os.makedirs(od, exist_ok=True)
    for x in glob.glob(f"{od}/*.jpg"):
        os.remove(x)
    pick, ss, prev = [], [], None
    for i in range(len(R)):
        f = f0 + i
        fl = None if i == k else cv2.resize(cv2.GaussianBlur(dis.calc(GR[i], GR[k], None), (0, 0), 2), (W, H)) * (W / w2)
        dref = float(np.abs(QR[i] - QR[i - 1]).mean()) if i > 0 else 0.0
        best = None
        for ci, im in enumerate(imgs):
            cands = [place(im, f)]
            if fl is not None:
                cands.append(cv2.remap(Ak[ci], XS + fl[..., 0], YS + fl[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE))
            for c in cands:
                s = ssim(g(c), GR[i], data_range=255); cq = q(c)
                dour = float(np.abs(cq - prev).mean()) if prev is not None else dref
                sc = s - a.lam * abs(dour - dref)
                if best is None or sc > best[0]:
                    best = (sc, ci, c, cq, s)
        cv2.imwrite(f"{od}/{f}.jpg", best[2], [cv2.IMWRITE_JPEG_QUALITY, 95])
        pick.append(best[1]); ss.append(best[4]); prev = best[3]
    p["seq"] = list(range(f0, f1 + 1)); p["pick"] = pick; p["ssim_fx"] = round(float(np.mean(ss)), 4)
    print(pid, f"元の絵だけ {np.mean(base_s):.3f} → 選んで {np.mean(ss):.3f}", "選んだ絵", "".join(str(c) for c in pick), flush=True)
json.dump(G, open(GJ, "w"))
