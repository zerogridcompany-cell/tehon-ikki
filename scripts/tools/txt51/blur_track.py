"""blur_track.py  字のぼけと濃さを毎コマ測る（51 再開4回目・ぼけの段の表）。

何をする：字の型を σ でぼかして a·型＋b で手本（の明るさ）に最小二乗で当て、毎コマの ぼけ σ(px)・濃さ a を出す。
  --split 0.3＝型の左 30% と残りで濃さを別に当てる（1字目だけ先に出るか）
使い方：python3 blur_track.py <id> <f0> <f1> --work <作業> [--src <mp4>（既定＝手本）] [--split 0.3]
入れる物：手本（か うち）の mp4・字の表・字だけの層
出す物：<out>/reg/blur_<id>_<mp4の名前>.json＝[[コマ, σ, 濃さ…], …] → 字の表の blurk（[[コマ, σ], …]＝段のまま）・
  blurgain（[[コマ, 明るさの倍], …]＝手本はぼかしても暗くならん＝同じ層を重ねて明るく）・words＋cfade（1字ずつぱっと）に写す（Txt51.tsx が描く）
効いた数字（51）：for の σ が全コマ一致・濃さ 2% 以内
"""
import os, sys, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U
ap = U.base_args(__doc__); ap.add_argument('id'); ap.add_argument('f0', type=int); ap.add_argument('f1', type=int)
ap.add_argument('--src', default=None); ap.add_argument('--split', type=float, default=None)
a = U.resolve(ap.parse_args()); src = a.src or a.ref
k = [d['id'] for d in a.T].index(a.id); A = U.sheet_alpha(a.sheet, k)
if A is None: sys.exit('字だけの層が無い')
x0, y0, x1, y1 = U.ebox(A, int(round(60 * a.K)), a.W, a.H); w, h = x1 - x0, y1 - y0; n = a.f1 - a.f0 + 1
F = U.clip(src, a.f0, n, x0, y0, w, h, a.fps, gray=True)
aa = A[y0:y1, x0:x1]
cs = np.where((aa > 0.5).any(0))[0]; cut = cs[0] + int((cs[-1] - cs[0]) * a.split) if a.split is not None else None
SIG = [v * a.K for v in [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 26, 30, 35, 40, 50]]
out = []
for i, g in enumerate(F):
    best = None
    for s in SIG:
        tb = cv2.GaussianBlur(aa, (0, 0), s) if s > 0 else aa
        if cut is not None:
            t1 = tb.copy(); t1[:, :cut] = 0; t0 = tb.copy(); t0[:, cut:] = 0
            X = np.stack([t0.ravel(), t1.ravel(), np.ones(h * w)], 1)
        else:
            X = np.stack([tb.ravel(), np.ones(h * w)], 1)
        c, *_ = np.linalg.lstsq(X, g.ravel(), rcond=None); e = ((X @ c - g.ravel()) ** 2).mean()
        if best is None or e < best[0]: best = (e, s, c)
    e, s, c = best
    out.append([a.f0 + i, round(float(s), 2)] + [round(float(v), 1) for v in c[:-1]])
    print(a.f0 + i, 'σ', round(s, 2), '濃さ', [round(float(v), 1) for v in c[:-1]], '地', round(float(c[-1]), 1), flush=True)
os.makedirs(f'{a.out}/reg', exist_ok=True)
json.dump(out, open(f'{a.out}/reg/blur_{a.id}_{os.path.splitext(os.path.basename(src))[0]}.json', 'w'))
