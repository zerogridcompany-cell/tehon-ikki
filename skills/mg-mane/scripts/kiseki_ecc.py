#!/usr/bin/env python3
"""mg-mane の「カメラを基準のコマへ直接重ねる」（ECC・相似）。窓や札が画面の外へ出て縁が取れん寄りでも、ずれが積もらん（exp1 手本F v3）。

/usr/bin/python3 kiseki_ecc.py <手本.mp4> --base B --from F0 --to F1 --roi x0,y0,x1,y1 --out <json> [--w 960]
  --roi は基準のコマ B の面（重ねに使う所）。前のコマの答えから始めて、各コマ t の A(2x3)＝基準の点 p → t の点（手本の画素）を出す
  使い方：基準のコマで縁が全部見える箱（kiseki --mode edge）を A で写す＝各コマの箱。exp1 の 372〜460 で見える左の縁と 1〜2px で一致
  流れをつないだカメラ（kiseki flow の拡大を積む）は速い寄りで 2 コマに 5% ずれた
"""
import sys, json, argparse, numpy as np, cv2
ap = argparse.ArgumentParser()
ap.add_argument('video'); ap.add_argument('--base', type=int, required=True); ap.add_argument('--from', dest='f0', type=int); ap.add_argument('--to', dest='f1', type=int)
ap.add_argument('--roi', required=True, help='基準のコマの面 x0,y0,x1,y1'); ap.add_argument('--w', type=int, default=960); ap.add_argument('--out', required=True)
ap.add_argument('--model', default='similarity'); ap.add_argument('--init', default=None, help='最初の推定 a,b,tx,ty（a=s cos, b=s sin）')
a = ap.parse_args()
cap = cv2.VideoCapture(a.video); F = {}; i = 0; lo, hi = min(a.base, a.f0), max(a.base, a.f1)
while True:
    ok, fr = cap.read()
    if not ok or i > hi: break
    if i >= lo: F[i] = fr
    i += 1
W = F[a.base].shape[1]; k = a.w / W
def prep(im):
    g = cv2.cvtColor(cv2.resize(im, (a.w, int(round(im.shape[0] * k))), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
    return cv2.GaussianBlur(g, (5, 5), 1.0)
B = prep(F[a.base]); x0, y0, x1, y1 = [float(v) * k for v in a.roi.split(',')]
mask = np.zeros(B.shape, np.uint8); mask[int(y0):int(y1), int(x0):int(x1)] = 255
mode = cv2.MOTION_AFFINE if a.model == 'affine' else cv2.MOTION_EUCLIDEAN
rows = []
def run(order):
    M = np.eye(2, 3, dtype=np.float32)
    if a.init:
        aa, bb, tx, ty = [float(v) for v in a.init.split(',')]; M = np.array([[aa, -bb, tx * k], [bb, aa, ty * k]], np.float32)
    res = {}
    for f in order:
        T = prep(F[f])
        # 相似：拡大を含む＝AFFINE で解いてから相似に寄せる（EUCLIDEAN は拡大を持たん）
        try:
            cc, M2 = cv2.findTransformECC(B, T, M.copy(), cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), mask, 5)
        except cv2.error:
            cc, M2 = -1, M.copy()
        if a.model == 'similarity':
            A2 = M2[:, :2]; s = np.sqrt(abs(np.linalg.det(A2))); th = np.arctan2(A2[1, 0] - A2[0, 1], A2[0, 0] + A2[1, 1])
            M2 = np.array([[s * np.cos(th), -s * np.sin(th), M2[0, 2]], [s * np.sin(th), s * np.cos(th), M2[1, 2]]], np.float32)
        M = M2
        A = M.astype(float).copy(); A[:, 2] /= k  # 手本の画素へ（拡大と回りは同じ）
        res[f] = dict(f=f, cc=round(float(cc), 5), A=[[round(v, 6) for v in A[0]], [round(v, 6) for v in A[1]]],
                      s=round(float(np.sqrt(abs(np.linalg.det(A[:, :2])))), 6), rot=round(float(np.degrees(np.arctan2(A[1, 0], A[0, 0]))), 4))
    return res
fw = run(range(a.base, a.f1 + 1)) if a.f1 >= a.base else {}
bw = run(range(a.base, a.f0 - 1, -1)) if a.f0 < a.base else {}
allr = {**bw, **fw}
json.dump(dict(video=a.video, base=a.base, roi=a.roi, frames=[allr[f] for f in sorted(allr)]), open(a.out, 'w'))
print('done', len(allr), 'min cc', min(r['cc'] for r in allr.values()))
