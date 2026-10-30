# 曲のつなぎ方をビームで選ぶ：1秒ごとに「続ける（曲の位置を速さ分だけ進める）」か「別の所へ飛ぶ（罰）」
import sys, json, numpy as np, librosa
from scipy.signal import fftconvolve
sr=22050; H=256; fps=sr/H; W=int(2*fps)
def mel(y): return np.log(librosa.feature.melspectrogram(y=y,sr=sr,n_mels=48,hop_length=H,fmin=60,fmax=8000)+1e-5)
R=mel(librosa.load('narr/music.wav',sr=sr)[0])
songs=sys.argv[1].split(','); rates=[float(x) for x in sys.argv[2].split(',')]; PEN=float(sys.argv[3]) if len(sys.argv)>3 else 0.15
M={}
for si,f in enumerate(songs):
    y0,_=librosa.load(f,sr=sr)
    for r in rates:
        y=librosa.resample(y0,orig_sr=sr,target_sr=int(round(sr/r))) if abs(r-1)>1e-4 else y0
        m=mel(y); cs=np.cumsum(np.pad(m,((0,0),(1,0))),1); cs2=np.cumsum(np.pad(m**2,((0,0),(1,0))),1)
        mu=(cs[:,W:]-cs[:,:-W])/W; sd=np.sqrt(np.maximum((cs2[:,W:]-cs2[:,:-W])/W-mu**2,1e-8)); sd=np.maximum(sd,np.percentile(sd,30))
        M[(si,r)]=(m,sd,mu.mean(0)<np.percentile(mu.mean(0),5))
T=list(range(0,R.shape[1]-W,int(fps)))
def allscores(k):
    q=R[:,k:k+W]; q=(q-q.mean(1,keepdims=True))/(q.std(1,keepdims=True)+1e-6); out={}
    for key,(m,sd,sil) in M.items():
        xc=np.stack([fftconvolve(m[i],q[i][::-1],mode='valid') for i in range(m.shape[0])]); sc=(xc/(W*sd)).mean(0); sc[sil]=-1; out[key]=sc
    return out
beam=[(0.0,[])]   # (点, [(t, song, rate, 曲の位置フレーム)])
for ti,k in enumerate(T):
    S=allscores(k); top=[]
    for key,sc in S.items():
        for j in np.argsort(-sc)[:6]: top.append((float(sc[j]),key,int(j)))
    nb=[]
    for tot,path in beam:
        if path:
            _,si,r,j=path[-1]; key=(si,r); jj=j+int(round(fps))   # 1秒後（その速さの曲で）＝フレームは同じ数だけ進む
            sc=S[key]
            if jj<len(sc): nb.append((tot+float(sc[jj]),path+[(k/fps,si,r,jj)]))
        for v,key,j in top: nb.append((tot+v-(PEN if path else 0),path+[(k/fps,key[0],key[1],j)]))
    nb.sort(key=lambda x:-x[0]); beam=nb[:30]
tot,path=beam[0]; segs=[]
for t,si,r,j in path:
    at=j*H/sr*r   # 元の曲の秒
    if segs and segs[-1]['f']==songs[si] and segs[-1]['rate']==r and abs((segs[-1]['at']+(t-segs[-1]['t_at'])*r)-at)<0.15: segs[-1]['t1']=round(t+1,2); continue
    segs.append(dict(t0=round(t,2),t1=round(t+1,2),f=songs[si],rate=r,at=round(at,3),t_at=round(t,2)))
segs[0]['t0']=0.0; segs[-1]['t1']=76.42
for a,b in zip(segs,segs[1:]): a['t1']=b['t0']
json.dump(segs,open(sys.argv[4] if len(sys.argv)>4 else 'bgm/segs_beam.json','w'),indent=0)
print('平均の点', round(tot/len(T),3)); [print(g) for g in segs]
