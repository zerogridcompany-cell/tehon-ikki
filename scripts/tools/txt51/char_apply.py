"""char_apply.py  char_reg.py の1字ずつのずれを字の表に当てる（51 再開5回目）。

何をする：字ごとの送り＝cdx（字ごと・空白も含む・SVG tspan の dx＝それより後ろの字も一緒に動く＝差を入れる）。止まっとる字は縦のずれも y に。
  当てる条件：当てた字が塊の 7割以上・1字ずつ当てて IoU が 0.01 以上上がる・字の塊の数＝空白以外の字の数（「"」の2つの塊は1字にまとめる）。
  画面の px → 字の単位：拡大 s（zoom・zoomk の、測ったコマの倍率）と sx で割る。1px 未満のずれは当てん（測りは 1px 刻み）。
使い方：python3 char_apply.py <版名> --work <作業> [--skip id,id] [--dry]
入れる物：<out>/r5/char_<版名>.json・字の表
出す物：字の表の cdx・y（Txt51.tsx が tspan の dx に描く）
効いた数字（51）：char_reg と組で IoU 平均 0.766→0.780・28語
落とし穴：太さ（wv）を変えると字の幅も変わる＝太さを変えたら1字ずつ当て直しとセット（±50 で IoU 0.78→0.68）
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U
ap = U.base_args(__doc__); ap.add_argument('ver'); ap.add_argument('--skip', default=''); ap.add_argument('--dry', action='store_true')
a = U.resolve(ap.parse_args()); SKIP = set(a.skip.split(',')) if a.skip else set()
TI = {t['id']: t for t in a.T}
R = json.load(open(f'{a.out}/r5/char_{a.ver}.json')); log = []
for r in R:
    d = TI[r['id']]
    if r['id'] in SKIP or 'a' not in r: continue
    nc = [i for i, c in enumerate(d['text']) if not c.isspace()]
    ch = r['chars']
    if len(ch) > len(nc):   # 「"」は2つの塊＝小さい塊が並んだら1字にまとめる
        md = np.median([c['n'] for c in ch]); out = []
        for c in ch:
            if out and c['n'] < 0.25 * md and out[-1]['n'] < 0.25 * md and not out[-1].get('m'):
                p_ = out[-1]; w_ = p_['n'] + c['n']
                out[-1] = dict(p_, cx=(p_['cx'] * p_['n'] + c['cx'] * c['n']) / w_, n=w_, dx=round((p_['dx'] * p_['n'] + c['dx'] * c['n']) / w_), refpx=p_['refpx'] + c['refpx'], iou=min(p_['iou'], c['iou']), m=1)
            else: out.append(c)
        ch = out
    r = dict(r, chars=ch); nG = len(ch)
    if nG != len(nc): log.append(f"{r['id']}：塊 {nG}・字 {len(nc)} が合わん＝当てん"); continue
    if r['nok'] < 0.7 * nG or r['iou1'] - r['iou0'] < 0.01: continue
    s, _ = U.zoom_at(d, r['f'] / a.fps, a.W, a.H); sx = d.get('sx', 1)
    o = []
    for c in r['chars']:
        ok = c['refpx'] > 0.4 * c['n'] and c['iou'] > 0.3
        v = c['dx'] if ok else r['a'] + r['b'] * (c['cx'] - r['xm'])
        o.append(v if abs(v) >= 1 else 0.0)
    old = d.get('cdx') or [0.0] * len(d['text'])
    cum_old = np.cumsum(old) * s * sx   # 今の cdx の累積（画面 px）に足す
    absn = [0.0] * len(d['text']); j = 0; last = 0.0
    for i, c in enumerate(d['text']):
        if not c.isspace(): last = o[j]; j += 1
        absn[i] = cum_old[i] + last
    cdx = [round((absn[i] - (absn[i - 1] if i else 0)) / (s * sx), 2) for i in range(len(d['text']))]
    dy = 0.0
    static = not any(d.get(k) for k in ('dyk', 'zoomk', 'zoom', 'jumps'))
    if static and abs(r['dy']) >= 1.5: dy = round(r['dy'], 1)
    log.append(f"{r['id']}：字ごとの送り（画面 px）{' '.join(f'{v:+.0f}' for v in o)}・縦 {dy:+.1f}・IoU {r['iou0']:.3f}→{r['iou1']:.3f}")
    if not a.dry:
        d['cdx'] = cdx
        if dy: d['y'] = round(d['y'] + dy, 2)
print('\n'.join(log))
if not a.dry: U.save_texts(a.texts, a.T, a.fmt, a.fps)
