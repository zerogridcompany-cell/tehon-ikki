# Shazam と同じ仕組みの指紋：スペクトルの山の組（f1, f2-f1, dt）を、時刻のずれがそろって何個一致するかで数える
# 使い方: python3 fp.py <手本の音.wav> <山のフォルダ,…> <出力.json> [最低一致数]
import sys, os, glob, json, numpy as np, librosa
from scipy.ndimage import maximum_filter
from collections import defaultdict, Counter
SR=22050; NF=1024; HOP=128; FAN=6; DT=(1,48); DF=80
def peaks(y):
    S=np.abs(librosa.stft(y,n_fft=NF,hop_length=HOP))[:400]   # 〜8.6kHz
    L=librosa.amplitude_to_db(S+1e-9,ref=np.max)
    mx=maximum_filter(L,size=(11,7)); P=np.argwhere((L==mx)&(L>-70)&(L>np.median(L)+8))
    # 1秒あたり多くても 60 個（強い順）
    if len(P)==0: return P
    st=L[P[:,0],P[:,1]]; keep=[]
    for t0 in range(0,L.shape[1],int(SR/HOP)):
        m=(P[:,1]>=t0)&(P[:,1]<t0+int(SR/HOP)); idx=np.where(m)[0]
        keep+=list(idx[np.argsort(-st[idx])[:120]])
    P=P[sorted(keep)]; return P[np.argsort(P[:,1])]
def hashes(P):
    out=[]
    for i,(f1,t1) in enumerate(P):
        n=0
        for f2,t2 in P[i+1:]:
            dt=t2-t1
            if dt<DT[0]: continue
            if dt>DT[1]: break
            if abs(f2-f1)>DF: continue
            out.append(((int(f1),int(f2-f1),int(dt)),int(t1))); n+=1
            if n>=FAN: break
    return out
if __name__=='__main__':
    ref,roots,outp=sys.argv[1],sys.argv[2].split(','),sys.argv[3]; MIN=int(sys.argv[4]) if len(sys.argv)>4 else 8
    y,_=librosa.load(ref,sr=SR,mono=True); RH=defaultdict(list)
    for h,t in hashes(peaks(y)): RH[h].append(t)
    print('手本の指紋', sum(len(v) for v in RH.values()), flush=True)
    files=[p for r in roots for p in glob.glob(r+'/**/*',recursive=True) if p.lower().endswith(('.wav','.mp3','.ogg','.m4a','.webm','.opus','.flac','.aif','.aiff'))]
    hits=[]
    for k,p in enumerate(files):
        try: z,_=librosa.load(p,sr=SR,mono=True,duration=900)
        except Exception: continue
        if len(z)<SR*0.05: continue
        H=hashes(peaks(z)); 
        if not H: continue
        C=Counter()
        for h,tf in H:
            for tr in RH.get(h,()): C[tr-tf]+=1
        if not C: continue
        # 近いずれ（±1コマ）をまとめて数える
        best=[]
        for off,c in C.most_common(20):
            tot=c+C.get(off-1,0)+C.get(off+1,0); best.append((tot,off))
        best.sort(reverse=True)
        used=[]
        for tot,off in best:
            if tot<MIN or any(abs(off-u)<int(0.2*SR/HOP) for u in used): continue
            used.append(off); hits.append(dict(file=p,ref_t=round(off*HOP/SR,3),count=int(tot),file_hashes=len(H),ratio=round(tot/len(H),3)))
        if k%200==0: print(k,'/',len(files),flush=True)
    hits.sort(key=lambda h:(-h['count']))
    json.dump(hits,open(outp,'w'),ensure_ascii=False,indent=0); print('一致', len(hits))
    for h in hits[:30]: print(h['count'], h['ratio'], h['ref_t'], os.path.basename(h['file']))
