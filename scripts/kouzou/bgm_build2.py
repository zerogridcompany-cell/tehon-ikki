# BGM を「当たった区間」どおりに組む（48kHz・ステレオ）
# 区間: t0〜t1 を、曲 f の song_at（手本 t0 の時の曲の秒）から、mode=rs（速さと高さ一緒＝resample）か ts（速さだけ・高さそのまま）で rate 倍
# 音量は区間ごとに手本の音楽の層とそろえる（メルの大きさの中央値の比＝効果音や声の漏れに引っぱられん）
import sys, json, numpy as np, librosa, soundfile as sf, pyrubberband as rb
SR = 48000
spec = json.load(open(sys.argv[1])); out = sys.argv[2]
ref, _ = librosa.load('ref.wav', sr=SR, mono=False); N = ref.shape[1]
mus = librosa.load('narr/music.wav', sr=SR)[0]
track = np.zeros((2, N)); XF = int(0.03 * SR); info = []
def melmed(x):
    return float(np.median(librosa.feature.melspectrogram(y=x, sr=SR, n_mels=40, hop_length=1024).sum(0)) + 1e-12)
for g in spec:
    t0, t1, r = g['t0'], g['t1'], g['rate']; L = t1 - t0
    pad = 0.05
    a = max(0.0, g['song_at'] - pad * r)
    y, _ = librosa.load(g['f'], sr=SR, mono=False, offset=a, duration=(L + 2 * pad) * r + 0.3); y = np.atleast_2d(y)
    if y.shape[0] == 1: y = np.vstack([y, y])
    if g['mode'] == 'rs':   # 速さと高さが一緒に動く（sped up / slowed）
        y = np.stack([librosa.resample(c, orig_sr=SR, target_sr=int(round(SR / r))) for c in y])
    elif abs(r - 1) > 1e-4:   # 速さだけ（高さそのまま）＝CapCut の速さ変更の既定
        y = rb.time_stretch(y.T, SR, r, rbargs={'--fine': ''}).T
    lead = int((g['song_at'] - a) / r * SR); seg = y[:, lead:lead + int(L * SR) + XF]
    i0 = int(t0 * SR); n = min(seg.shape[1], N - i0); seg = seg[:, :n].copy()
    gain = np.sqrt(melmed(mus[i0:i0 + int(L * SR)]) / melmed(seg.mean(0)[:int(L * SR)])) * g.get('gain_x', 1.0)
    seg *= gain
    f = np.ones(n); f[:XF] = np.linspace(0, 1, XF); f[-XF:] = np.linspace(1, 0, XF); seg *= f
    track[:, i0:i0 + n] += seg; info.append(dict(t0=t0, t1=t1, gain=round(float(gain), 3)))
sf.write(out, track.T, SR, subtype='FLOAT'); print(json.dumps(info, ensure_ascii=False))
