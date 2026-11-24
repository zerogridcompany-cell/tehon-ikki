# 線の太さと光のにじみ（暗い場面の白い線）：芯（明るさ>200・彩度小）の太さ px と、芯からの距離ごとの明るさ（背景を引いた値÷芯）
# 使い方: python3 sen_futosa.py <動画> <秒,秒,…>   → 太さの中央値・距離 1..16px の明るさの割合
import cv2, sys, numpy as np
from skimage.morphology import skeletonize
v = sys.argv[1]; ts = [float(x) for x in sys.argv[2].split(',')]; cap = cv2.VideoCapture(v)
W, P = [], []
for t in ts:
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000); ok, im = cap.read()
    if not ok: continue
    hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV); g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float32)
    core = ((g > 190) & (hsv[:, :, 1] < 60)).astype(np.uint8); core[:200] = 0
    if core.sum() < 500: continue
    n, lab, st, _ = cv2.connectedComponentsWithStats(core); keep = np.zeros_like(core)
    for i in range(1, n):
        if st[i, 4] > 80: keep[lab == i] = 1
    dt = cv2.distanceTransform(keep, cv2.DIST_L2, 5); sk = skeletonize(keep > 0)
    w = dt[sk] * 2; w = w[(w > 1) & (w < 14)]; W += list(w)
    out = cv2.distanceTransform((1 - keep).astype(np.uint8), cv2.DIST_L2, 5)
    bgv = np.median(g[out > 40]) if (out > 40).sum() > 100 else 8; cv = np.mean(g[keep > 0]) - bgv
    P.append([(np.mean(g[(out > d - 0.5) & (out <= d + 0.5)]) - bgv) / cv for d in range(1, 17)])
print(f'線の芯の太さ 中央 {np.median(W):.1f}px（四分位 {np.percentile(W,25):.1f}–{np.percentile(W,75):.1f}）')
print('にじみ（芯からの距離 px: 明るさの割合）', ' '.join(f'{d}:{x:.2f}' for d, x in zip(range(1, 17), np.mean(P, 0))))
