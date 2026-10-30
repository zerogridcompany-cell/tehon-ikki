"""font_id.py  手本の字の書体を探す（51 再開5・6回目の font_id.py・font_id6.py を1本に）。

何をする：手本の字のマスク（glyph_match の masks_<版>/<id>.npz の mr）の箱に、候補の書体で描いた語を縦横別に合わせ（箱をぴったり）、IoU を比べる。
  太さは 450〜850 を 50 刻みで一番良い所（可変の書体の時だけ効く）。
使い方：python3 font_id.py <版名> --work <作業> --fonts "<書体の道1>,<道2>,…|<フォルダ>/*.ttf" [--ids a,b]
入れる物：<out>/glyph/masks_<版名>/（glyph_match.py が作る）・字の表（text）・候補の書体（OFL の Google Fonts 等）
出す物：<out>/glyph/font_id_<版名>.json（書体ごと・字ごとの IoU と太さ）と画面に平均の順位
効いた数字（51）：太いゴシック 34書体を比べて Inter 0.651＝SF Pro 0.651（1位同点）＞Gantari 0.637＝書体は替えんと決めた
落とし穴：IoU は太い字に寄る（r2 は「ぼかした相関」で選んだ）。最後は字の形（y の尾・f・B）を目で見る（51 の通知の字は Lato やった）
"""
import os, sys, json, glob
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U

def bbox(m):
    ys, xs = np.where(m); return ys.min(), ys.max() + 1, xs.min(), xs.max() + 1

def render(fp, text, w):
    f = ImageFont.truetype(fp, 200)
    try:
        vals = []
        for ax in f.get_variation_axes():
            nm = ax.get('name', b''); nm = (nm.decode() if isinstance(nm, bytes) else str(nm)).lower()
            vals.append(max(ax['minimum'], min(ax['maximum'], w if nm.startswith('weight') else 32 if nm.startswith('optical') else ax['default'])))
        f.set_variation_by_axes(vals)
    except Exception: pass
    im = Image.new('L', (2400 + 120 * len(text), 400), 0); ImageDraw.Draw(im).text((20, 60), text, font=f, fill=255)
    return np.array(im) > 128

ap = U.base_args(__doc__); ap.add_argument('ver'); ap.add_argument('--fonts', required=True)
a = U.resolve(ap.parse_args())
FP = []
for s in a.fonts.split(','):
    FP += sorted(glob.glob(os.path.expanduser(s)))
TI = {t['id']: t for t in a.T}
MD = f'{a.out}/glyph/masks_{a.ver}'
IDS = sorted(a.idset) if a.idset else sorted(os.path.splitext(p)[0] for p in os.listdir(MD))
res = {}
for fp in FP:
    fn = os.path.basename(fp).split('[')[0]; sc = []
    for k in IDS:
        if k not in TI: continue
        z = np.load(f'{MD}/{k}.npz'); mr = z['mr'] > 0
        if mr.sum() < 50: continue
        y0, y1, x0, x1 = bbox(mr); R = mr[y0:y1, x0:x1]; best = (0, 0)
        for w in range(450, 851, 50):
            O = render(fp, TI[k]['text'], w)
            if not O.any(): continue
            p, q, r, s = bbox(O)
            o = cv2.resize(O[p:q, r:s].astype(np.uint8), (R.shape[1], R.shape[0]), interpolation=cv2.INTER_AREA) > 0
            v = (o & R).sum() / (o | R).sum()
            if v > best[0]: best = (v, w)
        sc.append((k, round(float(best[0]), 3), best[1]))
    res[fn] = sc
    if sc: print(f"{fn:22s} 平均 {np.mean([s[1] for s in sc]):.3f}  " + ' '.join(f'{k}:{v:.2f}/{w}' for k, v, w in sc), flush=True)
json.dump(res, open(f'{a.out}/glyph/font_id_{a.ver}.json', 'w'), indent=0, ensure_ascii=False)
rank = sorted(((np.mean([s[1] for s in v]), k) for k, v in res.items() if v), reverse=True)
print('順位：' + ' ＞ '.join(f'{k} {m:.3f}' for m, k in rank[:5]))
