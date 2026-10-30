"""build_texts.py  字の下書きの表（手本の字の箱つき）→ 字の表 texts.json。箱に同じ書体ファイルで大きさと位置を逆算して合わせる。

何をする：51 の build_texts.py（字を1つずつ add() で書いた物）の汎用版。字の中身は表（JSON）で渡す。
  行ごとに fit_text_box.fit で fs・sx・x・y を出し、ほかの値（reveal・exit・xout・blend…）はそのまま写す。
  sx は 0.8〜1.3 に収める（mode h の時・51 の決まり）。same＝前の字と同じ大きさで縦に並べる（[基の id, 縦の送り px]）
使い方：python3 build_texts.py <下書き.json> <書体の表.json> <出す texts.json>
入れる物：
  下書き＝[{id, text, font, w, color, box:[x0,y0,x1,y1], t0, t1(秒), mode?:'h'|'w', same?:[id,dy], ...好きな値}]
    箱は text_measure.py の box か lines[i]（手本の字のインクの外枠）・色は color（RGB の配列でも #hex でも）
  書体の表＝{"serif": {"file": "<ttf の道>", "opsz"?: 32}, "sans": {...}}（Txt51.tsx の fonts と同じ名前）
出す物：texts.json（Txt51.tsx・ほかの txt51 の道具が読む形）
効いた数字（51）：57語の位置が 0.5% 以内から始まる（その後 txt_reg・char_reg で詰める）
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fit_text_box import font, fit
src, fmap, out = sys.argv[1:4]
R = json.load(open(src)); FM = json.load(open(fmap)); T = []; cache = {}
C = lambda c: c if isinstance(c, str) else '#%02x%02x%02x' % tuple(c)
for r in R:
    d = dict(r); d['color'] = C(r.get('color', '#ffffff')); fd = FM[r['font']]
    key = (r['font'], r.get('w'))
    if key not in cache: cache[key] = font(fd['file'], r.get('w'), fd.get('opsz', 32))
    mode = r.get('mode', 'h'); d.pop('mode', None)
    d.update(fit(cache[key], r['text'], r['box'], mode, (0.8, 1.3) if mode == 'h' else None))
    T.append(d)
by = {t['id']: t for t in T}
for t in T:
    if t.get('same'):
        b, dy = t.pop('same'); s = by[b]; t.update(fs=s['fs'], sx=s['sx'], x=s['x'], y=round(s['y'] + dy, 1))
json.dump(T, open(out, 'w'), indent=0, ensure_ascii=False)
print(len(T), '字 →', out)
