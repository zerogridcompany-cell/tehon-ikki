# 使い方: python3 kouzou.py <作業>（<作業>/kouzou/kyoku.json・picture.json・<作業>/oto/narr/fa.json・oto/hako/hako.json を読む）
# 構造の地図＋つながり：曲の拍・絵の出来事・言葉の頭・効果音を1本の時間に並べ、
# 区間ごとに「絵の変わり目は何に合わせとるか」を、たまたま重なる割合（ずらし100回）と比べて決める
import json, numpy as np, librosa
SR = 22050
import sys
W = sys.argv[1] if len(sys.argv) > 1 else '.'   # 作業フォルダ（kouzou/ と oto/ がある所）
S = json.load(open(f'{W}/kouzou/kyoku.json'))   # [{name,a,b,f,mode(rs|ts),r,at0(=手本0秒の時の曲の秒)}]
O = f'{W}/oto/'
def song_beats(s):
    s0 = s['at0'] + s['a'] * s['r']; off = max(0, s0 - 3)
    y = librosa.load(O + s['f'], sr=SR, offset=off, duration=(s['b'] - s['a']) * s['r'] + 6)[0]
    tempo, bt = librosa.beat.beat_track(y=y, sr=SR, units='time')
    # 小節の頭＝4拍のうち低音の打ちが一番強い位相
    oe = librosa.onset.onset_strength(y=librosa.effects.preemphasis(y, coef=-0.97), sr=SR); tt = librosa.times_like(oe, sr=SR)
    st = np.interp(bt, tt, oe); ph = int(np.argmax([st[k::4].mean() for k in range(4)]))
    bt = (bt + off - s['at0']) / s['r']; m = (bt >= s['a'] - 0.6) & (bt <= s['b'] + 0.6)
    idx = np.arange(len(bt)); bars = bt[(idx % 4 == ph)]
    return bt[m], bars[(bars >= s['a'] - 0.6) & (bars <= s['b'] + 0.6)], float(np.atleast_1d(tempo)[0]) / s['r']
P = json.load(open(f'{W}/kouzou/picture.json')); FPS = P['fps']; ev = P['events']
words = [w['start'] for w in json.load(open(O + 'narr/fa.json'))['words'] if w['text'].strip()]
sfx = [e['t'] for e in json.load(open(O + 'hako/hako.json'))['3〜5 効果音'] if e['hako'] in (3, 4) and e['db'] > -46]
TOL = 2.0 / FPS   # 2コマ
rng = np.random.default_rng(0); out = dict(sections=[], rules=[])
def hit(ts, grid):
    if len(grid) == 0 or len(ts) == 0: return 0.0
    g = np.sort(np.asarray(grid)); return float(np.mean([np.min(np.abs(g - t)) <= TOL for t in ts]))
for s in S:
    bt, bars, bpm = song_beats(s); a, b = s['a'], s['b']
    half = np.sort(np.concatenate([bt, (bt[:-1] + bt[1:]) / 2])); q = np.sort(np.concatenate([half, (half[:-1] + half[1:]) / 2]))
    clocks = {'小節の頭': bars, '1拍': bt, '半拍': half, '4分の1拍': q,
              '言葉の頭': [w for w in words if a - 1 <= w <= b + 1], '効果音': [x for x in sfx if a - 1 <= x <= b + 1],
              '3コマごと': np.arange(a, b, 3 / FPS)}
    sec = dict(name=s['name'], a=a, b=b, bpm=round(bpm, 1), beats=[round(x, 3) for x in bt], bars=[round(x, 3) for x in bars], kinds={})
    for kind in ('cut', 'punch', 'flash', 'all'):
        ts = [e['t'] for e in ev if a <= e['t'] < b and (kind == 'all' or e['kind'] == kind)]
        if len(ts) < 3: continue
        res = {}
        for cn, g in clocks.items():
            obs = hit(ts, g)
            base = np.mean([hit([(t - a + rng.uniform(0, b - a)) % (b - a) + a for t in ts], g) for _ in range(100)])
            res[cn] = dict(hit=round(obs, 3), guuzen=round(float(base), 3), bai=round(obs / max(base, 1e-3), 2))
        # 決め：たまたまの1.5倍以上で、当たりが一番多い物（細かい網ほどたまたまも増えるので「倍」で選ぶ）
        good = {k: v for k, v in res.items() if v['bai'] >= 1.5 and v['hit'] >= 0.3}
        pick = max(good, key=lambda k: (good[k]['hit'] - good[k]['guuzen'])) if good else 'なし（決まった物差し無し）'
        sec['kinds'][kind] = dict(n=len(ts), res=res, pick=pick)
    out['sections'].append(sec)
json.dump(out, open(f'{W}/kouzou/kouzou.json', 'w'), ensure_ascii=False)
for s in out['sections']:
    print(f"■ {s['name']} {s['a']}-{s['b']}s BPM {s['bpm']} 拍{len(s['beats'])}")
    for k, v in s['kinds'].items():
        top = sorted(v['res'].items(), key=lambda kv: -(kv[1]['hit'] - kv[1]['guuzen']))[:3]
        print(f"   {k:5s} {v['n']:3d}本 → {v['pick']}   ", ' / '.join(f"{n} {x['hit']:.0%}(偶然{x['guuzen']:.0%})" for n, x in top))
