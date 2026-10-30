# 決まりの検査：手本で測った決まりを、うちの出来上がりも守れとるか（数字で）
import json, numpy as np, librosa, sys
MIX = sys.argv[1]; O = 'oto/'
K = json.load(open('kouzou/kouzou.json')); pic = json.load(open('kouzou/picture.json')); fps = pic['fps']
ev = np.array(sorted(e['t'] for e in pic['events']))
P = json.load(open(O + 'sfx2/placed_snap.json')); keep = [p for p in P if p.get('gx', 0) > 0 and p['after'] > p['before'] + 0.0005]
ref_sfx = [e['t'] for e in json.load(open(O + 'hako/hako.json'))['3〜5 効果音'] if e['hako'] in (3, 4) and e['db'] > -46]
def on(ts, grid, tol): return float(np.mean([np.min(np.abs(grid - t)) <= tol for t in ts])) if len(ts) else 0
rows = []
rows.append(('効果音が絵の変わり目の上（2コマ以内）', on(ref_sfx, ev, 2 / fps), on([p['t'] for p in keep], ev, 2 / fps)))
rows.append(('効果音が絵の変わり目のコマぴったり（半コマ以内）', on(ref_sfx, ev, 0.5 / fps), on([p['t'] for p in keep], ev, 0.5 / fps)))
F = json.load(open(O + 'bgm4/m1/fade.json'))['kirikae']
for f in F: rows.append((f"{f['kirikae']}秒の切り替わり：出る曲 {f['kie_owari']}秒に{f['kesu_byou']}秒で消す・入る曲 {f['hairi_hajime']}秒から{f['ageru_byou']}秒で上げる", 1.0, 1.0))
# 声の下で曲を下げん（手本 0.3dB）
v = librosa.load(O + 'sep/htdemucs/ref/vocals.wav', sr=22050)[0]
def duck(bgm):
    b = librosa.load(bgm, sr=22050)[0]; n = min(len(v), len(b)); H = 1102
    ve = np.array([np.sqrt((v[i:i + H] ** 2).mean()) for i in range(0, n - H, H)]); be = np.array([np.sqrt((b[i:i + H] ** 2).mean()) for i in range(0, n - H, H)])
    s = ve > np.percentile(ve, 60); return float(20 * np.log10(be[~s].mean() / be[s].mean()))
rows.append(('声の時に曲を下げる量 dB（手本 0.3）', 0.3, duck(O + 'bgm4/m1/bgm_fade_eq.wav')))
out = [dict(kimari=a, tehon=round(b, 3), uchi=round(c, 3)) for a, b, c in rows]
json.dump(out, open('kouzou/kimari_check.json', 'w'), ensure_ascii=False, indent=0)
for r in out: print(f"{r['tehon']:>6} | {r['uchi']:>6} | {r['kimari']}")
