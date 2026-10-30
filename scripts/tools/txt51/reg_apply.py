"""reg_apply.py  txt_reg.py の当てた差（手本−うちの dx,dy と倍率の比）を字の表の x,y,fs,sx に入れる（51 再開4回目）。

使い方：python3 reg_apply.py <版名> --work <作業> [--skip id,id] [--dry]
入れる物：<out>/reg/<版名>.json・字の表（texts/caps どちらも・元の形で書き戻す）
出す物：字の表の x,y,fs,sx を直す（ok の字・--skip の字は触らん）。倍率は型の箱の真ん中を中心にかける
効いた数字（51）：txt_reg と組で 字の位置 17→52/57。手本の点（score）が低くて目で外れとった物は --skip で外す
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U
ap = U.base_args(__doc__); ap.add_argument('ver'); ap.add_argument('--skip', default=''); ap.add_argument('--dry', action='store_true')
a = U.resolve(ap.parse_args()); skip = set(a.skip.split(',')) if a.skip else set()
R = {r['id']: r for r in json.load(open(f'{a.out}/reg/{a.ver}.json')) if 'err' not in r}; log = []
for d in a.T:
    r = R.get(d['id'])
    if not r or d['id'] in skip or r['ok']: continue
    n = r['need']; Sx, Sy = n['sx'], n['sy']; cx, cy = r['ours']['c'][0] + r['ours']['dx'], r['ours']['c'][1] + r['ours']['dy']
    old = (d['x'], d['y'], d['fs'], d['sx'])
    d['x'] = round(cx + Sx * (d['x'] - cx) + n['dx'], 1); d['y'] = round(cy + Sy * (d['y'] - cy) + n['dy'], 1)
    d['fs'] = round(d['fs'] * Sy, 2); d['sx'] = round(d['sx'] * Sx / Sy, 4)
    log.append(f"{d['id']}: x {old[0]}→{d['x']} y {old[1]}→{d['y']} fs {old[2]}→{d['fs']} sx {old[3]}→{d['sx']}")
if not a.dry: U.save_texts(a.texts, a.T, a.fmt, a.fps)
print('\n'.join(log)); print(len(log), '字を直した', '（--dry＝書いとらん）' if a.dry else '')
