# 区間ごとに、細かい帯（STFT の周波数ごと・なめらかに）で手本の音色へ合わせる。in の層を手本の層 ref に寄せる
import sys, json, numpy as np, librosa, soundfile as sf
from scipy.ndimage import uniform_filter1d
SR=44100; NF=4096; HOP=1024
inp, refp, segp, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
Y,_=librosa.load(inp,sr=SR,mono=False); Y=np.atleast_2d(Y); R,_=librosa.load(refp,sr=SR,mono=True)
N=min(Y.shape[1],len(R)); Y=Y[:,:N]; R=R[:N]
segs=json.load(open(segp)); RS=np.abs(librosa.stft(R,n_fft=NF,hop_length=HOP)); YM=np.abs(librosa.stft(Y.mean(0),n_fft=NF,hop_length=HOP))
G=np.ones_like(RS)
for g in segs:
    a=int(g['t0']*SR/HOP); b=int(g['t1']*SR/HOP)
    d=np.median(20*np.log10(RS[:,a:b]+1e-7)-20*np.log10(YM[:,a:b]+1e-7),axis=1)   # 周波数ごとの差（中央値）
    d=uniform_filter1d(d,25); d=np.clip(d,-24,12); G[:,a:b]=(10**(d/20))[:,None]
G=uniform_filter1d(G,9,axis=1)   # 区間の境目をなめらかに
outY=np.stack([librosa.istft(librosa.stft(Y[c],n_fft=NF,hop_length=HOP)*G,hop_length=HOP,length=N) for c in range(Y.shape[0])])
sf.write(out,outY.T,SR); print('音色を合わせた', len(segs),'区間')
