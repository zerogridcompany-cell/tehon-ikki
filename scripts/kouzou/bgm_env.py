# 曲の「切り替わり方」まで写す：各曲を手本の時間に並べ（区間より広く）、手本の音楽の層に対して
# 0.05秒ごとに「どの曲がどの大きさで鳴っとるか」を非負の最小二乗（メルの大きさ）で出す → なめらかにして音量の動きとして掛ける
# 使い方: python3 tools/bgm_env.py <src.json> <出す所> [中央値の秒 ならしの秒 漏れの線dB 名前]
#   中央値・ならしを長くすると、揺れの無いきれいなフェードになる。漏れの線＝その曲の中央値よりこれだけ下は 0   src.json = [{name,f,mode,rate,song_at_t0(=手本0秒の時の曲の秒),t0,t1}]
import sys, json, numpy as np, librosa, soundfile as sf, pyrubberband as rb
from scipy.optimize import nnls
from scipy.ndimage import median_filter, uniform_filter1d
SRC = json.load(open(sys.argv[1])); OUT = sys.argv[2]; SR = 48000; HOP = 2400   # 0.05秒
mus = librosa.load('narr/music.wav', sr=SR)[0]; N = len(mus)
def render(s):
    t0, t1, r = s['t0'], s['t1'], s['rate']; a = max(0.0, s['at0'] + t0 * r - 0.1 * r)
    y, _ = librosa.load(s['f'], sr=SR, mono=False, offset=a, duration=(t1 - t0 + 0.4) * r); y = np.atleast_2d(y)
    if y.shape[0] == 1: y = np.vstack([y, y])
    if s['mode'] == 'rs': y = np.stack([librosa.resample(c, orig_sr=SR, target_sr=int(round(SR / r))) for c in y])
    elif abs(r - 1) > 1e-4: y = rb.time_stretch(y.T, SR, r, rbargs={'--fine': ''}).T
    lead = int((s['at0'] + t0 * r - a) / r * SR); y = y[:, lead:]
    out = np.zeros((2, N)); i0 = int(t0 * SR); n = min(y.shape[1], N - i0, int((t1 - t0) * SR)); out[:, i0:i0 + n] = y[:, :n]; return out
import os
MED, SM, GATE, TAG = (float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]) if len(sys.argv) > 6 else (0.35, 0.15, 99, 'env')
C = f'{OUT}/_src.npy'
if os.path.exists(C): Y = list(np.load(C))
else: Y = [render(s) for s in SRC]; np.save(C, np.stack(Y).astype(np.float32))
def melmag(x): return np.sqrt(librosa.feature.melspectrogram(y=x, sr=SR, n_fft=4096, hop_length=HOP, n_mels=48, fmin=40, fmax=12000))
R = melmag(mus); M = [melmag(y.mean(0)) for y in Y]; T = R.shape[1]
G = np.zeros((len(Y), T))
if os.path.exists(f'{OUT}/raw_g.npy'): G = np.load(f'{OUT}/raw_g.npy'); T = 0
for j in range(T):
    act = [k for k in range(len(Y)) if M[k][:, j].sum() > 1e-6]
    if not act: continue
    A = np.stack([M[k][:, j] for k in act], 1); g, _ = nnls(A, R[:, j])
    for k, v in zip(act, g): G[k, j] = v
np.save(f'{OUT}/raw_g.npy', G); T = G.shape[1]
for k in range(len(Y)):   # その曲がちゃんと鳴っとる所の中央値より GATE dB 下は漏れ＝0
    on = G[k][G[k] > 0]
    if len(on): G[k][G[k] < np.median(on) * 10 ** (-GATE / 20)] = 0
Gs = median_filter(G, size=(1, max(1, int(MED * 20) | 1))); Gs = uniform_filter1d(Gs, max(1, int(SM * 20)), axis=1)
np.save(f'{OUT}/{TAG}.npy', Gs)
t = np.arange(N) / SR; tf = np.arange(T) * HOP / SR; bgm = np.zeros((2, N))
for k, y in enumerate(Y): bgm += y * np.interp(t, tf, Gs[k])[None]
sf.write(f'{OUT}/bgm_{TAG}.wav', bgm.T, SR, subtype='FLOAT')
# 切り替わりの周りの大きさ（dB）を表に
rows = []
for tt in np.arange(0, N / SR, 0.25):
    j = int(tt * SR / HOP); rows.append([round(tt, 2)] + [round(20 * np.log10(Gs[k, j] + 1e-6), 1) for k in range(len(Y))])
json.dump(dict(names=[s['name'] for s in SRC], rows=rows), open(f'{OUT}/{TAG}.json', 'w'), ensure_ascii=False)
print('出した', OUT)
