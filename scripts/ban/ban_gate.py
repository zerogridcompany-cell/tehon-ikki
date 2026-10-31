# 段7 門（全部まとめて）：書き出した mp4 を手本に重ねて数字にする
#  ① 絵：違う画素（1コマで明るさの差 >24 の画素の割合）・手本は動くのにうちは止まっとるコマ・悪い板
#  ② 切り替え：板の頭のコマで、書き出しは手本と何コマずれたか（同じ測り方で両方を測った差）
#  ③ 音：相互相関のずれ ms・音は絵の何ms後（30〜150Hz の鳴り始め）・20ms 窓のスペクトルの差
#  ④ 字：板ごとの代表コマを書き出しから切って読み、CapCut の字の墨の箱を手本と比べる（px）→ out/moji.json（ban_hosei.py が読む）
# 使い方：python3 ban_gate.py <ban の置き場> <書き出し.mp4>   → out/gate_<名前>.json・終わりに 門 ✅/🔴
import json, os, re, sys, subprocess
import numpy as np, librosa
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D); sys.path.insert(0, os.path.join(D, '..', 'tools'))
from ban_lib import Ban
from oto_ms import tachiagari
b = Ban(sys.argv[1]); OUT = sys.argv[2]; REF = b.ref(); FPS = b.FPS; st = b.states(); os.makedirs(b.p('out'), exist_ok=True)
sw, sh = 480, int(round(480 * b.H / b.W / 2) * 2)
def gray(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-vf', f'scale={sw}:{sh},format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, sh, sw).astype(np.int16)
gr, go = gray(REF), gray(OUT); n = min(len(gr), len(go)); gr, go = gr[:n], go[:n]
px = (np.abs(gr - go) > 24).mean(axis=(1, 2)) * 100
dr = np.abs(np.diff(gr, axis=0)).mean(axis=(1, 2)); do = np.abs(np.diff(go, axis=0)).mean(axis=(1, 2))
moving = dr > 0.15; miss = moving & (do < 0.05)
res = dict(px_med=float(np.median(px)), px_p90=float(np.percentile(px, 90)), px_max=float(px.max()), moving=int(moving.sum()), miss=int(miss.sum()))
print(f'① 違う画素：中央値 {np.median(px):.2f}%・上10% {np.percentile(px, 90):.2f}%・最大 {px.max():.2f}%（コマ {int(px.argmax())}）／手本が動くコマ {int(moving.sum())}・うちが止まっとる {int(miss.sum())}')
rows = sorted([(px[s['f0']:min(s['f1'], n)].mean(), s['i'], int(miss[s['f0']:min(s['f1'], n) - 1].sum())) for s in st if s['f0'] < n], reverse=True)
print('   悪い板：' + '・'.join(f"{r[1]}({r[0]:.1f}%{'・止' + str(r[2]) if r[2] else ''})" for r in rows[:8]))
def peak(d, j):
    w = d[max(0, j - 3):j + 4]; return (int(np.argmax(w)) + max(0, j - 3)) if len(w) and w.max() > 0.3 else None
EV = [s['f0'] for s in st[1:]]; offs = []
for f in EV:
    kr, ko = peak(dr, f - 1), peak(do, f - 1); offs.append(None if kr is None or ko is None else ko - kr)
ok = [o for o in offs if o is not None]
res.update(cuts=len(EV), cut_exact=sum(o == 0 for o in ok), cut_1=sum(abs(o) <= 1 for o in ok), cut_none=offs.count(None))
print(f'② 切り替え {len(EV)}回：ぴったり {res["cut_exact"]}・±1コマ {res["cut_1"]}・見つからん {res["cut_none"]}')
def wav(p, sr=44100):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32)
ar, ao = wav(REF), wav(OUT); L = min(len(ar), len(ao)); lo, hi = int(L * 0.1), int(L * 0.9)
best, bl = -1, 0
for step, rng in ((22, range(-8820, 8821, 22)), (1, None)):
    for lag in (rng if rng else range(bl - 22, bl + 23)):
        if lo + lag < 0 or hi + lag > len(ao): continue
        v = float(np.dot(ao[lo + lag:hi + lag], ar[lo:hi]))
        if v > best: best, bl = v, lag
res['oto_ms'] = bl / 44.1
def av(y, d):
    T = np.array([x['t'] for x in tachiagari(y, 44100, band=(30, 150))]); out = []
    for f in EV:
        k = peak(d, f - 1)
        if k is None or not len(T): continue
        t = (k + 1) / FPS; j = np.argmin(abs(T - t)); dt = (T[j] - t) * 1000
        if abs(dt) < 120: out.append(dt)
    return np.array(out)
mr, mo = av(ar, dr), av(ao, do)
print(f'③ 音のずれ {bl / 44.1:+.2f} ms（＋＝遅い）')
for nm, m in (('手本', mr), ('書き出し', mo)):
    if len(m): print(f'   {nm}：音は絵の {np.median(m):+.1f} ms 後（四分位 {np.percentile(m, 25):+.1f}〜{np.percentile(m, 75):+.1f}）・音が先 {int((m < 0).sum())}/{len(m)}')
res['av_ref'] = float(np.median(mr)) if len(mr) else None; res['av_out'] = float(np.median(mo)) if len(mo) else None
a2, o2 = wav(REF, 22050), wav(OUT, 22050); m2 = min(len(a2), len(o2))
Rr = librosa.amplitude_to_db(np.abs(librosa.stft(a2[:m2], n_fft=1024, hop_length=441)) + 1e-6); Oo = librosa.amplitude_to_db(np.abs(librosa.stft(o2[:m2], n_fft=1024, hop_length=441)) + 1e-6)
dd = np.abs(Rr - Oo).mean(0); res['spec_db_med'] = float(np.median(dd))
print(f'   20ms 窓のスペクトルの差：中央値 {np.median(dd):.1f}dB・6dB 超え {int((dd > 6).sum())}/{len(dd)}')
# ④ 字
ED = b.p('out', 'fr_' + os.path.splitext(os.path.basename(OUT))[0]); os.makedirs(ED, exist_ok=True)
sel = '+'.join(f"eq(n\\,{s['rep']})" for s in st)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', OUT, '-vf', f"select='{sel}'", '-vsync', '0', f'{ED}/e%03d.png'], check=True)
for k, f in enumerate(sorted(x for x in os.listdir(ED) if x.startswith('e'))): os.replace(f'{ED}/{f}', f'{ED}/s{k:02d}.png')
open(ED + '.tsv', 'w').write(subprocess.run([b.p('ocr_en')] + [f'{ED}/s{s["i"]:02d}.png' for s in st], capture_output=True, text=True).stdout)
from PIL import Image
RT, RE = b.rows(), b.rows(ED + '.tsv'); mo_ = []
for s in st:
    i = s['i']; gt = b.gray(i); ge = np.asarray(Image.open(f'{ED}/s{i:02d}.png').convert('L'), np.float32); used = set()
    for t, box in RT.get(i, []):
        if not b.capcut(i, t): continue
        it, _ = b.ink_box(gt, box); best = None
        for t2, b2 in RE.get(i, []):
            if tuple(b2) in used: continue
            cx, cy = (b2[0] + b2[2]) / 2 - (box[0] + box[2]) / 2, (b2[1] + b2[3]) / 2 - (box[1] + box[3]) / 2
            if abs(cx) < 40 and abs(cy) < 25:
                sim = len(set(t2.replace(' ', '')) & set(t.replace(' ', ''))) / max(1, len(set(t.replace(' ', ''))))
                if sim > 0.6 and (best is None or abs(cx) + abs(cy) < best[0]): best = (abs(cx) + abs(cy), b2)
        if not best: mo_.append(dict(i=i, t=t, bx=box[0] // 10, miss=True)); continue
        used.add(tuple(best[1])); ie, _ = b.ink_box(ge, best[1])
        mo_.append(dict(i=i, t=t, bx=box[0] // 10, dx=(ie[0] + ie[2]) / 2 - (it[0] + it[2]) / 2, dy=(ie[1] + ie[3]) / 2 - (it[1] + it[3]) / 2,
                        dw=(ie[2] - ie[0]) - (it[2] - it[0]), wt=it[2] - it[0], dh=(ie[3] - ie[1]) - (it[3] - it[1]), dl=ie[0] - it[0], dr=ie[2] - it[2]))
okm = [o for o in mo_ if not o.get('miss')]
json.dump(mo_, open(b.p('out', 'moji.json'), 'w'), ensure_ascii=False, indent=0, default=float)
if okm:
    for k, nm in (('dx', '横の真ん中'), ('dy', '縦の真ん中'), ('dl', '左の端'), ('dr', '右の端'), ('dh', '高さ')):
        v = np.array([abs(o[k]) for o in okm]); res['moji_' + k] = [float(np.median(v)), float(v.max()), int((v > 2).sum())]
        print(f'④ 字の{nm}のずれ：中央値 {np.median(v):.1f}px・最大 {v.max():.1f}px・2px超え {int((v > 2).sum())}/{len(v)}')
    print(f'   書き出しで見つからん字 {len(mo_) - len(okm)}')
gate = res['cut_1'] == len(EV) and abs(res['oto_ms']) <= 10 and (res['av_ref'] is None or abs(res['av_out'] - res['av_ref']) <= 10) and res['miss'] <= max(2, res['moving'] // 100) \
       and okm and res['moji_dx'][0] <= 1 and res['moji_dx'][2] <= max(3, len(okm) // 100)
res['gate'] = bool(gate)
json.dump(res, open(b.p('out', f'gate_{os.path.basename(OUT)}.json'), 'w'), ensure_ascii=False, indent=1)
print('門', '✅' if gate else '🔴'); sys.exit(0 if gate else 1)
