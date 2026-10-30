# 切り替わりを「数字2つ×2曲」で決める：出る曲＝いつ消え終わるか・何秒で消すか／入る曲＝いつ入り始めるか・何秒で上げるか
# 手本の音楽の層に一番近い組を総当たり（メルの大きさを足し算で近似・0.5秒ごとの形の相関）
# 使い方: python3 tools/fade_fit.py bgm4 → bgm4/fade.json と bgm4/bgm_fade.wav
import sys, json, numpy as np, librosa, soundfile as sf
D = sys.argv[1]; SR = 48000; HOP = 1200; fr = SR / HOP
Y = np.load(f'{D}/_src.npy'); N = Y.shape[2]
mel = lambda x: librosa.feature.melspectrogram(y=x, sr=SR, n_fft=4096, hop_length=HOP, n_mels=64, fmin=40, fmax=10000) + 1e-10
R = mel(librosa.load('narr/music.wav', sr=SR)[0][:N]); P = [mel(y.mean(0)) for y in Y]; T = R.shape[1]; tf = np.arange(T) / fr
SEC = [(0.0, 10.0), (10.0, 17.0), (17.0, 31.95), (31.95, 62.0), (62.0, 76.42)]
L = []
for k, (a, b) in enumerate(SEC):   # 真ん中の大きさ＝手本÷曲（メルの中央値の比）
    m = (tf >= a + 0.5) & (tf <= b - 0.5); L.append(float(np.sqrt(np.median(R[:, m].sum(0)) / np.median(P[k][:, m].sum(0) + 1e-12))))
import os
LENS = [x for x in [0.03, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0] if x <= float(os.environ.get("MAXLEN", 9))]
def ramp_out(e, l): return np.clip((e - tf) / l, 0, 1)
def ramp_in(s, l): return np.clip((tf - s) / l, 0, 1)
def score(gk, a, b):
    m = (tf >= a) & (tf < b); W = int(0.5 * fr); X = sum(g[m] ** 2 * P[k][:, m] for k, g in gk.items()); Rm = R[:, m]
    cs = [np.corrcoef(np.log(X[:, j:j + W] + 1e-12).ravel(), np.log(Rm[:, j:j + W]).ravel())[0, 1] for j in range(0, m.sum() - W + 1, W)]
    return float(np.mean(cs))
out = []; G = {k: np.zeros(T) for k in range(5)}
for k, (a, b) in enumerate(SEC): G[k][(tf >= a) & (tf < b)] = L[k]
for i in range(4):
    A, B = i, i + 1; bd = SEC[i][1]; lo, hi = bd - 3.0, bd + 3.0
    pa = dict(e=bd, l=0.03); pb = dict(s=bd, l=0.03)
    def g_of(pa, pb):
        ga = L[A] * ramp_out(pa['e'], pa['l']) * (tf >= SEC[A][0]); gb = L[B] * ramp_in(pb['s'], pb['l']) * (tf < SEC[B][1]); return {A: ga, B: gb}
    best = score(g_of(pa, pb), lo, hi); start = best
    for it in range(2):
        for e in np.arange(bd - 1.5, bd + 2.51, 0.05):
            for l in LENS:
                v = score(g_of(dict(e=e, l=l), pb), lo, hi)
                if v > best: best, pa = v, dict(e=round(float(e), 2), l=l)
        for s in np.arange(bd - 2.5, bd + 1.01, 0.05):
            for l in LENS:
                v = score(g_of(pa, dict(s=s, l=l)), lo, hi)
                if v > best: best, pb = v, dict(s=round(float(s), 2), l=l)
    g = g_of(pa, pb); G[A] = np.where(tf < bd - 3, G[A], g[A]) if i > 0 else np.where(tf < SEC[A][0], 0, g[A]); 
    G[A] = np.minimum(G[A], g[A]) if i > 0 else g[A]
    G[B] = np.where(tf < bd + 3, g[B], G[B])
    out.append(dict(kirikae=bd, deru=f'曲{A}', kie_owari=pa['e'], kesu_byou=pa['l'], hairu=f'曲{B}', hairi_hajime=pb['s'], ageru_byou=pb['l'], mae=round(start, 3), ato=round(best, 3)))
    print(out[-1], flush=True)
t = np.arange(N) / SR; bgm = sum(Y[k] * np.interp(t, tf, G[k])[None] for k in range(5))
sf.write(f'{D}/bgm_fade.wav', bgm.T, SR, subtype='FLOAT'); json.dump(dict(ookisa=L, kirikae=out), open(f'{D}/fade.json', 'w'), ensure_ascii=False, indent=0)
