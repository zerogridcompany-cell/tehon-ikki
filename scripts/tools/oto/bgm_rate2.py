# 速い版：帯ごとのピアソン相関を FFT で全位置。手本 a〜b 秒が曲の何秒・何倍速か
import sys, numpy as np, librosa
from scipy.signal import fftconvolve
sr=22050; H=256
def mel(y): return np.log(librosa.feature.melspectrogram(y=y,sr=sr,n_mels=48,hop_length=H,fmin=60,fmax=8000)+1e-5)
f,a,b=sys.argv[1],float(sys.argv[2]),float(sys.argv[3]); rates=[float(x) for x in sys.argv[4].split(',')] if len(sys.argv)>4 else list(np.arange(0.94,1.081,0.005))
src=sys.argv[5] if len(sys.argv)>5 else 'narr/music.wav'
q=mel(librosa.load(src,sr=sr,offset=a,duration=b-a)[0]); q=(q-q.mean(1,keepdims=True))/(q.std(1,keepdims=True)+1e-6); W=q.shape[1]
song,_=librosa.load(f,sr=sr); res=[]
for r in rates:
    y=librosa.resample(song,orig_sr=sr,target_sr=int(round(sr/r))) if abs(r-1)>1e-4 else song
    M=mel(y); n=M.shape[1]-W+1
    if n<1: continue
    cs=np.cumsum(np.pad(M,((0,0),(1,0))),1); cs2=np.cumsum(np.pad(M**2,((0,0),(1,0))),1)
    mu=(cs[:,W:]-cs[:,:-W])/W; sd=np.sqrt(np.maximum((cs2[:,W:]-cs2[:,:-W])/W-mu**2,1e-8))
    xc=np.stack([fftconvolve(M[i],q[i][::-1],mode='valid') for i in range(M.shape[0])])
    sd=np.maximum(sd,np.percentile(sd,30)); sc=(xc/(W*sd)).mean(0); sc[mu.mean(0)<np.percentile(mu.mean(0),5)]=-1; j=int(np.argmax(sc)); res.append((float(sc[j]),r,round(j*H/sr*r,3)))
res.sort(reverse=True)
for x in res[:5]: print(f"{x[0]:.3f} 倍率{x[1]:.3f} 曲の{x[2]}s ←手本{a}s")
