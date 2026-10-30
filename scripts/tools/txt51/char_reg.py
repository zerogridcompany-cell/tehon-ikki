"""char_reg.py  字を「1字ずつ」手本に当てる（51 再開5回目）。

何をする：txt_reg・glyph_match は語を1つの倍率とずれで当てる＝字の間（字ごとの送り）の違いが残る（左が合って右へずれる）。
  字だけの層の型を1字ずつの塊に分け、1字ごとに ±S px（既定 14×高さ/1080）を探して手本の字の色のマスク（RGB 距離 70 以内）と一番重なる dx,dy を出す。
  手本のマスクは「その字に一番近い所」だけ（距離の地図で分ける＝隣の字・地を拾わん）。
  語ごとに dx を字の中心 x の直線 a＋b·x に当てる：a＝語のずれ・b＝幅の倍率の違い・残り＝字ごとの送り。
使い方：python3 char_reg.py <うちの mp4> <版名> --work <作業> [--sheet <書き出し>] [--ids a,b]
入れる物：手本の mp4（うちの mp4 は名前の控えだけ・測るのは手本と型）・字の表・字だけの層（今の版で書き出した物）
出す物：<out>/r5/char_<版名>.json・.md → char_apply.py で字の表の cdx（字ごとの送り）へ
効いた数字（51）：字の形 IoU 平均 0.766→0.780・28語（trip 0.74→0.81・costs 0.76→0.82）
"""
import os, sys, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U

def iou(a, b):
    u = (a | b).sum(); return (a & b).sum() / u if u else 0

def main():
    ap = U.base_args(__doc__); ap.add_argument('ours'); ap.add_argument('ver')
    a = U.resolve(ap.parse_args()); K = a.K
    S = max(4, int(round(14 * K))); P = int(round(40 * K))
    res = []; md = [f'## 1字ずつの当て（{a.ver}）', '', '| id | 字の数 | 語のずれ a px | 幅の違い b（‰） | 残りの最大 px | 1字ずつ当てた後の IoU（前→後） | 字ごとの残り px |', '|---|---|---|---|---|---|---|']
    for k, d in enumerate(a.T):
        if a.idset and d['id'] not in a.idset: continue
        A0 = U.sheet_alpha(a.sheet, k)
        if A0 is None: continue
        A = A0 > 0.5
        f = U.frame_of(d, a.fps); R = U.grab(a.ref, f, a.fps, f'{a.out}/frames/ref')
        col = U.hexbgr(d.get('color', '#ffffff'))
        X0, Y0, X1, Y1 = U.ebox(A0, P, a.W, a.H)
        aa = A[Y0:Y1, X0:X1]; G = U.glyphs(aa)
        mr = (np.linalg.norm(R[Y0:Y1, X0:X1].astype(np.float32) - col, axis=2) < 70)
        mr = cv2.morphologyEx(mr.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8)) > 0
        D = np.stack([cv2.distanceTransform((~g).astype(np.uint8), cv2.DIST_L2, 3) for g in G])
        own = D.argmin(0); near = D.min(0) <= S + 4
        rows = []
        for i, g in enumerate(G):
            gy, gx = np.where(g); cx = gx.mean() + X0
            y0, y1, x0, x1 = max(0, gy.min() - S - 4), gy.max() + S + 5, max(0, gx.min() - S - 4), gx.max() + S + 5
            gc = g[y0:y1, x0:x1]; reg = ((own == i) & near)[y0:y1, x0:x1]; m = mr[y0:y1, x0:x1] & reg
            best = (-1, 0, 0)
            for dy in range(-S, S + 1):
                for dx in range(-S, S + 1):
                    v = iou(np.roll(np.roll(gc, dy, 0), dx, 1) & reg, m)
                    if v > best[0]: best = (v, dx, dy)
            rows.append(dict(i=i, cx=float(cx), w=int(gx.max() - gx.min() + 1), n=int(gc.sum()), iou0=float(iou(gc & reg, m)), iou=float(best[0]), dx=best[1], dy=best[2], refpx=int(m.sum())))
        ok = [r for r in rows if r['refpx'] > 0.4 * r['n'] and r['iou'] > 0.3]
        row = dict(id=d['id'], text=d['text'], f=f, chars=rows, nok=len(ok))
        if len(ok) >= 2:
            x = np.array([r['cx'] for r in ok]); y = np.array([r['dx'] for r in ok], float); w = np.array([r['n'] for r in ok], float)
            X = np.stack([np.ones_like(x), x - x.mean()], 1); Wt = np.sqrt(w)[:, None]
            (a0, b0), *_ = np.linalg.lstsq(X * Wt, y * Wt[:, 0], rcond=None)
            resid = y - X @ [a0, b0]
            row.update(a=float(a0), b=float(b0), xm=float(x.mean()), resid=[float(v) for v in resid], dy=float(np.average([r['dy'] for r in ok], weights=w)))
            i0 = np.average([r['iou0'] for r in ok], weights=w); i1 = np.average([r['iou'] for r in ok], weights=w); row.update(iou0=float(i0), iou1=float(i1))
            md.append(f"| {d['id']} | {len(ok)}/{len(G)} | {a0:+.1f}・縦 {row['dy']:+.1f} | {b0 * 1000:+.1f} | {np.abs(resid).max():.1f} | {i0:.3f}→{i1:.3f} | {' '.join(f'{v:+.0f}' for v in resid)} |")
        else: md.append(f"| {d['id']} | {len(ok)}/{len(G)} | 測れん | | | | |")
        res.append(row); print(md[-1], flush=True)
    os.makedirs(f'{a.out}/r5', exist_ok=True)
    json.dump(res, open(f'{a.out}/r5/char_{a.ver}.json', 'w'), ensure_ascii=False, indent=0)
    open(f'{a.out}/r5/char_{a.ver}.md', 'w').write('\n'.join(md) + '\n')

if __name__ == '__main__':
    main()
