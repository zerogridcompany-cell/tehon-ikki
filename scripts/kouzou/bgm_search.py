# 手本の区間に一番合う（曲・速さの変え方・速さ・位置）を総当たり
# 物差し＝出来上がりと同じ「0.5秒ごとのメル（dB）の形の相関」の平均
# 速さの変え方: rs＝resample（速さと高さ一緒） / ts＝速さだけ（高さそのまま）
# 使い方: python3 tools/bgm_search.py <手本の音楽.wav> <t0> <t1> <曲,…> <出す.json> [速さの下,上,刻み]
import sys, json, numpy as np, librosa
from scipy.ndimage import zoom
from scipy.signal import fftconvolve
SR = 22050; H = 256; fps = SR / H; W = int(0.5 * fps)
ref, t0, t1, files, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4].split(','), sys.argv[5]
lo, hi, st = (float(x) for x in (sys.argv[6] if len(sys.argv) > 6 else '0.90,1.12,0.005').split(','))
def dbmel(y): return librosa.power_to_db(librosa.feature.melspectrogram(y=y, sr=SR, n_mels=64, hop_length=H, fmin=40, fmax=10000) + 1e-10)
A = dbmel(librosa.load(ref, sr=SR, offset=t0, duration=t1 - t0)[0]); n = A.shape[1]
An = (A - A.mean(1, keepdims=True)); An /= (np.linalg.norm(An) + 1e-9)
def exact(M, k):
    # 0.5秒ごとの相関の平均（oto_eval と同じ形）
    cs = []
    for j in range(0, n - W + 1, W):
        x = A[:, j:j + W].ravel(); z = M[:, k + j:k + j + W].ravel()
        if len(z) < len(x): return -1
        cs.append(np.corrcoef(x, z)[0, 1])
    return float(np.mean(cs))
res = []
for f in files:
    y, _ = librosa.load(f, sr=SR); M1 = dbmel(y); en = M1.max(0)
    loud = en > np.percentile(en, 20)   # 静かな所（曲の頭と終わり）に当たらんように
    for r in np.arange(lo, hi + 1e-9, st):
        for mode in ('ts', 'rs'):
            M = zoom(M1, (1, 1 / r), order=1) if mode == 'ts' else dbmel(librosa.resample(y, orig_sr=SR, target_sr=int(round(SR / r))))
            Mn = M - M.mean(1, keepdims=True)
            c = sum(fftconvolve(Mn[i], An[i][::-1], mode='valid') for i in range(64))
            norm = np.sqrt(np.convolve((Mn ** 2).sum(0), np.ones(n), mode='valid')) + 1e-9; c = c / norm
            ok = zoom(loud.astype(float), 1 / r, order=0)[:len(c)] > 0; c[:len(ok)][~ok] = -1
            for k in np.argsort(-c)[:3]:
                res.append(dict(f=f, mode=mode, rate=round(float(r), 4), k=int(k), rough=float(c[k])))
    print(f, len(res), flush=True)
res.sort(key=lambda x: -x['rough']); top = res[:40]
for x in top:
    y, _ = librosa.load(x['f'], sr=SR); M1 = dbmel(y)
    M = zoom(M1, (1, 1 / x['rate']), order=1) if x['mode'] == 'ts' else dbmel(librosa.resample(y, orig_sr=SR, target_sr=int(round(SR / x['rate']))))
    x['score'] = round(exact(M, x['k']), 4); x['song_at'] = round(x['k'] / fps * x['rate'], 3)
top.sort(key=lambda x: -x['score'])
json.dump(top, open(out, 'w'), indent=0)
for x in top[:8]: print(x['score'], x['f'].split('/')[-1], x['mode'], x['rate'], '曲の', x['song_at'], 's')
