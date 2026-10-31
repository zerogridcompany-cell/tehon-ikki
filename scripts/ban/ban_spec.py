# 段5 CapCut の仕様書（spec.json）：板ごとの字（字体・大きさ・位置・横の倍率・色）＋変わる字＋1コマずつのフェード＋図の素材（zu.mp4 を板ごとに切る）＋曲
# 使い方：python3 ban_spec.py <ban の置き場> [下書きの名前]
#   hosei.json があれば字ごとの戻し（書き出しを測ったずれ）を足す。使った戻しは hosei_used.json に書く（次の戻し＝これ＋測ったずれ）
import json, os, re, sys
from collections import Counter
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ban_lib import Ban
b = Ban(sys.argv[1]); FPS = b.FPS; st = b.states(); R = b.rows()
NAME = sys.argv[2] if len(sys.argv) > 2 else b.cfg.get('name', 'ban_v1')
HOSEI = {}
if os.path.exists(b.p('hosei.json')):
    for o in json.load(open(b.p('hosei.json'))): HOSEI[(o['i'], o['t'], o.get('bx'))] = o
KW = json.load(open(b.p('kawaru.json'))) if os.path.exists(b.p('kawaru.json')) else {}
FD = json.load(open(b.p('fade.json'))) if os.path.exists(b.p('fade.json')) else {'frame': {}, 'text': {}}
def timer_vals(sp):                                   # 時計（00.6 s）：1区切りごとに 0.1 進む＝読んだ値から頭の値を多数決で決めて並びを作り直す（読み違いに強い）
    c = Counter()
    for k, (e0, e1, r) in enumerate(sp):
        m = re.fullmatch(r'(\d\d)\.(\d) s', r.strip())
        if m: c[round(float(m.group(1) + '.' + m.group(2)) - 0.1 * k, 1)] += 1
    if not c: return None
    v0 = c.most_common(1)[0][0]; return ['%04.1f s' % (v0 + 0.1 * k) for k in range(len(sp))], c.most_common(1)[0][1], len(sp)
REPL = b.cfg.get('replace', {})                      # 字の差し替え {元の字: 新しい字}：動き・時刻・字体はそのまま、中身だけ替える（図は手本のまま）
items, layers, TSTAT, FSEL, USED = [], [], [], {}, {}
for s in st:
    i = s['i']; a = s['f0'] / FPS; bb = s['f1'] / FPS; g = b.gray(i)
    for t, box in R.get(i, []):
        if not b.capcut(i, t): continue
        ib, pk = b.ink_box(g, box)
        key = b.rule_font(i, t, box) or b.pick_font(t, g, ib)
        center = b.is_center(ib)
        sz, cx, cy, iw, sx = b.fit(t, key, ib)
        hk = f'{i}|{t}|{box[0] // 10}'; FSEL[hk] = key
        h = HOSEI.get((i, t, box[0] // 10)) or HOSEI.get((i, t, None))
        if h and h.get('font', key) != key: h = None    # 字体が替わった字は戻しをやり直す
        USED[hk] = dict(h, font=key, i=i, t=t, bx=box[0] // 10) if h else dict(i=i, t=t, bx=box[0] // 10, x=0.0, y=0.0, w=1.0, font=key)
        if h: cx -= h['x']; cy -= h['y']; sx = min(1.4, max(0.6, sx * h['w']))
        fk = f'{i}:{t}:{box[0]}'
        if t in REPL: sz, cx, cy, sx = b.fit_new(REPL[t], key, ib, sz, center); t = REPL[t]
        col = int(min(255, pk))
        base = dict(i=i, t=t, font=key, px=sz, sx=sx, x=cx, y=cy, color='#%02x%02x%02x' % (col, col, col), a=a, b=bb, fk=fk)
        sp = KW.get(fk)
        if not sp: items.append(base); continue
        tv = timer_vals(sp) if re.fullmatch(r'\d\d\.\d s', t) else None
        if tv: TSTAT.append(tv[1:])
        for k, (e0, e1, r) in enumerate(sp):
            txt = tv[0][k] if tv else (b.norm(r.strip()) if b.plain(r.strip()) else t)
            z = dict(base, t=txt, a=e0 / FPS, b=e1 / FPS)
            if txt != t:                              # 字が替わった区切り：大きさ・高さはそのまま、真ん中寄せは真ん中・左寄せは左の端をそろえる
                f = b.font(key, max(4, int(round(sz)))); l2, _, r2, _ = f.getbbox(txt, anchor='ls'); adv2 = f.getlength(txt)
                l1, _, r1, _ = f.getbbox(t, anchor='ls'); adv1 = f.getlength(t)
                if not center: z['x'] = cx - (adv1 / 2 - l1) * sx + (adv2 / 2 - l2) * sx
            items.append(z)
    layers.append(dict(path='zu.mp4', a=a, b=bb, src=a))   # 図の素材を板ごとに切って置く（src＝同じ時刻）
items.sort(key=lambda z: (z['t'], round(z['x'] / 6), round(z['y'] / 6), z['a']))
merged = []
for z in items:                                       # 同じ字が続く板は1本につなぐ
    p = merged[-1] if merged else None
    if p and p['t'] == z['t'] and p['font'] == z['font'] and abs(p['x'] - z['x']) <= 4 and abs(p['y'] - z['y']) <= 4 and abs(p['b'] - z['a']) < 1e-6:
        p['b'] = z['b']; continue
    merged.append(dict(z))
texts = [dict(t=z['t'], font=z['font'], fs=round(b.fs_of(z['font'], z['px']), 4), px=round(z['px'], 2), sx=round(z['sx'], 4), x=round(z['x'], 2), y=round(z['y'], 2),
              color=z['color'], a=round(z['a'], 6), b=round(z['b'], 6), fk=z['fk']) for z in merged]
# フェード＝測った割合を、CapCut の字の不透明度（global_alpha）で1コマずつ打つ（字の区切りを1コマずつに割る）
FR = {int(k): v for k, v in FD['frame'].items()}; TX = {k: {int(f): v for f, v in c.items()} for k, c in FD['text'].items()}
out = []
for z in texts:
    crv = TX.get(z['fk'], FR); fa, fb = round(z['a'] * FPS), round(z['b'] * FPS)
    fr = [f for f in range(fa, fb) if crv.get(f, 1.0) < 0.999]; cur = fa
    for f in fr:
        if f > cur: out.append(dict(z, a=cur / FPS, b=f / FPS))
        out.append(dict(z, a=f / FPS, b=(f + 1) / FPS, alpha=round(crv[f], 4))); cur = f + 1
    if cur < fb: out.append(dict(z, a=cur / FPS, b=fb / FPS))
texts = [dict({k: v for k, v in z.items() if k != 'fk'}, a=round(z['a'], 6), b=round(z['b'], 6)) for z in out if z['b'] - z['a'] > 1e-4]
dur = st[-1]['f1'] / FPS
spec = dict(name=NAME, W=b.W, H=b.H, fps=FPS, dur=dur, fonts=b.F, texts=texts, layers=layers,
            audio=[dict(path=b.cfg['audio'], a=0.0, b=dur, vol=1.0)] if b.cfg.get('audio') else [], cover=f"f/s{b.cfg.get('cover_state', 0):02d}.png")
json.dump(spec, open(b.p('spec.json'), 'w'), ensure_ascii=False, indent=0)
json.dump(FSEL, open(b.p('fontsel.json'), 'w'), ensure_ascii=False)
json.dump(USED, open(b.p('hosei_used.json'), 'w'), ensure_ascii=False)
print(f"字 {len(items)}→つないで {len(merged)}→1コマのフェードで割って {len(texts)}（不透明度を打った区切り {sum(1 for z in texts if 'alpha' in z)}）・図の区切り {len(layers)}・{dur:.2f}秒・時計の読みの一致 {TSTAT}")
