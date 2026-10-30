# 手本の区間（ref の a〜b 秒）が、元の音のどこに・どの速さで入っとるかを測る
import sys, numpy as np, librosa
ref, a, b, src, s0, s1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4], float(sys.argv[5]), float(sys.argv[6])
sr=16000; hop=160
def feat(y):
    m=librosa.feature.melspectrogram(y=y,sr=sr,n_mels=64,hop_length=hop); m=np.log(m+1e-6)
    m=(m-m.mean(1,keepdims=True)); return m
yr,_=librosa.load(ref,sr=sr,offset=a,duration=b-a)
ys,_=librosa.load(src,sr=sr,offset=s0,duration=s1-s0)
best=None
for sp in np.arange(0.90,1.25,0.005):
    yrs=librosa.effects.time_stretch(yr,rate=1/sp) if abs(sp-1)>1e-3 else yr   # sp=元の秒/手本の秒
    fr=feat(yrs); fs=feat(ys); n=fr.shape[1]
    if fs.shape[1]<n: continue
    frn=fr/np.linalg.norm(fr)
    sc=[]
    for k in range(0,fs.shape[1]-n,2):
        w=fs[:,k:k+n]; sc.append((frn*w).sum()/np.linalg.norm(w))
    k=int(np.argmax(sc))*2; v=max(sc)
    if best is None or v>best[0]: best=(v,sp,s0+k*hop/sr)
print(f"相関 {best[0]:.3f}  速さ(元/手本) {best[1]:.3f}  元の始まり {best[2]:.3f}s ←手本 {a}s")
