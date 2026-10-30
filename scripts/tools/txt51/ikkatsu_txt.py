"""ikkatsu_txt.py  字の一括補正（51 10/24「データを元に一発で縮められんのか」→ 案1 の、字の所だけ）。

何をする：今までの版（--hist・最後が今の版）の測り（glyph_match の match_<版>.json・masks_<版>/）と、その版で使った字の表の控え
  （<out>/glyph/texts_<版>.json）から、字ごとに一番 IoU の良かった版を土台にし、その版の手本とうちの字のマスクを重ね合わせて
  （横・縦の倍率と位置で IoU 最大＝位相相関で位置の見当→倍率 0.95〜1.05 を 0.01→0.0025 で細かく）、ずれの逆向きを x・y・sx・fs に入れる。
  拡大中の字は拡大の前に戻して計算する。直す量はダンピング 0.8。
使い方：python3 ikkatsu_txt.py <次の版> --hist v1,v2,…,今の版 --work <作業> [--to <書く字の表>（既定＝字の表そのもの）] [--damp 0.8]
入れる物：<out>/glyph/match_<版>.json・masks_<版>/・texts_<版>.json（版ごと・書き出した時の字の表の写し）
出す物：字の表（--to）と <out>/glyph/texts_<次の版>.json（控え）・<out>/glyph/ikkatsu_<次の版>.md（字ごとの 土台・IoU 前→後・直した事）
効いた数字（51）：ik1 の学び＝箱の差だけで直すと箱は 22→39/57 になったが、字の形がずれて IoU 0.70→0.67・SSIM が下がった＝箱やなく形で合わせる
  （51 の ikkatsu.py の色・動きの所は 51 の場面の決まり（紙の場面・mane_check の秒の表）に乗っとる＝移さん。色は look_shot.py を使う）
"""
import os, sys, json, shutil
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U

def reg(mr, mo):
    """mo（うち）を倍率 kx,ky（重心まわり）＋ずれ tx,ty で動かして mr（手本）との IoU を最大に → (kx, ky, tx, ty, iou, 重心)"""
    a = cv2.GaussianBlur(mr.astype(np.float32), (0, 0), 1.5); ys, xs = np.where(mo > 0); c = (xs.mean(), ys.mean())
    def warp(k, t):
        M = np.float32([[k[0], 0, c[0] - k[0] * c[0] + t[0]], [0, k[1], c[1] - k[1] * c[1] + t[1]]])
        return cv2.warpAffine(mo.astype(np.float32), M, mo.shape[::-1], flags=cv2.INTER_LINEAR)
    def iou(w): A, Bm = mr > 0, w > 0.5; return (A & Bm).sum() / max(1, (A | Bm).sum())
    def best_t(k):
        w = cv2.GaussianBlur(warp(k, (0, 0)), (0, 0), 1.5)
        (sx, sy), _ = cv2.phaseCorrelate(w, a); sx, sy = float(np.clip(sx, -20, 20)), float(np.clip(sy, -20, 20))
        return max(((iou(warp(k, t)), t) for t in [(sx, sy), (0, 0)]), key=lambda z: z[0])
    best = (-1, (1, 1), (0, 0))
    for kx in np.arange(0.95, 1.051, 0.01):
        for ky in np.arange(0.95, 1.051, 0.01):
            v, t = best_t((kx, ky))
            if v > best[0]: best = (v, (kx, ky), t)
    v0, k0, t0 = best
    for kx in np.arange(k0[0] - 0.01, k0[0] + 0.011, 0.0025):
        for ky in np.arange(k0[1] - 0.01, k0[1] + 0.011, 0.0025):
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    t = (t0[0] + dx, t0[1] + dy); v = iou(warp((kx, ky), t))
                    if v > best[0]: best = (v, (kx, ky), t)
    return best[1][0], best[1][1], best[2][0], best[2][1], best[0], c

def main():
    ap = U.base_args(__doc__); ap.add_argument('nxt'); ap.add_argument('--hist', required=True); ap.add_argument('--to', default=None); ap.add_argument('--damp', type=float, default=0.8)
    a = U.resolve(ap.parse_args()); GL = f'{a.out}/glyph'; D = a.damp
    H = a.hist.split(','); ver = H[-1]
    J = lambda p: json.load(open(p))
    TX = {v: {d['id']: d for d in U.load_texts(f'{GL}/texts_{v}.json', a.fps, a.look)[0]} for v in H}
    GM = {v: {r['id']: r for r in J(f'{GL}/match_{v}.json')['rows']} for v in H}
    T = a.T; nt = 0
    log = [f'# 字の一括補正 {ver} → {a.nxt}（ダンピング {D}・比べた版 {",".join(H)}）', '',
           '| id | 土台 | IoU 土台→重ねた時 | 倍率 横/縦 | ずれ px | 直した事 |', '|---|---|---|---|---|---|']
    for d in T:
        i = d['id']
        if a.idset and i not in a.idset: continue
        got = [(GM[v][i]['iou'], k, v) for k, v in enumerate(H) if GM[v].get(i, {}).get('state') == '測れた' and i in TX[v]]
        if not got: continue
        _, _, bv = max(got); base = TX[bv][i]; r = GM[bv][i]
        z = np.load(f'{GL}/masks_{bv}/{i}.npz'); kx, ky, tx, ty, iou2, c = reg(z['mr'], z['mo'])
        s, (zx, zy) = r['zoom']; cx, cy = c[0] + z['off'][0], c[1] + z['off'][1]
        cx, cy = zx + (cx - zx) / s, zy + (cy - zy) / s; tx, ty = tx / s, ty / s   # 拡大の前に戻す
        kx, ky, tx, ty = 1 + D * (kx - 1), 1 + D * (ky - 1), D * tx, D * ty
        old = {k: base[k] for k in ('x', 'y', 'sx', 'fs')}
        new = dict(x=round(cx + kx * (base['x'] - cx) + tx, 1), y=round(cy + ky * (base['y'] - cy) + ty, 1), sx=round(base['sx'] * kx / ky, 4), fs=round(base['fs'] * ky, 2))
        d.update(new); nt += 1
        log.append(f"| {i} | {bv} | {r['iou']:.3f}→{iou2:.3f} | {kx:.3f}/{ky:.3f} | {tx:+.1f},{ty:+.1f} | x {old['x']}→{new['x']}・y {old['y']}→{new['y']}・sx {old['sx']}→{new['sx']}・fs {old['fs']}→{new['fs']} |")
    log += ['', f'字：直した {nt}']
    to = a.to or a.texts
    if to != a.texts: shutil.copy(a.texts, to)
    U.save_texts(to, T, a.fmt, a.fps); shutil.copy(to, f'{GL}/texts_{a.nxt}.json')
    open(f'{GL}/ikkatsu_{a.nxt}.md', 'w').write('\n'.join(log) + '\n')
    print(f'字 {nt} → {to}')

if __name__ == '__main__':
    main()
