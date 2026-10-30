"""手本に網点（細かい点の模様）がかかっとるのに、うちに無いカットを探す（10/28 r2：44・46・47 に 2.67px の網点・72 と同じ型）。
python3 ht_scan.py <作業> <うちの書き出し.mp4> [--period 2.67]
- カットの真ん中のコマの左上 512x256 の周波数で、その周期の山の強さ（中央値との比）を手本とうちで比べる
- 手本 >40 かつ うちの3倍以上＝網点が足りん。足し方＝72・46 の型（tmp/b72_S.npy：0.985+1.008×S を σ1.5 のぼかしに掛ける）。層だけのカットは Remotion の filter#ht（R2.tsx・ht.json）
"""
import argparse, glob, os
import cv2, numpy as np
FPS = 29.97
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("out"); ap.add_argument("--period", type=float, default=2.67)
a = ap.parse_args(); w = os.path.abspath(a.w)


def power(cap, n):
    cap.set(1, n); ok, f = cap.read()
    if not ok: return 0.0
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)[40:296, 64:576]
    F = np.abs(np.fft.fft2(g - g.mean())); h, ww = F.shape; fx, fy = int(round(ww / a.period)), int(round(h / a.period))
    return float(max(F[fy - 1:fy + 2, fx - 1:fx + 2].max(), F[fy - 1:fy + 2, ww - fx - 1:ww - fx + 2].max()) / (np.median(F) + 1e-6))


cr, co = cv2.VideoCapture(glob.glob(f"{w}/ref/*.mp4")[0]), cv2.VideoCapture(os.path.join(w, a.out))
for l in open(f"{w}/eye/segs.txt"):
    c, t = l.strip().split(":"); s0, s1 = map(float, t.split("-")); m = round((s0 + s1) / 2 * FPS)
    r, o = power(cr, m), power(co, m)
    if r > 40 and r > 3 * max(o, 1): print(c, "網点 手本", round(r, 1), "うち", round(o, 1))
