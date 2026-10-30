# Shazam で当てた曲の「聞き比べ」を作る：区間ごとに 手本（声を抜いた音楽）／本物の曲そのまま／本物を手本の速さに合わせた物／左右同時
import numpy as np, librosa, soundfile as sf, subprocess, os
SR = 48000; O = 'kikikurabe'
mus = librosa.load('narr/music.wav', sr=SR)[0]
bgm = librosa.load('bgm3/bgm_e1.wav', sr=SR)[0]
# (名前, 手本の始め, 終わり, 曲, 曲の何秒目（手本の始めの時）, 速さ)
S = [('A', 1, 9, 'bgm/ver/KCWvlQo4XJw.webm', 3.89 + 1, 1.0),
     ('B', 10, 17, 'bgm/Bad5zz0kbTs.webm', 10.472, 1.07),
     ('C', 18, 28, 'bgm/ver/FfzUkUVawaU.webm', 248.145 + 1, 1.0),
     ('D', 34, 44, 'bgm3/songs/6_4TUct8c14.webm', 34 - 17.763, 1.0),
     ('E', 63, 73, 'bgm/Bad5zz0kbTs.webm', 187.525 + 0.96, 0.96)]
def fade(y, f=int(0.15 * SR)): y = y.copy(); y[:f] *= np.linspace(0, 1, f); y[-f:] *= np.linspace(1, 0, f); return y
def norm(y): return y * (0.1 / (np.sqrt((y ** 2).mean()) + 1e-9))
def mp3(y, name):
    y = np.clip(y, -0.99, 0.99); w = f'{O}/{name}.wav'; sf.write(w, y.T if y.ndim > 1 else y, SR)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', w, '-b:a', '256k', f'{O}/{name}.mp3'], check=True); os.remove(w)
for k, a, b, f, at, r in S:
    t = norm(fade(mus[int(a * SR):int(b * SR)]))
    raw = librosa.load(f, sr=SR, offset=at, duration=(b - a) * r)[0]   # 曲そのまま（速さも高さも元のまま）
    aw = norm(fade(bgm[int(a * SR):int(b * SR)]))
    mp3(t, f'{k}1_tehon'); mp3(norm(fade(raw)), f'{k}2_honmono'); mp3(aw, f'{k}3_awase')
    mp3(np.vstack([t, aw]), f'{k}4_sayuu')
    print(k, 'ok')
