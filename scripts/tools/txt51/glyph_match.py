"""glyph_match.py  字の物差し：字ごとに手本とうちの字の色のマスクを取り、IoU と箱のずれを出す（51 10/24 一括補正・再開7回目で物差し2）。

何をする：OCR の文字列は使わん（手本の OCR が money→mainey 等に読み違える＝物差しが壊れる）。字ごと（測るコマ＝frame_of）に、
  手本とうちの同じコマから字の色のマスク（RGB 距離 70 以内）を取る。窓＝字だけの層の字の形を BAND px（既定 18×高さ/1080）太らせた帯の中だけ。
  1つ目で測れん字・掛け合わせの字だけ物差し2：色の字＝一番強い色の線がほかの 1.6 倍＋8 以上（hue）／白い字＝帯の中を大津で2つに（otsu）。
  地を拾った怪しい測り（帯の 75% 超・面積の比 0.6〜1.67 の外・帯の縁の 25% 超・箱の差が大きすぎ）は「測り不能」（数に入れん・推測で埋めん）。
判定：IoU ≥0.995・箱 ±0.5%（幅・高さの 0.5%）
使い方：python3 glyph_match.py <うちの mp4|none> <版名> --work <作業> --sheet <今の版の字だけの層> [--frames <うちを字ごとに書き出した element-kk.png>]
入れる物：手本・うちの mp4（--frames があれば要らん）・字の表・字だけの層
出す物：<out>/glyph/match_<版名>.json・.md・masks_<版名>/<id>.npz（ikkatsu_txt.py・font_id.py が使う）
効いた数字（51）：測れた 47→52（物差し2）・字の箱 27→43/57（dk・ka・sw などと組）
落とし穴：🔴 --sheet は必ず今の版の字だけの層（古い層で測って数字がずれた）。🔴 箱のずれは位置を動かす根拠にせん（薄い所を拾わん＝片寄る）。
  箱だけ合って見た目が悪くなる直しは捨てる（帯の SSIM と一緒に見る）
"""
import os, sys, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U

def mask(img, col, win, band):
    x0, y0, x1, y1 = win; sub = img[y0:y1, x0:x1].astype(np.float32)
    m = (np.linalg.norm(sub - col, axis=2) < 70).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    full = np.zeros(img.shape[:2], np.uint8); full[y0:y1, x0:x1] = m; return full * band

def mask2(img, col, win, band, how):
    x0, y0, x1, y1 = win; sub = img[y0:y1, x0:x1].astype(np.float32); bb = band[y0:y1, x0:x1] > 0
    if how == 'hue':
        c = int(np.argmax(col)); o = [i for i in range(3) if i != c]
        m = (sub[..., c] >= 1.6 * np.maximum(sub[..., o[0]], sub[..., o[1]]) + 8).astype(np.uint8)
    else:
        L = cv2.cvtColor(sub.astype(np.uint8), cv2.COLOR_BGR2GRAY); v = L[bb]
        th, _ = cv2.threshold(v.reshape(-1, 1), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU); m = (L > th).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    full = np.zeros(img.shape[:2], np.uint8); full[y0:y1, x0:x1] = m; return full * band

def box(m):
    ys, xs = np.where(m > 0)
    if len(xs) < 80: return None
    q = lambda v, p: float(np.percentile(v, p))
    return [q(xs, 0.5), q(ys, 0.5), q(xs, 99.5), q(ys, 99.5)]

def main():
    ap = U.base_args(__doc__); ap.add_argument('ours'); ap.add_argument('ver')
    ap.add_argument('--frames', default=None, help='うちの絵を字ごとに書き出した所（element-kk.png＝字 k の測るコマ）')
    a = U.resolve(ap.parse_args()); W, H, K = a.W, a.H, a.K
    BAND = max(4, int(round(18 * K))); LX, LY = 0.005 * W, 0.005 * H; PX, PY = int(110 * K), int(70 * K)
    rows = []; niou = nbox = nbad = 0; T = [d for d in a.T]
    for i, d in enumerate(T):
        if a.idset and d['id'] not in a.idset: continue
        f = U.frame_of(d, a.fps); R = U.grab(a.ref, f, a.fps, f'{a.out}/frames/ref')
        O = cv2.imread(f'{a.frames}/element-{i:02d}.png') if a.frames else U.grab(a.ours, f, a.fps, f'{a.out}/frames/{a.ver}')
        A = U.sheet_alpha(a.sheet, i)
        col = U.hexbgr(d.get('color', '#ffffff'))
        r = dict(id=d['id'], f=f, color=d.get('color', '#ffffff'))
        if A is None: r.update(state='測り不能', why='字だけの層が無い'); rows.append(r); nbad += 1; continue
        sh = (A > 80 / 255); ys, xs = np.where(sh)
        win = [max(0, int(xs.min()) - PX), max(0, int(ys.min()) - PY), min(W, int(xs.max()) + PX), min(H, int(ys.max()) + PY)]
        band = cv2.dilate(sh.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * BAND + 1, 2 * BAND + 1)))
        area = int(band.sum())
        def judge(mr, mo):
            br, bo = box(mr), box(mo); ar, ao = int(mr.sum()), int(mo.sum()); why = None
            if br is None or bo is None: why = '字の色の画素が少ない（80 未満）'
            elif max(ar, ao) / area > 0.75: why = f'帯の {max(ar, ao) / area:.0%} が字の色＝地を拾っとる'
            elif not 0.6 <= ao / max(ar, 1) <= 1.67: why = f'面積の比 {ao / max(ar, 1):.2f}＝片方が地か別の物を拾っとる'
            else:
                edge = band - cv2.erode(band, np.ones((5, 5), np.uint8)); fe = float((mr * edge).sum()) / max(1, edge.sum())
                if fe > 0.25: why = f'帯の縁の {fe:.0%} が字の色＝地を拾っとる'
                elif abs((bo[2] - bo[0]) - (br[2] - br[0])) >= 80 * K or abs((bo[3] - bo[1]) - (br[3] - br[1])) >= 40 * K: why = '箱の幅・高さの差が大きい＝別の物（札・光）を拾った疑い'
            return br, bo, ar, ao, why
        sat = col.max() - col.min() > 60; mul = bool(d.get('mul')) or d.get('blend') == 'multiply'
        how = 'hue' if (mul and sat) else '色'
        mr, mo = (mask2(R, col, win, band, 'hue'), mask2(O, col, win, band, 'hue')) if how == 'hue' else (mask(R, col, win, band), mask(O, col, win, band))
        br, bo, ar, ao, why = judge(mr, mo)
        if why and how == '色':
            how = 'hue' if sat else 'otsu'; why1 = why
            mr, mo = mask2(R, col, win, band, how), mask2(O, col, win, band, how); br, bo, ar, ao, why = judge(mr, mo)
            if why: why = f'{why1}／物差し2（{how}）も：{why}'
        r['how'] = how
        if why: r.update(state='測り不能', why=why, rbox=br, obox=bo); rows.append(r); nbad += 1; continue
        by, bx = np.where(band > 0); y0b, y1b, x0b, x1b = by.min(), by.max() + 1, bx.min(), bx.max() + 1
        os.makedirs(f'{a.out}/glyph/masks_{a.ver}', exist_ok=True)
        np.savez_compressed(f'{a.out}/glyph/masks_{a.ver}/{d["id"]}.npz', mr=mr[y0b:y1b, x0b:x1b], mo=mo[y0b:y1b, x0b:x1b], off=np.array([x0b, y0b]))
        inter = int(((mr > 0) & (mo > 0)).sum()); uni = int(((mr > 0) | (mo > 0)).sum()); iou = inter / uni
        dd = [((bo[0] + bo[2]) - (br[0] + br[2])) / 2, ((bo[1] + bo[3]) - (br[1] + br[3])) / 2, (bo[2] - bo[0]) - (br[2] - br[0]), (bo[3] - bo[1]) - (br[3] - br[1])]
        okb = abs(dd[0]) <= LX and abs(dd[1]) <= LY and abs(dd[2]) <= LX and abs(dd[3]) <= LY
        s, c = U.zoom_at(d, f / a.fps, W, H)
        r.update(state='測れた', iou=round(iou, 4), okiou=iou >= 0.995, rbox=br, obox=bo, d=[round(v, 1) for v in dd], okbox=okb, zoom=[s, list(c)], area=[ar, ao])
        niou += iou >= 0.995; nbox += okb; rows.append(r)
    n = len(rows); nm = n - nbad
    os.makedirs(f'{a.out}/glyph', exist_ok=True)
    json.dump(dict(ver=a.ver, n=n, measured=nm, iou_ok=int(niou), box_ok=int(nbox), rows=rows), open(f'{a.out}/glyph/match_{a.ver}.json', 'w'), ensure_ascii=False, indent=0)
    md = [f'## 字のマスク照合（{a.ver}・{n} 字・測れた {nm}・測り不能 {nbad}）', f'- IoU ≥0.995：**{niou}/{n}**　箱 ±0.5%（横 {LX:.1f}px・縦 {LY:.1f}px）：**{nbox}/{n}**', '',
          '| id | コマ | 状態 | IoU | 横px | 縦px | 幅px | 高さpx | 箱 | 測り不能の理由 |', '|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        if r['state'] == '測れた':
            md.append(f"| {r['id']} | {r['f']} | 測れた（{r.get('how', '色')}） | {r['iou']:.3f} | {r['d'][0]:+.0f} | {r['d'][1]:+.0f} | {r['d'][2]:+.0f} | {r['d'][3]:+.0f} | {'✅' if r['okbox'] else '🔴'} | |")
        else: md.append(f"| {r['id']} | {r['f']} | 測り不能 | | | | | | | {r['why']} |")
    open(f'{a.out}/glyph/match_{a.ver}.md', 'w').write('\n'.join(md) + '\n')
    ious = [r['iou'] for r in rows if r['state'] == '測れた']
    print(f'{a.ver}: IoU合格 {niou}/{n}・箱合格 {nbox}/{n}・測れた {nm}' + (f'・IoU 中央 {np.median(ious):.3f}・平均 {np.mean(ious):.3f}' if ious else ''))

if __name__ == '__main__':
    main()
