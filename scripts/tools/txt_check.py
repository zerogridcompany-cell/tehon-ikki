"""字幕の照合：1語ずつ、手本とこっちの同じコマで字の白い形を取り、重なり（IoU）と箱のずれを出す。

python3 txt_check.py <作業フォルダ> <こっちの mp4>
- 語＝proj/src/caps.json。コマ＝出てから消えるまでの真ん中
- 白い形＝明るい白（字の芯）。手本・こっち同じ物差し
- 出す物：txt/check_<名前>.json と、IoU の中央値・0.6 未満の語
"""
import argparse, json, os, subprocess
import cv2
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("mp4")
g = ap.parse_args()
C = json.load(open(f"{g.w}/proj/src/caps.json"))
name = os.path.splitext(os.path.basename(g.mp4))[0]
od = f"{g.w}/txt/ours_{name}"; os.makedirs(od, exist_ok=True)
if not os.listdir(od):
    subprocess.run(["ffmpeg", "-v", "error", "-i", g.mp4, "-q:v", "2", f"{od}/%05d.jpg"])


def core(im):
    mn, mx = im.min(2).astype(int), im.max(2).astype(int)
    return (mn > 225) & (mx - mn < 40)


res = []
for c in C:
    f = (c["f0"] + c["f1"]) // 2
    x0, y0, x1, y1 = c["box"]
    a = cv2.imread(f"{g.w}/txt/f/{f + 1:05d}.jpg"); b = cv2.imread(f"{od}/{f + 1:05d}.jpg")
    if a is None or b is None:
        continue
    pad = 12
    sl = (slice(max(0, y0 - pad), y1 + pad), slice(max(0, x0 - pad), x1 + pad))
    ma, mb = core(a[sl]), core(b[sl])
    inter, uni = float((ma & mb).sum()), float((ma | mb).sum())
    iou = inter / uni if uni else 0
    def bb(m):
        ys, xs = np.nonzero(m)
        return None if len(xs) < 20 else (xs.min(), ys.min(), xs.max(), ys.max())
    ba, bb_ = bb(ma), bb(mb)
    d = None if not ba or not bb_ else [int(bb_[k] - ba[k]) for k in range(4)]
    res.append({"i": c["i"], "w": c["w"], "f": f, "iou": round(iou, 3), "dbox": d})
json.dump(res, open(f"{g.w}/txt/check_{name}.json", "w"), indent=1, ensure_ascii=False)
v = np.array([r["iou"] for r in res])
print(f"{len(res)} 語・IoU 中央値 {np.median(v):.3f}・平均 {v.mean():.3f}・0.6未満 {int((v < 0.6).sum())}")
print("低い順:", [(r["w"], r["iou"]) for r in sorted(res, key=lambda r: r["iou"])[:15]])
