#!/usr/bin/env python3
"""検品の一覧（mg-mane references/kenpin.md）：手本を上の段・うちを下の段に、同じコマを6コマおきに並べた jpg。

/usr/bin/python3 ken.py <手本.mp4> <うち.mp4> <出す所> [--step 6] [--per 6] [--bands 4] [--from コマ] [--to コマ]
- 1枚＝bands 本の帯。帯1本＝上の段に手本 per 枚・下の段にうち per 枚（同じコマ番号が縦に並ぶ）
- 絵の左上＝コマ番号。うちの絵の左下＝そのコマの SSIM。0.85 未満は赤い枠＝先に見る所（全部見るのは変わらん）
- 出す物＝<出す所>/k00.jpg, k01.jpg …・最後に枚数と赤い枠のコマを出す
- 🔴の区間を全コマで見る時＝--from 186 --to 240 --step 1 --per 8
"""
import argparse, os
import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim_fn

ap = argparse.ArgumentParser(); ap.add_argument("ref"); ap.add_argument("ours"); ap.add_argument("out")
ap.add_argument("--step", type=int, default=6); ap.add_argument("--per", type=int, default=6); ap.add_argument("--bands", type=int, default=4)
ap.add_argument("--from", dest="f0", type=int, default=0); ap.add_argument("--to", dest="f1", type=int, default=10 ** 9)
A = ap.parse_args(); os.makedirs(A.out, exist_ok=True)
ca, cb = cv2.VideoCapture(A.ref), cv2.VideoCapture(A.ours)
W, H = int(ca.get(cv2.CAP_PROP_FRAME_WIDTH)), int(ca.get(cv2.CAP_PROP_FRAME_HEIGHT))
tw = 320 if W >= H else 180; th = int(round(tw * H / W / 2)) * 2
GAP, BAND_GAP, BG = 4, 14, (40, 40, 40)


def thumb(f, label, sub=None, red=False):
    t = cv2.resize(f, (tw, th), interpolation=cv2.INTER_AREA)
    cv2.putText(t, label, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3); cv2.putText(t, label, (5, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    if sub:
        cv2.putText(t, sub, (5, th - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3); cv2.putText(t, sub, (5, th - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    if red: cv2.rectangle(t, (0, 0), (tw - 1, th - 1), (0, 0, 255), 4)
    return t


pairs = []; i = 0
while True:
    oka, fa = ca.read(); okb, fb = cb.read()
    if not oka or not okb: break
    if A.f0 <= i <= A.f1 and (i - A.f0) % A.step == 0:
        ga = cv2.cvtColor(cv2.resize(fa, (tw, th), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        gb = cv2.cvtColor(cv2.resize(fb, (tw, th), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        s = float(ssim_fn(ga, gb)); pairs.append((i, thumb(fa, str(i)), thumb(fb, f"u{i}", f"s{s:.2f}", s < 0.85), s))
    i += 1
    if i > A.f1: break

blank = np.full((th, tw, 3), BG, np.uint8)
rowW = A.per * tw + (A.per - 1) * GAP
bands = [pairs[k:k + A.per] for k in range(0, len(pairs), A.per)]
pages = [bands[k:k + A.bands] for k in range(0, len(bands), A.bands)]
for pn, pg in enumerate(pages):
    out = []
    for bd in pg:
        top = [p[1] for p in bd] + [blank] * (A.per - len(bd)); bot = [p[2] for p in bd] + [blank] * (A.per - len(bd))
        sep = np.full((th, GAP, 3), BG, np.uint8)
        rt = np.hstack(sum([[t, sep] for t in top], [])[:-1]); rb = np.hstack(sum([[t, sep] for t in bot], [])[:-1])
        out += [rt, np.full((GAP, rowW, 3), BG, np.uint8), rb, np.full((BAND_GAP, rowW, 3), (0, 0, 0), np.uint8)]
    cv2.imwrite(os.path.join(A.out, f"k{pn:02d}.jpg"), np.vstack(out[:-1]), [cv2.IMWRITE_JPEG_QUALITY, 88])
red = [p[0] for p in pairs if p[3] < 0.85]
print(f"コマ {A.f0}〜{min(i, A.f1 + 1) - 1}・並べた {len(pairs)}（{A.step}コマおき）・{len(pages)} 枚 → {A.out}/k00.jpg …")
print(f"赤い枠（SSIM 0.85 未満）{len(red)}：{'・'.join(map(str, red)) or 'なし'}")
