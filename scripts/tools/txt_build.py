"""字幕の1語ずつを Remotion で描く表（proj/src/caps.json）にする。大きさと位置は手本の字の形から逆算する。

python3 txt_build.py <作業フォルダ> [--serif-w 550] [--sans-w 800]
- 書体：txt/eye/style.json（Codex の目＝serif/sans）→ serif＝Libre Baskerville Italic・sans＝Inter
- 箱：手本の3コマで白い所（字）の外枠（読み取りの箱の中）。取れん時は読み取りの箱
- 大きさ＝箱の高さ ÷ その語を描いた時の字の高さ・位置＝字の左上が箱の左上に来る基準線（SVG の x,y）
"""
import argparse, json
import cv2
import numpy as np
from PIL import ImageFont

ap = argparse.ArgumentParser(); ap.add_argument("w")
ap.add_argument("--serif-w", type=int, default=550); ap.add_argument("--sans-w", type=int, default=800)
g = ap.parse_args()
FD = f"{g.w}/proj/public/fonts/"
FONTS = {"serif": ("LibreBaskerville-Italic[wght].ttf", {"Weight": g.serif_w}),
         "sans": ("Inter[opsz,wght].ttf", {"Optical size": 32, "Weight": g.sans_w})}
cache = {}


def font(kind):
    if kind not in cache:
        file, ax = FONTS[kind]
        f = ImageFont.truetype(FD + file, 1000)
        vals = []
        for a in f.get_variation_axes():
            nm = a["name"].decode() if isinstance(a["name"], bytes) else a["name"]
            vals.append(ax.get(nm, a["default"]))
        f.set_variation_by_axes(vals)
        cache[kind] = f
    return cache[kind]


def tight(x):
    x0, y0, x1, y1 = map(int, x["box"])
    f = (x["f0"] + x["f1"]) // 2
    ms = []
    for d in (-1, 0, 1):
        im = cv2.imread(f"{g.w}/txt/f/{min(x['f1'], max(x['f0'], f + d)) + 1:05d}.jpg")
        c = im[max(0, y0 - 8):y1 + 8, max(0, x0 - 2):x1 + 2]
        mn, mx = c.min(2).astype(int), c.max(2).astype(int)
        ms.append((mn > 225) & (mx - mn < 40))
    m = np.logical_and.reduce(ms)
    # 小さい点（背景の白）を外す
    n, lab, st, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8))
    keep = np.zeros_like(m)
    for k in range(1, n):
        if st[k, cv2.CC_STAT_AREA] >= 12:
            keep |= lab == k
    ys, xs = np.nonzero(keep)
    if len(xs) < 40:
        return None
    return [max(0, x0 - 2) + int(xs.min()), max(0, y0 - 8) + int(ys.min()),
            max(0, x0 - 2) + int(xs.max()) + 1, max(0, y0 - 8) + int(ys.max()) + 1]


W = json.load(open(f"{g.w}/txt/words.json"))
L = json.load(open(f"{g.w}/txt/eye/style.json"))
out, prev = [], None
for i, x in enumerate(W):
    kind = L.get(str(i))
    if kind not in ("serif", "sans"):
        kind = prev or "serif"
    prev = kind
    if "box" not in x:
        continue
    bx = tight(x) or [round(v) for v in x["box"]]
    f = font(kind)
    l, t, r, b = f.getbbox(x["w"], anchor="ls")
    fs = (bx[3] - bx[1]) * 1000 / (b - t)
    sx = ((bx[2] - bx[0]) * 1000 / (r - l)) / fs  # 横の伸び（1.0 が書体どおり）
    out.append({"i": i, "w": x["w"], "f0": x["f0"], "f1": x["f1"], "kind": kind, "fs": round(fs, 2),
                "x": round(bx[0] - l * fs / 1000, 1), "y": round(bx[1] - t * fs / 1000, 1), "sx": round(sx, 3),
                "box": bx, "guess": x.get("guess", False)})
# 大きさの外れを直す：同じ句・同じ書体の語の大きさの中央値から2割以上外れた語は、中央値にして箱の真ん中を保つ（10/25「to」が倍の大きさになった）
from collections import defaultdict
grp = defaultdict(list)
for o in out:
    grp[(W[o["i"]]["line"], o["kind"])].append(o["fs"])
allmed = {k: float(np.median([o["fs"] for o in out if o["kind"] == k])) for k in ("serif", "sans")}
fixed = 0
for o in out:
    fl = grp[(W[o["i"]]["line"], o["kind"])]
    med = float(np.median(fl)) if len(fl) >= 2 else allmed[o["kind"]]
    if abs(o["fs"] / med - 1) > 0.2 and (len(fl) >= 2 or abs(o["fs"] / med - 1) > 0.35):
        f = font(o["kind"]); l, t, r, b = f.getbbox(o["w"], anchor="ls")
        cx, cy = (o["box"][0] + o["box"][2]) / 2, (o["box"][1] + o["box"][3]) / 2
        fs = med
        o.update(fs=round(fs, 2), x=round(cx - (l + r) / 2 * fs / 1000, 1), y=round(cy - (t + b) / 2 * fs / 1000, 1), fixed=True)
        fixed += 1
print("大きさを揃えた語", fixed)
json.dump(out, open(f"{g.w}/proj/src/caps.json", "w"), indent=1, ensure_ascii=False)
sxs = np.array([o["sx"] for o in out])
print(len(out), "語・横の伸びの中央値", round(float(np.median(sxs)), 3), "（serif",
      round(float(np.median([o['sx'] for o in out if o['kind'] == 'serif'])), 3), "sans",
      round(float(np.median([o['sx'] for o in out if o['kind'] == 'sans'])), 3), "）")
print("大きさの中央値", round(float(np.median([o["fs"] for o in out])), 1))
