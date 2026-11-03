#!/usr/bin/env python3
"""mg-mane の「軌跡」：手本の中の 1 つの物の道を 1 コマずつ、サブピクセルで測る（滑らかの元の数字）。

/usr/bin/python3 kiseki.py <手本.mp4> --roi x,y,w,h --from F0 --to F1 [--w 960] --out <json>
    [--mode flow|box] [--mask none|bright|dark|orange|white] [--thr 0.25] [--follow 1] [--follow-scale 0]
    [--name 名前] [--jpg <絵.jpg>]
    edge のとき：--obj r,g,b（物の色）[--band 0.2] [--corner x0,y0,x1,y1（地を測る隅）| --bg r,g,b] [--pad 40（追いつく枠の余白）]

枠（roi）は手本の画素（1920x1080 なら 1920 の座標）。--w の幅に縮めて測り、出す数字は手本の画素に戻す。
 flow（既定）＝DIS の光の流れ。枠の中の「動いとる画素」（流れ > thr・模様あり・mask）の
               流れの中央値＝その物の動き（dx,dy）を足して x(t),y(t)。同じ画素に 1 次の式（アフィン）を当てて
               横・縦の大きさの変わり（sx,sy＝流れの発散）と回り（r）。枠は毎コマ物に追いつく（--follow）
 box        ＝mask の画素の箱（0.5〜99.5%）と重心。字や玉のように地と色が違う物。大きさ＝箱の幅・高さ
 edge       ＝縁をサブピクセルで（等倍で読む・--obj r,g,b の物の色）。覆い a=1−|画素−物の色|/|地−物の色|（縁の混ざった画素は
               ちょうど混ざりの割合）を、真ん中の帯（±--band）の各行・各列で外から内へ 0.5 を越える所を線形補間→中央値。
               地の色はコマごとに --corner の隅の中央値（UI に覆われん隅を選ぶ）か --bg で固定。0.1px の細かさで窓・札の「息」が取れる
               （exp1 手本F の窓 169〜204：幅 741→735→778→762 のバネ）。枠は物に追いつく（--follow）
出す物＝json {frames:[{f,x,y,sx,sy,s,r,dx,dy,v,n,roi,(x0,x1,y0,y1,w,h,cx,cy,area)}]}・絵（x,y,大きさ,速さの線＋枠のコマ）
  x,y   ＝始めのコマを 0 にした足し算の道（flow）／箱の中心（box・手本の画素）
  v     ＝そのコマで動いた長さ（手本の画素/コマ）
"""
import argparse, json, os, sys
import numpy as np
import cv2


def read_range(path, f0, f1, w):
    cap = cv2.VideoCapture(path)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    k = w / W; h = int(round(H * k))
    out = {}; i = 0
    while True:
        ok, fr = cap.read()
        if not ok or i > f1:
            break
        if i >= f0:
            out[i] = cv2.resize(fr, (w, h), interpolation=cv2.INTER_AREA)
        i += 1
    cap.release()
    return W, H, k, out


def mask_of(img, kind, roi_gray=None):
    if kind == 'none':
        return np.ones(img.shape[:2], bool)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    if kind == 'bright':
        return g > np.median(g) + 25
    if kind == 'white':
        return g > 200
    if kind == 'dark':
        return g < np.median(g) - 35
    if kind == 'orange':
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        return (hsv[..., 0] >= 3) & (hsv[..., 0] <= 25) & (hsv[..., 1] > 110) & (hsv[..., 2] > 110)
    raise SystemExit(f'mask が分からん：{kind}')


def clip_roi(r, w, h):
    x, y, rw, rh = r
    rw = max(8, min(rw, w)); rh = max(8, min(rh, h))
    x = min(max(0, x), w - rw); y = min(max(0, y), h - rh)
    return [x, y, rw, rh]


def fit_affine(X, Y, U, V):
    """u = a0 + a1 X + a2 Y ; v = b0 + b1 X + b2 Y を 2 周の外れ値はずしで"""
    A = np.stack([np.ones_like(X), X, Y], 1)
    keep = np.ones(len(X), bool)
    for _ in range(3):
        if keep.sum() < 6:
            break
        pa, *_ = np.linalg.lstsq(A[keep], U[keep], rcond=None)
        pb, *_ = np.linalg.lstsq(A[keep], V[keep], rcond=None)
        res = np.hypot(A @ pa - U, A @ pb - V)
        th = max(0.15, 2.5 * np.median(res[keep]))
        keep = res <= th
    return pa, pb


def _cross(prof):
    """外→内の並びで最初に 0.5 を越える所（線形補間・画素の中心が整数）"""
    idx = np.nonzero(prof >= 0.5)[0]
    if len(idx) == 0:
        return None
    j = idx[0]
    if j == 0:
        return 0.0
    p0, p1 = prof[j - 1], prof[j]
    return (j - 1) + (0.5 - p0) / max(p1 - p0, 1e-6)


def edge_main(a):
    """--mode edge：物の縁を等倍のサブピクセルで（x0,x1,y0,y1・中心・幅・高さ）"""
    cap = cv2.VideoCapture(a.video)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if not a.obj:
        raise SystemExit('edge は --obj r,g,b が要る')
    OBJ = np.array([float(v) for v in a.obj.split(',')])[::-1]
    BGF = np.array([float(v) for v in a.bg.split(',')])[::-1] if a.bg else None
    c0 = [int(v) for v in a.corner.split(',')]
    rx, ry, rw, rh = [float(v) for v in a.roi.split(',')]
    box = [rx, ry, rx + rw, ry + rh]
    rows = []; i = 0
    while True:
        ok, fr = cap.read()
        if not ok or i > a.f1:
            break
        if i < a.f0:
            i += 1; continue
        f = fr.astype(np.float32)
        bg = BGF if BGF is not None else np.median(f[c0[1]:c0[3], c0[0]:c0[2]].reshape(-1, 3), 0)
        X0 = int(max(0, np.floor(box[0]))); Y0 = int(max(0, np.floor(box[1]))); X1 = int(min(W, np.ceil(box[2]))); Y1 = int(min(H, np.ceil(box[3])))
        R = f[Y0:Y1, X0:X1]
        D = float(np.linalg.norm(bg - OBJ))
        cov = 1 - np.clip(np.linalg.norm(R - OBJ, axis=2) / max(D, 1e-3), 0, 1)
        ys, xs = np.nonzero(cov > 0.5)
        row = dict(f=i, roi=[X0, Y0, X1 - X0, Y1 - Y0], bg=[round(float(v), 1) for v in bg[::-1]])
        if len(xs) > 50:
            bx0, bx1 = np.percentile(xs, 0.2), np.percentile(xs, 99.8); by0, by1 = np.percentile(ys, 0.2), np.percentile(ys, 99.8)
            hm, wm, hh, ww = (by0 + by1) / 2, (bx0 + bx1) / 2, (by1 - by0) / 2, (bx1 - bx0) / 2
            rr = range(max(0, int(hm - a.band * hh * 2)), min(cov.shape[0], int(hm + a.band * hh * 2) + 1))
            cc = range(max(0, int(wm - a.band * ww * 2)), min(cov.shape[1], int(wm + a.band * ww * 2) + 1))
            L = [v for v in (_cross(cov[r, :]) for r in rr) if v is not None]; Rt = [v for v in (_cross(cov[r, ::-1]) for r in rr) if v is not None]
            T = [v for v in (_cross(cov[:, c]) for c in cc) if v is not None]; B = [v for v in (_cross(cov[::-1, c]) for c in cc) if v is not None]
            if L and Rt and T and B:
                x0 = X0 + float(np.median(L)) + 0.5; x1 = X1 - float(np.median(Rt)) - 0.5
                y0 = Y0 + float(np.median(T)) + 0.5; y1 = Y1 - float(np.median(B)) - 0.5
                row.update(x0=round(x0, 3), x1=round(x1, 3), y0=round(y0, 3), y1=round(y1, 3), cx=round((x0 + x1) / 2, 3), cy=round((y0 + y1) / 2, 3),
                           w=round(x1 - x0, 3), h=round(y1 - y0, 3), x=round((x0 + x1) / 2, 3), y=round((y0 + y1) / 2, 3), area=round(float(cov.sum()), 1),
                           cut=[bool(X0 <= 0 and x0 < 1.5), bool(X1 >= W and x1 > W - 1.5), bool(Y0 <= 0 and y0 < 1.5), bool(Y1 >= H and y1 > H - 1.5)])
                if a.follow:
                    box = [x0 - a.pad, y0 - a.pad, x1 + a.pad, y1 + a.pad]
        rows.append(row)
        i += 1
    cap.release()
    out = dict(video=os.path.abspath(a.video), name=a.name, mode='edge', obj=a.obj, roi0=[float(v) for v in a.roi.split(',')], W=W, H=H, frames=rows)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, 'w'), ensure_ascii=False, indent=0)
    jp = a.jpg or os.path.splitext(a.out)[0] + '.jpg'
    Wd, Hg = 1400, 130; panels = []
    for key, col in (('cx', (80, 200, 255)), ('cy', (255, 160, 60)), ('w', (120, 255, 120)), ('h', (220, 220, 220))):
        g = np.full((Hg, Wd, 3), 28, np.uint8)
        vals = np.array([r.get(key, np.nan) for r in rows], float)
        if np.isfinite(vals).sum() >= 2:
            lo, hi = np.nanmin(vals), np.nanmax(vals); sp = max(hi - lo, 1e-6)
            pts = [(int(8 + k / max(len(vals) - 1, 1) * (Wd - 16)), int(Hg - 10 - (v - lo) / sp * (Hg - 30))) for k, v in enumerate(vals) if np.isfinite(v)]
            cv2.polylines(g, [np.array(pts, np.int32)], False, col, 2, cv2.LINE_AA)
            cv2.putText(g, f'{key}  {lo:.2f} .. {hi:.2f}   {a.name} {a.f0}-{a.f1} edge', (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1, cv2.LINE_AA)
        panels.append(g)
    cv2.imwrite(jp, np.vstack(panels), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(f'{a.name or "kiseki"} {a.f0}-{a.f1} mode=edge → {a.out}（{len(rows)} コマ）・絵 {jp}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('video'); ap.add_argument('--roi', required=True); ap.add_argument('--from', dest='f0', type=int, required=True)
    ap.add_argument('--to', dest='f1', type=int, required=True); ap.add_argument('--w', type=int, default=960)
    ap.add_argument('--out', required=True); ap.add_argument('--mode', default='flow', choices=['flow', 'box', 'edge'])
    ap.add_argument('--mask', default='none'); ap.add_argument('--thr', type=float, default=0.25)
    ap.add_argument('--follow', type=int, default=1); ap.add_argument('--follow-scale', type=int, default=0)
    ap.add_argument('--margin', type=float, default=0.6, help='流れを測る窓＝枠＋枠の大きさ×これ')
    ap.add_argument('--name', default=''); ap.add_argument('--jpg', default=None)
    ap.add_argument('--obj', default=None, help='edge：物の色 r,g,b'); ap.add_argument('--band', type=float, default=0.2)
    ap.add_argument('--corner', default='20,20,60,60', help='edge：地の色を測る隅 x0,y0,x1,y1（手本の画素）'); ap.add_argument('--bg', default=None)
    ap.add_argument('--pad', type=float, default=40, help='edge：追いつく枠＝前のコマの箱＋この余白（手本の画素）')
    a = ap.parse_args()
    if a.mode == 'edge':
        return edge_main(a)
    W, H, k, F = read_range(a.video, a.f0 - 1 if a.mode == 'flow' else a.f0, a.f1, a.w)
    h, w = next(iter(F.values())).shape[:2]
    roi = [float(v) * k for v in a.roi.split(',')]
    G = {f: cv2.GaussianBlur(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (3, 3), 0) for f, im in F.items()}
    rows = []
    x = y = 0.0; sx = sy = 1.0; rot = 0.0
    dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    rois = {}
    for f in range(a.f0, a.f1 + 1):
        r = clip_roi([int(round(v)) for v in roi], w, h); rois[f] = r
        if a.mode == 'box':
            rx, ry, rw, rh = r
            m = mask_of(F[f][ry:ry + rh, rx:rx + rw], a.mask)
            ys, xs = np.nonzero(m)
            row = dict(f=f, roi=[v / k for v in r], n=int(len(xs)))
            if len(xs) >= 6:
                x0, x1 = np.percentile(xs, 0.5), np.percentile(xs, 99.5); y0, y1 = np.percentile(ys, 0.5), np.percentile(ys, 99.5)
                cx, cy = xs.mean(), ys.mean()
                row.update(x0=(rx + x0) / k, x1=(rx + x1) / k, y0=(ry + y0) / k, y1=(ry + y1) / k, w=(x1 - x0) / k, h=(y1 - y0) / k,
                           cx=(rx + cx) / k, cy=(ry + cy) / k, area=float(len(xs)) / k / k)
                row['x'] = (rx + (x0 + x1) / 2) / k; row['y'] = (ry + (y0 + y1) / 2) / k
                if a.follow:
                    roi[0] = rx + (x0 + x1) / 2 - roi[2] / 2; roi[1] = ry + (y0 + y1) / 2 - roi[3] / 2
            rows.append(row)
            continue
        if f == a.f0:
            rows.append(dict(f=f, x=0.0, y=0.0, sx=1.0, sy=1.0, s=1.0, r=0.0, dx=0.0, dy=0.0, v=0.0, n=0, roi=[v / k for v in r]))
            continue
        rx, ry, rw, rh = r
        mg = int(max(rw, rh) * a.margin) + 16
        wx0, wy0 = max(0, rx - mg), max(0, ry - mg); wx1, wy1 = min(w, rx + rw + mg), min(h, ry + rh + mg)
        # 窓の切り出しは連続の配列に（DIS は I0.isContinuous() を求める・幅いっぱいでない窓で落ちた 11/3 jp4）
        g0 = np.ascontiguousarray(G[f - 1][wy0:wy1, wx0:wx1]); g1 = np.ascontiguousarray(G[f][wy0:wy1, wx0:wx1])
        fl = dis.calc(g0, g1, None)
        sub = fl[ry - wy0:ry - wy0 + rh, rx - wx0:rx - wx0 + rw]
        U = sub[..., 0].ravel(); V = sub[..., 1].ravel()
        gx = cv2.Sobel(g0, cv2.CV_32F, 1, 0, ksize=3)[ry - wy0:ry - wy0 + rh, rx - wx0:rx - wx0 + rw]
        gy = cv2.Sobel(g0, cv2.CV_32F, 0, 1, ksize=3)[ry - wy0:ry - wy0 + rh, rx - wx0:rx - wx0 + rw]
        tex = (np.hypot(gx, gy) > 12).ravel()
        mk = mask_of(F[f - 1][ry:ry + rh, rx:rx + rw], a.mask).ravel()
        mov = np.hypot(U, V) > a.thr
        sel = tex & mk & mov
        YY, XX = np.mgrid[0:rh, 0:rw]
        Xc = (XX.ravel() - rw / 2).astype(np.float32); Yc = (YY.ravel() - rh / 2).astype(np.float32)
        n = int(sel.sum())
        if n < 12:
            dx = dy = 0.0; dsx = dsy = 1.0; dr = 0.0
        else:
            dx = float(np.median(U[sel])); dy = float(np.median(V[sel]))
            if n >= 40:
                pa, pb = fit_affine(Xc[sel], Yc[sel], U[sel], V[sel])
                dsx = 1 + float(pa[1]); dsy = 1 + float(pb[2]); dr = float((pb[1] - pa[2]) / 2)
                # 大きさが変わる時は中心の動き＝式の中心の値（中央値は片寄る）
                if abs(dsx - 1) > 0.004 or abs(dsy - 1) > 0.004:
                    dx = float(pa[0]); dy = float(pb[0])
            else:
                dsx = dsy = 1.0; dr = 0.0
        x += dx / k; y += dy / k; sx *= dsx; sy *= dsy; rot += dr
        rows.append(dict(f=f, x=round(x, 3), y=round(y, 3), sx=round(sx, 5), sy=round(sy, 5), s=round(float(np.sqrt(sx * sy)), 5), r=round(np.degrees(rot), 3),
                         dx=round(dx / k, 3), dy=round(dy / k, 3), v=round(float(np.hypot(dx, dy) / k), 3), n=n, roi=[round(v / k, 1) for v in r]))
        if a.follow:
            roi[0] += dx; roi[1] += dy
        if a.follow_scale:
            cxr, cyr = roi[0] + roi[2] / 2, roi[1] + roi[3] / 2
            roi[2] *= dsx; roi[3] *= dsy; roi[0] = cxr - roi[2] / 2; roi[1] = cyr - roi[3] / 2
    out = dict(video=os.path.abspath(a.video), name=a.name, mode=a.mode, mask=a.mask, roi0=[float(v) for v in a.roi.split(',')], w=a.w, W=W, H=H,
               frames=rows)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, 'w'), ensure_ascii=False, indent=0)
    # 絵：上＝枠のコマ 6 枚・下＝道の線
    jp = a.jpg or os.path.splitext(a.out)[0] + '.jpg'
    fs = [r['f'] for r in rows]
    pick = [fs[int(i)] for i in np.linspace(0, len(fs) - 1, min(6, len(fs)))]
    tiles = []
    for f in pick:
        im = F[f].copy(); rx, ry, rw, rh = rois[f]
        cv2.rectangle(im, (rx, ry), (rx + rw, ry + rh), (0, 255, 255), 2)
        t = cv2.resize(im, (320, int(320 * h / w)), interpolation=cv2.INTER_AREA)
        cv2.putText(t, str(f), (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
        tiles.append(t)
    while len(tiles) < 6:
        tiles.append(np.zeros_like(tiles[0]))
    top = np.hstack(tiles)
    Wd = top.shape[1]; Hg = 130
    chans = (('x', (80, 200, 255)), ('y', (255, 160, 60)), ('sx' if a.mode == 'flow' else 'w', (120, 255, 120)), ('v' if a.mode == 'flow' else 'h', (220, 220, 220)))
    panels = []
    for key, col in chans:
        g = np.full((Hg, Wd, 3), 28, np.uint8)
        vals = np.array([r.get(key, np.nan) for r in rows], float)
        ok = np.isfinite(vals)
        if ok.sum() >= 2:
            lo, hi = np.nanmin(vals), np.nanmax(vals); sp = max(hi - lo, 1e-6)
            pts = [(int(8 + i / max(len(vals) - 1, 1) * (Wd - 16)), int(Hg - 10 - (v - lo) / sp * (Hg - 30))) for i, v in enumerate(vals) if np.isfinite(v)]
            cv2.polylines(g, [np.array(pts, np.int32)], False, col, 2, cv2.LINE_AA)
            for p in pts:
                cv2.circle(g, p, 2, col, -1, cv2.LINE_AA)
            cv2.putText(g, f'{key}  {lo:.2f} .. {hi:.2f}   {a.name} {a.f0}-{a.f1}', (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (230, 230, 230), 1, cv2.LINE_AA)
        panels.append(g)
    cv2.imwrite(jp, np.vstack([top] + panels), [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(f'{a.name or "kiseki"} {a.f0}-{a.f1} mode={a.mode} → {a.out}（{len(rows)} コマ）・絵 {jp}')


if __name__ == '__main__':
    main()
