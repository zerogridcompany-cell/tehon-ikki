"""dk_pick.py  字ごとに、試した版の中から一番良い値（下の出 dk・上の出 ka・線の削り er など1つ）を選んで字の表に書く（51 再開6回目）。

何をする：同じ値を全部の字に振った試しの版（Txt51 の --props {"dk":{"*":0.88}} で字だけの層＋字ごとのコマを書き出し → glyph_match）を比べる。
  選び方＝箱が合う版のうち IoU が一番高い物。合う版が無ければ、IoU を基の版より 0.003 以上落とさず縦の差 |dh| が一番小さい物。
  基の版と IoU の差が 0.002 未満で箱の合否も同じなら書かん（基の値のまま）。
使い方：python3 dk_pick.py <基の版>:<基の値>,<版>:<値>,… --work <作業> [--key dk] [--font sans] [--dry]
  例：dk100:1,dk92:0.92,dk88:0.88,dk84:0.84 --key dk
入れる物：<out>/glyph/match_<版>.json（版ごと）・字の表
出す物：字の表の <key>（基の値と同じなら消す）
効いた数字（51）：dk で字の箱 27→33/57（job +25→−2・possible +20→+3・money2 +17→0）・ka で costs 🔴→✅・lifeis 0.874→0.892
落とし穴：箱だけ合って見た目が悪くなる直しは捨てる（帯の SSIM と一緒に見る）
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _t51 as U
ap = U.base_args(__doc__); ap.add_argument('vers'); ap.add_argument('--key', default='dk'); ap.add_argument('--font', default=None); ap.add_argument('--dry', action='store_true')
a = U.resolve(ap.parse_args())
VV = [s.split(':') for s in a.vers.split(',')]; V = [v for v, _ in VV]; VAL = {v: float(x) for v, x in VV}; base = V[0]
M = {v: {r['id']: r for r in json.load(open(f'{a.out}/glyph/match_{v}.json'))['rows']} for v in V}; log = []
for d in a.T:
    if a.font and d['font'] != a.font: continue
    if a.idset and d['id'] not in a.idset: continue
    rs = {v: M[v].get(d['id'], {}) for v in V}; b = rs[base]
    if b.get('state') != '測れた': continue
    ok = [v for v in V if rs[v].get('okbox')]
    if ok: v = max(ok, key=lambda v: (rs[v]['iou'], v == base))
    else:
        c = [v for v in V if rs[v].get('state') == '測れた' and rs[v]['iou'] >= b['iou'] - 0.003]
        v = min(c, key=lambda v: (abs(rs[v]['d'][3]), v != base))
    k = VAL[v]
    if abs(rs[v]['iou'] - b['iou']) < 0.002 and rs[v].get('okbox') == b.get('okbox'): k = VAL[base]
    if k != VAL[base]:
        d[a.key] = k; log.append(f"{d['id']}: {a.key} {k}（IoU {b['iou']:.3f}→{rs[v]['iou']:.3f}・箱 {'✅' if b.get('okbox') else '🔴'}→{'✅' if rs[v].get('okbox') else '🔴'}・dh {b['d'][3]:+.0f}→{rs[v]['d'][3]:+.0f}）")
    else: d.pop(a.key, None)
if not a.dry: U.save_texts(a.texts, a.T, a.fmt, a.fps)
print('\n'.join(log)); print(len(log), '字')
