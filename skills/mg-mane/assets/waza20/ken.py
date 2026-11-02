#!/usr/bin/env python3
"""20 の技の検品の一覧（mg-mane assets/waza20）。
python3 ken.py <All20.mp4> <出す所> [--step 15] [--detail 3] [--only 1,5]
- <出す所>/ken.jpg ＝ 20 行。1行＝左に手本の keys.jpg（6コマ）・右にうちの All20 を step コマおき（1つ 75 コマ → 0・15・30・45・60）
- <出す所>/ken_NN.jpg ＝ 1つずつの細かい一覧：上の段＝手本の clip を detail コマおき・下の段＝うちを同じコマ番号で（＋75 コマまでの残り）
- 絵の左上＝コマ番号（手本は clip の頭からのコマ・うちは技の頭からのコマ）
"""
import argparse, json, os
import numpy as np, cv2
W20 = os.environ.get("WAZA20_TEHON") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "tehon")   # 手本の札（clip.mp4・keys.jpg）＝このスキルの中に写した物（元 ~/research/tehon-me/手本M/waza20）
ap = argparse.ArgumentParser(); ap.add_argument("mp4"); ap.add_argument("out")
ap.add_argument("--step", type=int, default=15); ap.add_argument("--detail", type=int, default=3); ap.add_argument("--only", default="")
ap.add_argument("--sec", type=int, default=75)
A = ap.parse_args(); os.makedirs(A.out, exist_ok=True)
idx = json.load(open(os.path.join(W20, "index.json")))
only = {int(x) for x in A.only.split(",") if x.strip()}
cap = cv2.VideoCapture(A.mp4); ours = []
while True:
    ok, fr = cap.read()
    if not ok: break
    ours.append(cv2.resize(fr, (270, 480), interpolation=cv2.INTER_AREA))
print("うちのコマ数", len(ours))
def lab(im, t, col=(0, 255, 255), sc=0.8):
    cv2.putText(im, t, (6, 26), cv2.FONT_HERSHEY_SIMPLEX, sc, (0, 0, 0), 4); cv2.putText(im, t, (6, 26), cv2.FONT_HERSHEY_SIMPLEX, sc, col, 2); return im
rows = []
for it in idx:
    n = it["n"]; d = os.path.join(W20, os.path.basename(it["dir"]))
    keys = cv2.imread(os.path.join(d, "keys.jpg"))
    base = (n - 1) * A.sec
    ou = [lab(ours[base + k].copy(), f"u{k}") for k in range(0, A.sec, A.step) if base + k < len(ours)]
    name = np.full((480, 260, 3), 24, np.uint8); lab(name, f"{n:02d}", (80, 200, 255), 1.4)
    cv2.putText(name, it["name"][:14], (8, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    gap = np.full((480, 20, 3), 0, np.uint8)
    rows.append(np.hstack([name, keys, gap] + sum([[o, np.full((480, 6, 3), 0, np.uint8)] for o in ou], [])[:-1]))
    if only and n not in only: continue
    # 細かい一覧
    cp = cv2.VideoCapture(os.path.join(d, "clip.mp4")); cl = []
    while True:
        ok, fr = cp.read()
        if not ok: break
        cl.append(cv2.resize(fr, (205, 240), interpolation=cv2.INTER_AREA))
    ks = list(range(0, len(cl), A.detail)); top = [lab(cl[k].copy(), str(k), sc=0.6) for k in ks]
    bot = [lab(cv2.resize(ours[base + k], (135, 240), interpolation=cv2.INTER_AREA), f"u{k}", sc=0.6) for k in range(0, A.sec, A.detail) if base + k < len(ours)]
    per = 13
    def band(ims, w):
        out = []
        for s in range(0, len(ims), per):
            seg = ims[s:s + per] + [np.full((240, w, 3), 20, np.uint8)] * (per - len(ims[s:s + per]))
            out.append(np.hstack(sum([[x, np.full((240, 4, 3), 20, np.uint8)] for x in seg], [])[:-1]))
        return out
    tb, bb = band(top, 205), band(bot, 135)
    Wd = max(x.shape[1] for x in tb + bb)
    pad = lambda x: np.hstack([x, np.full((x.shape[0], Wd - x.shape[1], 3), 20, np.uint8)]) if x.shape[1] < Wd else x
    sheet = np.vstack(sum([[pad(x), np.full((6, Wd, 3), 60, np.uint8)] for x in tb], []) + [np.full((10, Wd, 3), 200, np.uint8)] + sum([[pad(x), np.full((6, Wd, 3), 60, np.uint8)] for x in bb], []))
    cv2.imwrite(os.path.join(A.out, f"ken_{n:02d}.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 85])
Wm = max(r.shape[1] for r in rows)
big = np.vstack(sum([[np.hstack([r, np.zeros((480, Wm - r.shape[1], 3), np.uint8)]) if r.shape[1] < Wm else r, np.full((10, Wm, 3), 90, np.uint8)] for r in rows], [])[:-1])
big = cv2.resize(big, (big.shape[1] // 2, big.shape[0] // 2), interpolation=cv2.INTER_AREA)
cv2.imwrite(os.path.join(A.out, "ken.jpg"), big, [cv2.IMWRITE_JPEG_QUALITY, 82])
for s in range(0, 20, 4):   # 見る用に 4 行ずつ
    part = big[s * 245: (s + 4) * 245]
    cv2.imwrite(os.path.join(A.out, f"ken_rows{s + 1:02d}-{s + 4:02d}.jpg"), part, [cv2.IMWRITE_JPEG_QUALITY, 85])
print("出した:", A.out)
