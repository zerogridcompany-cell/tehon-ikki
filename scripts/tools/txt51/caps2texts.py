"""caps2texts.py  字の表の形を変える：r2 の caps.json（語ごと・コマ）⇄ 51 の texts.json（字ごと・秒）。

違い：
  caps 形 ＝{i, w(語), f0, f1(コマ・f1 のコマも出とる), kind('serif'|'sans'), fs, x, y, sx, box, guess}。太さ・横の倍率・書体は look.json（serifW・sansW・serifSx・sansSx・serifFile・sansFile）
  texts 形＝{id, text, font, w(太さ), color, t0, t1(秒・t1 は出とらん), reveal?, exit?, xout?, fs, x, y, sx, ...}
  直し方：id＝"c<i>"・text＝w・font＝kind・w＝look の <kind>W・sx＝look の <kind>Sx（r2 の Main.tsx は c.sx でなく look の倍率で描いとる）・
  t0＝f0/fps・t1＝(f1+1)/fps・color＝#ffffff
使い方：python3 caps2texts.py <caps.json> <texts.json> --fps 29.97 [--look look.json]   （caps → texts）
        python3 caps2texts.py <texts.json> <caps.json> --fps 29.97 --back <元の caps.json>  （texts → caps・元の caps に x,y,fs,sx と足した値を戻す）
ほかの txt51 の道具は caps.json をそのまま読める（中でこれと同じ直しをする）。Remotion で Txt51.tsx を使う時に texts.json が要る
"""
import os, sys, json, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U
g = lambda k, d=None: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
src, dst = sys.argv[1], sys.argv[2]; fps = float(g('--fps', 30)); look = g('--look')
if g('--back'):
    T = json.load(open(src)); shutil.copy(g('--back'), dst)
    for i, d in enumerate(T):
        if '_i' not in d: d['_i'] = int(str(d['id']).lstrip('c')) if str(d['id']).lstrip('c').isdigit() else i
    U.save_texts(dst, T, 'caps', fps); print(len(T), '語 →', dst)
else:
    if look is None:
        p = os.path.join(os.path.dirname(os.path.abspath(src)), 'look.json'); look = p if os.path.exists(p) else None
    T, fmt = U.load_texts(src, fps, look)
    if fmt != 'caps': sys.exit('caps 形やない')
    for d in T: d.pop('_i', None); d.pop('_sxl', None)
    json.dump(T, open(dst, 'w'), ensure_ascii=False, indent=1); print(len(T), '語 →', dst, '（look:', look, '）')
