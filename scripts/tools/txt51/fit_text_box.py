#!/usr/bin/env python3
"""fit_text_box.py  手本の字のインクの外枠（測った箱）に、同じ書体ファイルで大きさ・位置を逆算する（技「箱合わせの字」）。

使い方：python3 fit_text_box.py <書体.ttf> <文> <x0> <y0> <x1> <y1> [--w 太さ] [--opsz 32] [--mode h|w]
  --mode h＝高さで fs を決めて幅は sx で合わせる（既定）／w＝幅で fs を決めて sx=1
入れる物：書体ファイル（可変の書体は --w で太さ）・文・箱（画面の px）
出す物：1行の JSON {fs, sx, x, y}（SVG の text を translate(x,y) scale(sx,1)・font-size=fs で置く＝Txt51.tsx と同じ置き方）
効いた数字（51）：位置 0.5% 以内（build_texts.py の土台）
"""
import sys, json
from PIL import ImageFont

def font(f, w=None, opsz=32):
    F = ImageFont.truetype(f, 1000)
    if w:
        try:
            vals = []
            for ax in F.get_variation_axes():
                nm = ax.get('name', b''); nm = (nm.decode() if isinstance(nm, bytes) else str(nm)).lower()
                vals.append(max(ax['minimum'], min(ax['maximum'], w if nm.startswith('weight') else opsz if nm.startswith('optical') else ax['default'])))
            F.set_variation_by_axes(vals)
        except Exception: pass
    return F

def fit(F, text, box, mode='h', sx_lim=None):
    l, t, r, b = F.getbbox(text, anchor='ls'); bw, bh = box[2] - box[0], box[3] - box[1]
    fsh, fsw = bh * 1000 / (b - t), bw * 1000 / (r - l)
    fs = fsh if mode == 'h' else fsw; sx = 1.0 if mode == 'w' else fsw / fsh
    if sx_lim: sx = max(sx_lim[0], min(sx_lim[1], sx))
    return dict(fs=round(fs, 2), sx=round(sx, 4), x=round(box[0] - l * fs / 1000 * sx, 1), y=round(box[1] - t * fs / 1000, 1))

if __name__ == '__main__':
    f, text = sys.argv[1], sys.argv[2]; box = [float(v) for v in sys.argv[3:7]]
    g = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    w = int(g('--w')) if g('--w') else None
    print(json.dumps(fit(font(f, w, float(g('--opsz', 32))), text, box, g('--mode', 'h'))))
