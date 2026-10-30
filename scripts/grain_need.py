"""一枚絵の場面に足す粒（コマごとの細かい揺れ）の強さを、手本とうちの書き出しから測る → proj/src/grain.json

python3 grain_need.py <作業フォルダ> <うちの書き出し mp4>
- 揺れ＝となりのコマの差から 3px より大きい形を引いた物の標準偏差（中央値）。足す粒＝√(手本²−うち²)/√2・上限 3（手本の揺れには絵の中の本当の動きも入るため）
- Green.tsx の GRAIN_K（強さの換算）は 0.038（r2 で実測：K=0.1 で揺れ 7.17・手本 2.73 に合わせた）。🔴 粒はぼかしの後に足す（前だと消える）
- r2 の実測：SSIM −0.001・細かい動き 14→16fps＝残す価値あり。51 の決まり「乱数は手本に合わせるほど画素の SSIM は下がる＝両方のコストで選ぶ」
"""
import glob, json, sys
import cv2
import numpy as np

w, ours = sys.argv[1], sys.argv[2]
G = json.load(open(f"{w}/proj/src/green.json"))
def tn(cap, a, b):
    cap.set(cv2.CAP_PROP_POS_FRAMES, a); prev = None; ds = []
    for n in range(a, b + 1):
        ok, im = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(float)
        if prev is not None:
            d = g - prev; d = d - cv2.GaussianBlur(d, (0, 0), 3); ds.append(d.std())
        prev = g
    return float(np.median(ds)) if ds else 0.0
cr = cv2.VideoCapture(glob.glob(f"{w}/ref/*.mp4")[0]); co = cv2.VideoCapture(ours); out = {}
for k, p in sorted(G.items()):
    if p["f1"] - p["f0"] < 2:
        continue
    r, o = tn(cr, p["f0"], p["f1"]), tn(co, p["f0"], p["f1"])
    out[k] = round(min(3.0, max(0.0, r * r - o * o) ** 0.5 / 1.414), 2)
json.dump(out, open(f"{w}/proj/src/grain.json", "w"), indent=0)
print("粒", len(out), "枚", out)
