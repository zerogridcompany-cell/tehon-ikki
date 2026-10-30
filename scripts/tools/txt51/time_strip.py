"""time_strip.py  字の箱の所を 手本（上）・うち（下）でコマごとに並べた1枚（目で出る・消える・ぼけを見る）。

使い方：python3 time_strip.py <うちの mp4> <id> <f0> <f1> [--step 1] --work <作業>
入れる物：手本・うちの mp4・字の表・字だけの層（箱を決める）
出す物：<out>/reg/strip_<id>.jpg（8コマで1段・左上にコマ番号）
効いた数字（51）：char_time・txt_time の数字を目で確かめる係（打ち字 10/11 が ±1コマの確かめ）
"""
import os, sys
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U
ap = U.base_args(__doc__); ap.add_argument('ours'); ap.add_argument('id'); ap.add_argument('f0', type=int); ap.add_argument('f1', type=int); ap.add_argument('--step', type=int, default=1)
a = U.resolve(ap.parse_args())
k = [d['id'] for d in a.T].index(a.id); A = U.sheet_alpha(a.sheet, k)
if A is None: sys.exit('字だけの層が無い')
x0, y0, x1, y1 = U.ebox(A, int(round(30 * a.K)), a.W, a.H); w, h = x1 - x0, y1 - y0; n = a.f1 - a.f0 + 1
R = U.clip(a.ref, a.f0, n, x0, y0, w, h, a.fps).astype(np.uint8); O = U.clip(a.ours, a.f0, n, x0, y0, w, h, a.fps).astype(np.uint8)
tw = 240; th = max(1, int(h * tw / w)); cols = []
for i in range(0, min(len(R), len(O)), a.step):
    c = np.vstack([cv2.resize(R[i], (tw, th)), cv2.resize(O[i], (tw, th))])
    cv2.putText(c, str(a.f0 + i), (3, 14), 0, 0.45, (255, 0, 255), 1); cols.append(c)
rows = [np.hstack(cols[j:j + 8] + [np.zeros_like(cols[0])] * (8 - len(cols[j:j + 8]))) for j in range(0, len(cols), 8)]
os.makedirs(f'{a.out}/reg', exist_ok=True); p = f'{a.out}/reg/strip_{a.id}.jpg'
cv2.imwrite(p, np.vstack(rows)); print(p)
