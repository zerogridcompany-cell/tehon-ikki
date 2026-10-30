"""txt_reg.py  字の位置と大きさを「箱」でなく「形の重ね合わせ」で測る（51 再開4回目）。

何をする：字だけの層（Txt51.tsx の TxtSheet の書き出し・透明の地）を型にして、手本とうちの同じコマ（frame_of）で
  位置 dx,dy と横・縦の倍率 sx,sy を探して当てる。当て方＝明るさの縁（勾配）0.6＋字の色の近さ 0.4 の相関（後ろの白・赤を箱に拾わん）。
  手本の字の色は、1回当ててから型の下の画素の中央値で測り直す。
使い方：python3 txt_reg.py <うちの mp4> <版名> --work <作業> [--sheet <書き出し>] [--srange 0.88,1.121,0.02]
入れる物：手本・うちの mp4・字の表（texts/caps）・字だけの層
出す物：<out>/reg/<版名>.json・.md（字ごとに 手本｜うち｜差。差＝4辺の px・線＝幅の 0.5%・高さの 0.5%）
  need＝{dx,dy,sx,sy}（手本−うち）→ reg_apply.py で字の表へ
先に：うちの動画に自分の型を当てて 0〜1px になる事を確かめる（測りが正しいかの確かめ）
効いた数字（51）：字の位置 17→52/57（＋目で一致 5）・全体 SSIM 0.715→0.727。
落とし穴：ぼけた字は型が小さめに当たる（liefor 毎回 0.85）＝ぼける前のくっきりしたコマで測る。字が引く（拡大）区間は --srange を広げる
"""
import os, sys, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U

def grad(g):
    g = cv2.GaussianBlur(g.astype(np.float32), (0, 0), 1.5)
    return cv2.magnitude(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))

def fit(img, A, col, W, H, pad, srange):
    """A＝字の濃さ 0..1（画面の大きさ）。img＝BGR。→ dict(dx,dy,sx,sy,score,box,tbox,c)。型の箱の真ん中を中心に倍率をかける"""
    ys, xs = np.where(A > 0.5); x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
    win = img[Y0:Y1, X0:X1].astype(np.float32)
    gW = grad(cv2.cvtColor(win.astype(np.uint8), cv2.COLOR_BGR2GRAY))
    cW = np.exp(-((win - col[None, None, :]) ** 2).sum(2) / (2 * 45.0 ** 2))
    tA = A[y0:y1, x0:x1].astype(np.float32); gA = grad(tA * 255)
    best = (-9, 0, 0, 1, 1)
    def tryit(sx, sy):
        w, h = max(8, int(round((x1 - x0) * sx))), max(8, int(round((y1 - y0) * sy)))
        if w >= gW.shape[1] or h >= gW.shape[0]: return None
        ta = cv2.resize(tA, (w, h), interpolation=cv2.INTER_AREA); tg = cv2.resize(gA, (w, h), interpolation=cv2.INTER_AREA)
        r = 0.6 * cv2.matchTemplate(gW, tg, cv2.TM_CCOEFF_NORMED) + 0.4 * cv2.matchTemplate(cW, ta, cv2.TM_CCOEFF_NORMED)
        _, mv, _, ml = cv2.minMaxLoc(r)
        return (mv, X0 + ml[0] + w / 2 - cx, Y0 + ml[1] + h / 2 - cy, w / (x1 - x0), h / (y1 - y0))
    for s in np.arange(*srange):
        r = tryit(s, s)
        if r and r[0] > best[0]: best = r
    s0x, s0y = best[3], best[4]
    for sx in np.arange(s0x - 0.03, s0x + 0.031, 0.006):
        for sy in np.arange(s0y - 0.03, s0y + 0.031, 0.006):
            r = tryit(sx, sy)
            if r and r[0] > best[0]: best = r
    mv, dx, dy, sx, sy = best
    box = [cx + dx - (cx - x0) * sx, cy + dy - (cy - y0) * sy, cx + dx + (x1 - cx) * sx, cy + dy + (y1 - cy) * sy]
    return dict(dx=round(float(dx), 1), dy=round(float(dy), 1), sx=round(float(sx), 4), sy=round(float(sy), 4), score=round(float(mv), 3),
                box=[round(float(v), 1) for v in box], tbox=[int(x0), int(y0), int(x1), int(y1)], c=[float(cx), float(cy)])

def main():
    ap = U.base_args(__doc__); ap.add_argument('ours'); ap.add_argument('ver')
    ap.add_argument('--srange', default='0.88,1.121,0.02', help='倍率を探す幅（字が引く区間は広げる）')
    a = U.resolve(ap.parse_args()); W, H, K = a.W, a.H, a.K
    SR = tuple(float(v) for v in a.srange.split(',')); PAD = int(round(90 * K)); LX, LY = 0.005 * W, 0.005 * H
    rows = []
    for k, d in enumerate(a.T):
        if a.idset and d['id'] not in a.idset: continue
        A = U.sheet_alpha(a.sheet, k)
        if A is None: rows.append(dict(id=d['id'], err='型が空')); continue
        f = U.frame_of(d, a.fps); R = U.grab(a.ref, f, a.fps, f'{a.out}/frames/ref'); O = U.grab(a.ours, f, a.fps, f'{a.out}/frames/{a.ver}')
        col = U.hexbgr(d.get('color', '#ffffff'))
        o = fit(O, A, col, W, H, PAD, SR); r = fit(R, A, col, W, H, PAD, SR)
        sh = np.float32([[r['sx'], 0, r['c'][0] + r['dx'] - r['c'][0] * r['sx']], [0, r['sy'], r['c'][1] + r['dy'] - r['c'][1] * r['sy']]])
        M = cv2.warpAffine(A, sh, (W, H)); px = R[M > 0.6]
        if len(px) > 50:   # 手本の字の色を型の下で測り直して当て直す
            r = fit(R, A, np.median(px, 0).astype(np.float32), W, H, PAD, SR); o = fit(O, A, np.median(O[A > 0.6], 0).astype(np.float32), W, H, PAD, SR)
        dl = [round(r['box'][i] - o['box'][i], 1) for i in range(4)]
        ok = abs(dl[0]) <= LX and abs(dl[2]) <= LX and abs(dl[1]) <= LY and abs(dl[3]) <= LY
        rows.append(dict(id=d['id'], frame=f, ref=r, ours=o, d=dl, ok=ok,
                         need=dict(dx=round(r['dx'] - o['dx'], 1), dy=round(r['dy'] - o['dy'], 1), sx=round(r['sx'] / o['sx'], 4), sy=round(r['sy'] / o['sy'], 4))))
        print(d['id'], f, 'ref', r['dx'], r['dy'], r['sx'], r['sy'], r['score'], '| ours', o['dx'], o['dy'], o['sx'], o['sy'], o['score'], '| d', dl, '✅' if ok else '🔴', flush=True)
    od = f'{a.out}/reg'; os.makedirs(od, exist_ok=True)
    json.dump(rows, open(f'{od}/{a.ver}.json', 'w'), ensure_ascii=False, indent=1)
    n_ok = sum(1 for r in rows if r.get('ok'))
    L = [f'# 字の形の重ね合わせ（{a.ver}）＝ 4辺が 横 {LX:.1f}px・縦 {LY:.1f}px 以内：{n_ok}/{len(rows)}', '',
         '| id | コマ | 手本 dx,dy | 手本 sx,sy | 手本の点 | うち dx,dy | うち sx,sy | うちの点 | 差 左,上,右,下 px | 判定 |', '|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        if 'err' in r: L.append(f"| {r['id']} | | | | | | | | {r['err']} | 🔴 |"); continue
        x, o = r['ref'], r['ours']
        L.append(f"| {r['id']} | {r['frame']} | {x['dx']:+.1f},{x['dy']:+.1f} | {x['sx']:.3f},{x['sy']:.3f} | {x['score']} | {o['dx']:+.1f},{o['dy']:+.1f} | {o['sx']:.3f},{o['sy']:.3f} | {o['score']} | {','.join(f'{v:+.0f}' for v in r['d'])} | {'✅' if r['ok'] else '🔴'} |")
    open(f'{od}/{a.ver}.md', 'w').write('\n'.join(L) + '\n')
    print('OK', n_ok, len(rows), '→', f'{od}/{a.ver}.md')

if __name__ == '__main__':
    main()
