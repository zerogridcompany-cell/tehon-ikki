"""ero_fit.py  溶けて削れる消え方（exit 'erode'）の進みの表 erop を、手本の「字の色が残っとる割合」に寄せる（51 再開4回目）。

何をする：字の型の中で「字の色と地の色のどちらに近いか」で残りの割合を毎コマ出す（元 51/tools/keep_curve.py を中に入れた）。
  基準＝削れ始めの直前3コマの平均（地の物が動いても狂わん）。較正の表（残りの割合→erop の値・Txt51.tsx の erode フィルタで測った物）で
  手本の割合を erop に直し、うちの割合との差を今の表に足す。止めコマの表（--hold・コマ f の見た目は hold[f] で決まる）があれば hold[f] に入れる。
使い方：python3 ero_fit.py <うちの mp4> id:削れ始め:終わり[,id:a:b …] --work <作業> [--init] [--hold <hold.json>] [--dry]
  --init：較正の表だけで作る（うちの今の値を使わん・最初の1回）／--curve：残りの割合を出すだけ（手本とうち）
入れる物：手本・うちの mp4・字の表・字だけの層
出す物：字の表の erop（[[コマ, 進み], …]・単調に増やす）と exit='erode'
効いた数字（51）：4つの消え方（chasing・ourlives・uses・moneydot）で手本との差 平均 0.02〜0.05
落とし穴：🔴 割合の基準を「最初のコマ」にすると狂う（v78 を捨てた）＝直前3コマの平均。コマはちょうど f から読む（(f−0.5)/fps）
"""
import os, sys, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U
ap = U.base_args(__doc__); ap.add_argument('ours'); ap.add_argument('wins')
ap.add_argument('--init', action='store_true'); ap.add_argument('--hold', default=None); ap.add_argument('--dry', action='store_true'); ap.add_argument('--curve', action='store_true')
a = U.resolve(ap.parse_args())
CAL = [(1.0, 0.2), (0.97, 0.24), (0.60, 0.32), (0.37, 0.48), (0.28, 0.56), (0.20, 0.64), (0.13, 0.72), (0.07, 0.80), (0.04, 0.88), (0.02, 0.96), (0.0, 1.04)]
KK = np.array([c[0] for c in CAL][::-1]); EE = np.array([c[1] for c in CAL][::-1]); k2e = lambda k: float(np.interp(k, KK, EE)) if k < 0.995 else 0.0
HOLD = json.load(open(a.hold)) if a.hold else None
IDX = {d['id']: k for k, d in enumerate(a.T)}

def curve(src, tid, f0, f1):
    """字の型の中で字の色が残っとる割合（コマ f0 のまま＝1 にはまだ割らん）→ {コマ: 割合}"""
    A = U.sheet_alpha(a.sheet, IDX[tid]) > 0.5
    x0, y0, x1, y1 = U.ebox(A.astype(np.float32), int(round(24 * a.K)), a.W, a.H)
    aa = A[y0:y1, x0:x1].astype(np.uint8); M = cv2.erode(aa, np.ones((5, 5), np.uint8)) > 0
    F = U.clip(src, f0, f1 - f0 + 1, x0, y0, x1 - x0, y1 - y0, a.fps)
    col = np.median(F[0][M], 0); bg = np.median(F[0][~(cv2.dilate(aa, np.ones((15, 15), np.uint8)) > 0)], 0)
    out = {}
    for i, f in enumerate(F):
        px = f[M]; out[f0 + i] = float((((px - col) ** 2).sum(1) < ((px - bg) ** 2).sum(1)).mean())
    return out

for w in a.wins.split(','):
    tid, s0, s1 = w.split(':'); A0, B0 = int(s0), int(s1); d = a.T[IDX[tid]]
    R = curve(a.ref, tid, A0 - 6, B0); r0 = np.mean([R[A0 - 3], R[A0 - 2], R[A0 - 1]]) or 1; R = {f: v / r0 for f, v in R.items()}
    O = curve(a.ours, tid, A0 - 6, B0); o0 = np.mean([O[A0 - 3], O[A0 - 2], O[A0 - 1]]) or 1; O = {f: v / o0 for f, v in O.items()}
    print(tid, 'err', round(np.mean([abs(R[f] - O[f]) for f in range(A0, B0 + 1)]), 3), 'ref', [round(R[f], 2) for f in range(A0, B0 + 1)], 'ours', [round(O[f], 2) for f in range(A0, B0 + 1)])
    if a.curve: continue
    cur = {f: e for f, e in d.get('erop', [])}
    def ep_at(f):
        ks = sorted(cur)
        if not ks: return 0
        if f <= ks[0]: return cur[ks[0]]
        for i in range(1, len(ks)):
            if f < ks[i]: return cur[ks[i - 1]] + (cur[ks[i]] - cur[ks[i - 1]]) * (f - ks[i - 1]) / (ks[i] - ks[i - 1])
        return cur[ks[-1]]
    new = {}
    for f in range(A0, B0 + 1):
        h = HOLD[f] if HOLD and f < len(HOLD) else f
        e = k2e(R[f]) if a.init else (max(0.0, min(1.2, ep_at(h) + k2e(R[f]) - k2e(O[f]))) if R[f] < 0.995 else ep_at(h))
        new.setdefault(h, []).append(e)
    tab = [[A0 - 1, 0.0]] + [[h, round(float(np.mean(v)), 3)] for h, v in sorted(new.items())]
    m = 0
    for p in tab: m = max(m, p[1]); p[1] = m
    d['erop'] = tab; d['exit'] = 'erode'
if not a.dry and not a.curve: U.save_texts(a.texts, a.T, a.fmt, a.fps)
