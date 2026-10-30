"""字幕の1語ずつ、書体（候補の中で手本の白い形と一番重なる物）・大きさ・位置を決める。

python3 txt_style.py <作業フォルダ> <書体フォルダ>
- txt/words.json の語ごとに、出揃った後の3コマ（真ん中付近）で手本の白い所（字＋光）を取る
- 候補の書体で同じ語を描き、白い形の外枠にぴったり合わせて IoU を比べる
- 出す物：txt/style.json＝[{w, f0, f1, font, weight, iou, box（白い形の外枠・手本の画素）}]
"""
import argparse, json, os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("fonts")
g = ap.parse_args()
FD = g.fonts
CANDS = [
    ("serif_italic", "InstrumentSerif-Italic.ttf", None),
    ("lora_italic", "Lora-Italic[wght].ttf", [700]),
    ("inter700", "Inter[opsz,wght].ttf", [32, 700]),
    ("inter800", "Inter[opsz,wght].ttf", [32, 800]),
]


def render(word, cand, h=160):
    name, file, axes = cand
    f = ImageFont.truetype(f"{FD}/{file}", h)
    if axes:
        f.set_variation_by_axes(axes)
    l, t, r, b = f.getbbox(word)
    im = Image.new("L", (r - l + 8, b - t + 8), 0)
    ImageDraw.Draw(im).text((4 - l, 4 - t), word, font=f, fill=255)
    a = np.array(im) > 127
    ys, xs = np.nonzero(a)
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def white(im):
    mn, mx = im.min(2).astype(int), im.max(2).astype(int)
    return (mn > 215) & (mx - mn < 45)


W = json.load(open(f"{g.w}/txt/words.json"))
out = []
for x in W:
    word = x["w"]
    f = (x["f0"] + x["f1"]) // 2
    if "box" not in x:  # 読めんかった語（推量）は前の語の箱の右
        x["box"] = [0, 315, 0, 380]
    x0, y0, x1, y1 = map(int, x["box"])
    pad = 10
    ms = []
    for d in (-1, 0, 1):
        p = f"{g.w}/txt/f/{min(x['f1'], max(x['f0'], f + d)) + 1:05d}.jpg"
        im = cv2.imread(p)
        ms.append(white(im[max(0, y0 - pad):y1 + pad, max(0, x0 - pad):x1 + pad]))
    m = np.logical_and.reduce(ms)  # 3コマとも白＝字（動く背景の白を外す）
    ys, xs = np.nonzero(m)
    rec = {"w": word, "f0": x["f0"], "f1": x["f1"], "line": x["line"], "guess": x.get("guess", False)}
    if len(xs) < 30:
        rec.update(font=None, iou=0, box=x["box"]); out.append(rec); continue
    mm = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    bx = [max(0, x0 - pad) + int(xs.min()), max(0, y0 - pad) + int(ys.min()),
          max(0, x0 - pad) + int(xs.max()) + 1, max(0, y0 - pad) + int(ys.max()) + 1]
    best = None
    for c in CANDS:
        r = render(word.rstrip(".?,"), c) if word[-1] in ".?," and False else render(word, c)
        rr = cv2.resize(r.astype(np.uint8), (mm.shape[1], mm.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        k = cv2.dilate(mm.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0  # 光でにじむぶん
        iou = float((rr & k).sum()) / max(1, float((rr | mm).sum()))
        if best is None or iou > best[1]:
            best = (c[0], iou)
    rec.update(font=best[0], iou=round(best[1], 3), box=bx)
    out.append(rec)
json.dump(out, open(f"{g.w}/txt/style.json", "w"), indent=1, ensure_ascii=False)
from collections import Counter
print(Counter(r["font"] for r in out))
print("IoU の中央値", np.median([r["iou"] for r in out if r["font"]]))
for r in out[:30]:
    print(r["w"], r["font"], r["iou"])
