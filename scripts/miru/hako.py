# 動画の音を7つの箱に分ける（声・音楽・曲っぽい効果音・編集の効果音・物の音・環境音・聞こえ方の加工）
# 使い方:
#   python3 hako.py <手本の音 .wav/.mp4> <出す所> [--cuts cuts.txt|手本.mp4] [--sep <demucsの4本の置き場>] [--sfx-src 残り.wav]
# 出る物: <出す所>/hako.json（全部の数字）・hako.md（人が読む表）・hako.png（箱ごとの譜面）
# 元＝/oto-bunrui の hako.py（2026-11-02 に tehon-ikki に同梱）。demucs が無い Mac では librosa の HPSS で粗く分けて先へ進む（声は分けられん）
import sys, os, json, argparse, subprocess, numpy as np, librosa, soundfile as sf
from collections import Counter

ap = argparse.ArgumentParser()
ap.add_argument('src'); ap.add_argument('out')
ap.add_argument('--cuts', help='カットの秒の一覧（1行1つ）か、手本の mp4（scdet で出す）')
ap.add_argument('--sep', help='demucs の vocals/drums/bass/other.wav がある所（無ければ作る）')
ap.add_argument('--sfx-src', help='効果音を拾う元（BGM を引いた残り等）。無ければ 音楽の層から拾う')
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
SR = 44100; HOP = 512; FPS = SR / HOP
NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# ---- 0. 音を用意して4つに分ける ----
wav = os.path.join(a.out, 'src.wav')
if not os.path.exists(wav):
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', a.src, '-vn', '-ac', '2', '-ar', str(SR), wav], check=True)
sep = a.sep
if not sep:
    sep = os.path.join(a.out, 'sep', 'htdemucs', 'src')
    if not os.path.exists(os.path.join(sep, 'vocals.wav')):
        ok = False
        import importlib.util
        if importlib.util.find_spec('demucs') is not None:
            for dev in ('mps', 'cpu'):   # Intel の Mac・古い torch は mps が無い
                if subprocess.run([sys.executable, '-m', 'demucs', '-n', 'htdemucs', '-d', dev, '-o', os.path.join(a.out, 'sep'), wav]).returncode == 0:
                    ok = True; break
        if not ok:
            # 🟡 demucs が無い・動かん＝librosa の HPSS で粗く分ける（声＝無音・太鼓＝打つ音・ベース＝150Hz 未満・残り＝その他）
            msg = 'demucs が無い（か動かん）＝声と曲を粗く分けた（声の層は無音）・pip install demucs で細かく分かる'
            print('🟡', msg)
            if os.environ.get('TI_SKIP_LOG'): open(os.environ['TI_SKIP_LOG'], 'a').write(f'⏭️ 飛ばした：demucs の4つ分け（理由：{msg}）\n')
            os.makedirs(sep, exist_ok=True)
            y_, _ = librosa.load(wav, sr=SR, mono=False); y_ = np.atleast_2d(y_)
            harm = np.stack([librosa.effects.hpss(c)[0] for c in y_]); perc = y_ - harm
            import scipy.signal as _ss
            lo = _ss.sosfiltfilt(_ss.butter(4, 150, 'lowpass', fs=SR, output='sos'), harm, axis=-1)
            for k, v in (('vocals', np.zeros_like(y_)), ('drums', perc), ('bass', lo), ('other', harm - lo)):
                sf.write(os.path.join(sep, f'{k}.wav'), v.T, SR)
def load(p, mono=True):
    y, _ = librosa.load(p, sr=SR, mono=mono); return y
mix_st = load(wav, mono=False); mix = mix_st.mean(0); N = len(mix)
fit = lambda y: np.pad(y, [(0, 0)] * (y.ndim - 1) + [(0, max(0, N - y.shape[-1]))])[..., :N]
S = {k: fit(load(os.path.join(sep, f'{k}.wav'), mono=False)) for k in ['vocals', 'drums', 'bass', 'other']}
voc = S['vocals'].mean(0); music_st = S['drums'] + S['bass'] + S['other']; music = music_st.mean(0)
rmsdb = lambda y, fl=2048: 20 * np.log10(librosa.feature.rms(y=y, frame_length=fl, hop_length=HOP)[0] + 1e-9)

def segs(mask, min_gap=0.3, min_len=0.2):
    out = []; on = None
    for i, m in enumerate(np.append(mask, False)):
        if m and on is None: on = i
        if not m and on is not None: out.append([on / FPS, i / FPS]); on = None
    merged = []
    for s in out:
        if merged and s[0] - merged[-1][1] < min_gap: merged[-1][1] = s[1]
        else: merged.append(s)
    return [[round(x, 3), round(y, 3)] for x, y in merged if y - x >= min_len]

# ---- カットの秒 ----
cuts = []
if a.cuts:
    if a.cuts.endswith(('.mp4', '.mov', '.webm')):
        r = subprocess.run(['ffmpeg', '-nostdin', '-i', a.cuts, '-vf', 'scdet=t=10', '-f', 'null', '-'], capture_output=True, text=True)
        cuts = [float(l.split('lavfi.scd.time:')[1].split()[0]) for l in r.stderr.splitlines() if 'lavfi.scd.time:' in l]
    else:
        cuts = [float(l) for l in open(a.cuts) if l.strip()]
cuts = np.array(sorted(cuts))

# ---- 1. 声 ----
vdb = rmsdb(voc); v_on = vdb > max(-40, np.percentile(vdb, 95) - 25)
voice = []
for s0, s1 in segs(v_on):
    # 1秒ごとに声の高さを測る（ナレと本人の声が続いとる区間も分けられるように）
    for w0 in np.arange(s0, s1, 1.0):
        w1 = min(s1, w0 + 1.0)
        if w1 - w0 < 0.3: continue
        y = voc[int(w0 * SR):int(w1 * SR)]
        f0, vf, _ = librosa.pyin(y, fmin=60, fmax=400, sr=SR, hop_length=HOP)
        f = np.nanmedian(f0) if np.any(~np.isnan(f0)) else np.nan
        voice.append(dict(t0=round(float(w0), 3), t1=round(float(w1), 3), f0=None if np.isnan(f) else round(float(f), 1)))
# 人を分ける：声の指紋（resemblyzer）で窓をまとめる。無ければ声の高さ
try:
    from resemblyzer import VoiceEncoder, preprocess_wav
    enc = VoiceEncoder(verbose=False); E = []
    for v in voice:
        y = librosa.resample(voc[int(v['t0'] * SR):int(v['t1'] * SR)], orig_sr=SR, target_sr=16000)
        E.append(enc.embed_utterance(preprocess_wav(y, source_sr=16000)))
    E = np.array(E); lab = [-1] * len(E); cent = []
    # 長い窓から順に、近い人（似とる度 0.80 以上）に入れる。無ければ新しい人
    for i in np.argsort([-(v['t1'] - v['t0']) for v in voice]):
        sims = [float(E[i] @ c / np.linalg.norm(c)) for c in cent]
        if sims and max(sims) >= 0.80: k = int(np.argmax(sims)); cent[k] = cent[k] + E[i]
        else: k = len(cent); cent.append(E[i].copy())
        lab[i] = k
    # 似た人（中心どうし 0.72 以上）は同じ人にまとめる
    for i in range(len(cent)):
        for j in range(i):
            if lab.count(i) and lab.count(j) and float(cent[i] @ cent[j] / np.linalg.norm(cent[i]) / np.linalg.norm(cent[j])) >= 0.72:
                lab = [j if l == i else l for l in lab]; cent[j] = cent[j] + cent[i]
    # 0.6秒より短い窓は当てにならん＝長い方の隣と同じ人にする
    for i, v in enumerate(voice):
        if v['t1'] - v['t0'] < 0.6:
            nb = [k for k in (i - 1, i + 1) if 0 <= k < len(voice)]
            if nb: lab[i] = lab[max(nb, key=lambda k: voice[k]['t1'] - voice[k]['t0'])]
    # 窓が1つしかない人は一番近い人に寄せる
    big = [k for k in range(len(cent)) if lab.count(k) >= 2] or [0]
    for i in range(len(lab)):
        if lab[i] not in big: lab[i] = max(big, key=lambda k: float(E[i] @ cent[k] / np.linalg.norm(cent[k])))
    order = {k: j for j, k in enumerate(sorted(big, key=lambda k: -lab.count(k)))}
    for v, l in zip(voice, lab): v['hito'] = 'P%d' % order[l]
    centers = [float(np.median([v['f0'] for v in voice if v['hito'] == 'P%d' % j and v['f0']] or [0])) for j in range(len(order))]
except ImportError:
    fs = np.array(sorted(v['f0'] for v in voice if v['f0'])); centers = [float(np.median(fs))] if len(fs) else []
    for v in voice: v['hito'] = 'P0'
# 同じ人の窓をつなぐ
vj = []
for v in voice:
    if vj and vj[-1]['hito'] == v['hito'] and v['t0'] - vj[-1]['t1'] < 0.35: vj[-1]['t1'] = v['t1']; vj[-1]['f0s'].append(v['f0'])
    else: vj.append(dict(v, f0s=[v['f0']]))
voice = [dict(t0=v['t0'], t1=v['t1'], hito=v['hito'], f0=round(float(np.median([x for x in v['f0s'] if x] or [0])), 1)) for v in vj]

# ---- 2. 音楽 ----
mdb = rmsdb(music); m_on = mdb > max(-45, np.percentile(mdb, 95) - 30)
tempo, beats = librosa.beat.beat_track(y=music, sr=SR, hop_length=HOP, units='time')
tempo = float(np.atleast_1d(tempo)[0]); beats = np.array(beats)
# 小節の頭＝低い音が一番強い拍の並び（4拍ごと）
low = librosa.feature.rms(y=librosa.effects.preemphasis(S['bass'].mean(0) + S['drums'].mean(0), coef=-0.9), hop_length=HOP)[0]
ph = int(np.argmax([low[(beats[k::4] * FPS).astype(int).clip(0, len(low) - 1)].mean() for k in range(4)])) if len(beats) >= 8 else 0
downbeats = beats[ph::4]
chroma = librosa.feature.chroma_cqt(y=librosa.effects.harmonic(S['other'].mean(0) + S['bass'].mean(0)), sr=SR, hop_length=HOP).mean(1)
maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]); mnr = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
ks = [(np.corrcoef(chroma, np.roll(maj, i))[0, 1], NOTES[i] + ' major') for i in range(12)] + [(np.corrcoef(chroma, np.roll(mnr, i))[0, 1], NOTES[i] + ' minor') for i in range(12)]
key = max(ks)[1]
grid16 = np.concatenate([np.linspace(b0, b1, 5)[:-1] for b0, b1 in zip(beats[:-1], beats[1:])]) if len(beats) > 1 else np.array([])
def near(arr, t): return float(np.min(np.abs(arr - t))) if len(arr) else 9.9

# ---- 3〜5. 効果音の出来事 ----
src = fit(load(a.sfx_src)) if a.sfx_src else (S['other'].mean(0) + S['drums'].mean(0))
on = librosa.onset.onset_strength(y=src, sr=SR, hop_length=HOP)
pk = librosa.util.peak_pick(on, pre_max=4, post_max=4, pre_avg=12, post_avg=12, delta=np.percentile(on, 85) * 0.5, wait=4)
sdb = rmsdb(src, 1024); M = np.abs(librosa.feature.melspectrogram(y=src, sr=SR, hop_length=HOP, n_mels=64)) + 1e-9; LM = np.log(M)
def shape_at(p, w=8):
    x = LM[:, p:p + w]; x = np.pad(x, ((0, 0), (0, w - x.shape[1]))); x = x - x.mean(); return x.ravel() / (np.linalg.norm(x) + 1e-9)
events = []
for i, p in enumerate(pk):
    peak = sdb[p:p + 5].max()
    if peak < -48: continue
    q = p + 1
    while q < len(sdb) and q < p + int(3 * FPS) and sdb[q] > peak - 20: q += 1
    if i + 1 < len(pk): q = min(q, pk[i + 1])
    y = src[p * HOP:max(q, p + 4) * HOP]; d = len(y) / SR
    Sx = np.abs(librosa.stft(y, n_fft=1024, hop_length=128)) + 1e-9
    cen = librosa.feature.spectral_centroid(S=Sx, sr=SR)[0]; flat = float(np.mean(librosa.feature.spectral_flatness(S=Sx)))
    n3 = max(2, len(cen) // 3); c0, c1 = float(np.median(cen[:n3])), float(np.median(cen[-n3:]))
    tonal = float(np.mean(Sx.max(0) / Sx.mean(0)))
    fr = librosa.fft_frequencies(sr=SR, n_fft=1024); lowr = float(Sx[fr < 150].sum() / Sx.sum())
    env = sdb[p:max(q, p + 2)]; pk_pos = float(np.argmax(env) / max(1, len(env) - 1))
    f0 = None
    if tonal > 20 and d >= 0.04:
        ff, _, _ = librosa.pyin(y, fmin=80, fmax=4000, sr=SR, frame_length=2048, hop_length=256)
        if np.any(~np.isnan(ff)): f0 = float(np.nanmedian(ff))
    t = p / FPS
    # 形で種類（細かい名前）
    if d > 0.4 and (c1 > c0 * 1.4 or pk_pos > 0.75): kind = 'ライザー（上がる・吸い込み）'
    elif lowr > 0.55 and d >= 0.25: kind = 'サブドロップ／ブーム（ドゥーン）'
    elif c1 < c0 * 0.7 and d > 0.3: kind = 'ダウンリフター（下がる）'
    elif lowr > 0.3 and d >= 0.12: kind = 'インパクト（ドン）'
    elif d < 0.08 and cen.mean() > 2500: kind = 'カチッ（クリック）'
    elif tonal > 25 and flat < 0.05: kind = 'ピッ（電子音・音程あり）'
    elif flat > 0.25 and d > 0.2: kind = 'グリッチ／ノイズ'
    elif d > 0.15 and flat > 0.08: kind = 'シュッ（whoosh）'
    elif d < 0.15 and 400 < cen.mean() < 3500: kind = 'ポン（pop）'
    else: kind = 'トッ（短い打撃）'
    events.append(dict(t=round(t, 3), dur=round(d, 3), db=round(float(peak), 1), kind=kind, centroid=int(cen.mean()), tonal=round(tonal, 1), flat=round(flat, 3), low=round(lowr, 2),
                       note=None if not f0 else NOTES[int(round(librosa.hz_to_midi(f0))) % 12] + str(int(round(librosa.hz_to_midi(f0))) // 12 - 1),
                       beat_ms=round(near(grid16, t) * 1000), down_ms=round(near(downbeats, t) * 1000), cut_ms=round(near(cuts, t) * 1000) if len(cuts) else None,
                       in_music=bool(m_on[min(p, len(m_on) - 1)]), _p=int(p)))
# 曲の中の繰り返し：同じ形が 半小節・1・2・4小節 前か後ろの音楽の層にもある＝BGM の音の一部とみなして箱2へ
bar = 4 * 60 / tempo if tempo > 0 else 2.0
MM = np.log(np.abs(librosa.feature.melspectrogram(y=music, sr=SR, hop_length=HOP, n_mels=64)) + 1e-9)
def mshape(p, w=8):
    x = MM[:, max(0, p):p + w]; x = np.pad(x, ((0, 0), (0, w - x.shape[1]))); x = x - x.mean(); return x.ravel() / (np.linalg.norm(x) + 1e-9)
for e in events:
    sh = mshape(e['_p']); rep = 0
    for k in (bar / 2, bar, 2 * bar, 4 * bar):
        for sg in (-1, 1):
            q = e['_p'] + int(round(sg * k * FPS))
            if 0 <= q < MM.shape[1] - 8:
                best = max(float(sh @ mshape(q + j)) for j in range(-2, 3))
                if best > 0.8: rep += 1
    e['kurikaeshi'] = rep
# タイピング＝カチッ・トッが 6〜16 回/秒で3つ以上続く
ts = [e for e in events if e['kind'] in ('カチッ（クリック）', 'トッ（短い打撃）')]
for x, y in zip(ts, ts[1:]):
    if 0.06 <= y['t'] - x['t'] <= 0.17: x['typing'] = y['typing'] = True
MUSICAL = ('ライザー', 'サブドロップ', 'ダウンリフター', 'インパクト')
for e in events:
    k = e['kind']; on_cut = e['cut_ms'] is not None and e['cut_ms'] <= 70; on_beat = e['in_music'] and e['beat_ms'] <= 35
    if e.get('typing'): e['kind'] = 'タイピング'
    if e['kurikaeshi'] >= 3 and e['in_music'] and not on_cut:
        e['hako'] = 2; e['why'] = '1小節ごとに同じ形＝曲の太鼓・音の一部'
    elif k.startswith(MUSICAL):
        e['hako'] = 3; e['why'] = '曲っぽい形' + ('・拍の上' if on_beat else '') + ('・カットの上' if on_cut else '')
    elif on_cut or k.startswith(('シュッ', 'ポン', 'カチッ', 'ピッ', 'グリッチ')) or e.get('typing'):
        e['hako'] = 4; e['why'] = '絵の動きの音' + ('・カットの上' if on_cut else '') + ('・音程あり＝調も合わせる' if e['note'] else '')
    elif e['flat'] > 0.12 and not on_beat:
        e['hako'] = 5; e['why'] = '自然なザラつき・拍にもカットにも乗らん＝物の音の候補（目で確かめる）'
    else:
        e['hako'] = 4; e['why'] = '短い打撃・どれにも当たらん＝編集の音とみなす'
    e['awaseru'] = '拍' if (e['hako'] == 3 and on_beat) or e['hako'] == 2 else ('カット' if on_cut else ('映っとる物' if e['hako'] == 5 else '絵の動き'))
    e.pop('_p', None)

# ---- 6. 環境音（声も曲も出来事も無いのに薄く鳴り続ける所） ----
quiet = (~v_on) & (~m_on)
floor = rmsdb(mix - voc - music) if True else None
amb_mask = quiet & (floor > -60) & (floor < -30)
ambience = [dict(t0=s0, t1=s1, db=round(float(np.median(floor[int(s0 * FPS):int(s1 * FPS)])), 1)) for s0, s1 in segs(amb_mask, 0.3, 1.5)]

# ---- 7. 聞こえ方 ----
def lufs(path):
    r = subprocess.run(['ffmpeg', '-nostdin', '-i', path, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True)
    l = [x for x in r.stderr.splitlines() if x.strip().startswith('I:')]; return float(l[-1].split()[1]) if l else None
def width(st):
    m = (st[0] + st[1]) / 2; s = (st[0] - st[1]) / 2; return round(float(np.sqrt((s ** 2).mean() / ((m ** 2).mean() + 1e-12))), 3)
both = v_on & m_on; only_m = (~v_on) & m_on
duck = round(float(np.median(mdb[both]) - np.median(mdb[only_m])), 1) if both.sum() > 10 and only_m.sum() > 10 else None
silence = segs(rmsdb(mix) < -55, 0.05, 0.15)
fade_in = round(float(rmsdb(mix)[int(0.5 * FPS)] - rmsdb(mix)[1]), 1); fade_out = round(float(rmsdb(mix)[-int(0.5 * FPS)] - rmsdb(mix)[-2]), 1)
kakou = dict(lufs=lufs(wav), dakkingu_db=duck, haba=dict(koe=width(S['vocals']), ongaku=width(music_st), zentai=width(mix_st)),
             mu_on=silence, fade_in_db=fade_in, fade_out_db=fade_out)

# ---- まとめて書く ----
H = {'1 声': voice, '2 音楽': dict(bpm=round(tempo, 1), key=key, beats=len(beats), atama=[round(float(x), 3) for x in downbeats[:8]], kukan=segs(m_on, 1.0, 2.0)),
     '3〜5 効果音': events, '6 環境音': ambience, '7 聞こえ方': kakou, 'cuts': len(cuts)}
json.dump(H, open(os.path.join(a.out, 'hako.json'), 'w'), ensure_ascii=False, indent=1)
cnt = Counter(e['hako'] for e in events); kc = Counter((e['hako'], e['kind']) for e in events)
L = [f'# 音の7つの箱（{os.path.basename(a.src)}・{N / SR:.1f}秒）', '',
     '| 箱 | 数 | 中身 | 何に合わせて置く |', '|---|---|---|---|',
     f"| 1 声 | {len(voice)}区間 | 人 {len(centers)}（高さ {', '.join(f'{c:.0f}Hz' for c in centers)}） | 台本と口 |",
     f"| 2 音楽 | {len(H['2 音楽']['kukan'])}区間＋太鼓の出来事 {cnt.get(2, 0)} | BPM {tempo:.1f}・{key} | 曲の版（速さ・高さ） |",
     f'| 3 曲っぽい効果音 | {cnt.get(3, 0)} | ' + '・'.join(f'{k} {v}' for (h, k), v in kc.most_common() if h == 3) + ' | 拍と調 |',
     f'| 4 編集の効果音 | {cnt.get(4, 0)} | ' + '・'.join(f'{k} {v}' for (h, k), v in kc.most_common() if h == 4) + ' | 絵の動き（カット・字・寄り） |',
     f'| 5 物の音（候補） | {cnt.get(5, 0)} | 目で確かめる | 映っとる物 |',
     f'| 6 環境音 | {len(ambience)}区間 | ' + ('・'.join(f"{x['t0']}〜{x['t1']}s" for x in ambience[:5]) or 'なし') + ' | 場面の頭から終わり |',
     f"| 7 聞こえ方 | — | {kakou['lufs']} LUFS・BGM の沈み {duck}dB・広がり 声{kakou['haba']['koe']}/曲{kakou['haba']['ongaku']}・無音 {len(silence)}か所 | 全体 |", '',
     '## 効果音の一覧（箱3〜5）', '', '| 秒 | 箱 | 種類 | 長さ | 音名 | 拍ずれms | カットずれms | 合わせる | 理由 |', '|---|---|---|---|---|---|---|---|---|']
L += [f"| {e['t']} | {e['hako']} | {e['kind']} | {e['dur']} | {e['note'] or ''} | {e['beat_ms']} | {e['cut_ms'] if e['cut_ms'] is not None else ''} | {e['awaseru']} | {e['why']} |" for e in events]
open(os.path.join(a.out, 'hako.md'), 'w').write('\n'.join(L) + '\n')

# 譜面の絵（箱ごとの段・拍の線・カットの線）
try:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
except ImportError:   # 絵は無くても数字（hako.json）は出す
    print('\n'.join(L[:12])); print('🟡 matplotlib が無い＝hako.png は飛ばした'); sys.exit(0)
plt.rcParams['font.family'] = ['Hiragino Sans', 'Arial Unicode MS', 'sans-serif']
fig, ax = plt.subplots(figsize=(max(12, N / SR / 4), 4.5))
for b in downbeats: ax.axvline(b, color='#ccc', lw=0.6)
for c in cuts: ax.axvline(c, ymin=0.0, ymax=0.06, color='#e33', lw=0.8)
for v in voice: ax.plot([v['t0'], v['t1']], [7, 7], lw=6, color='#4a7', solid_capstyle='butt')
for s0, s1 in H['2 音楽']['kukan']: ax.plot([s0, s1], [6, 6], lw=6, color='#58c', solid_capstyle='butt')
col = {2: '#58c', 3: '#c5a', 4: '#e93', 5: '#986'}
for e in events: ax.scatter(e['t'], 8 - e['hako'] if e['hako'] != 2 else 6, s=10 + 4 * max(0, e['db'] + 50), color=col[e['hako']], alpha=0.8)
for x in ambience: ax.plot([x['t0'], x['t1']], [2, 2], lw=6, color='#aaa', solid_capstyle='butt')
ax.set_yticks([7, 6, 5, 4, 3, 2]); ax.set_yticklabels(['1 声', '2 音楽', '3 曲っぽい', '4 編集', '5 物', '6 環境'])
ax.set_xlim(0, N / SR); ax.set_xlabel('秒（灰＝小節の頭・赤＝カット）'); plt.tight_layout(); plt.savefig(os.path.join(a.out, 'hako.png'), dpi=110)
print('\n'.join(L[:12]))
