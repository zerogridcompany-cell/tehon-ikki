# 行ごとに、候補の全部を「1語ずつ合わせた後」に手本の声と比べて一番の1本を選ぶ（本当の物差しで選ぶ）
import json, os, glob, subprocess, sys, numpy as np, librosa, pyrubberband as rb
K=open(os.path.expanduser('~/.elevenlabs_key')).read().strip(); SR=44100; sr=22050
FA=[w for w in json.load(open('narr/fa.json'))['words'] if w['text'].strip()]
L=json.load(open('narr/lines.json')); B=json.load(open('narr/best.json'))
V,_=librosa.load('sep/htdemucs/ref/vocals.wav',sr=sr)
REAL=json.load(open("narr/real.json")); idx=0; refw=[]
for i,(a,b,t) in enumerate(L):
    for x in REAL:
        if i==x['before_line']: idx+=len(x['text'].split())
    n=len(t.split()); refw.append(FA[idx:idx+n]); idx+=n
def melf(y): return librosa.power_to_db(librosa.feature.melspectrogram(y=y,sr=sr,n_mels=48,hop_length=256,fmin=60,fmax=10000)+1e-10)
def fa(take,text):
    fj=f"narr/fa_takes/{os.path.basename(take)}.json"
    if not os.path.exists(fj):
        r=subprocess.run(['curl','-s','-X','POST','https://api.elevenlabs.io/v1/forced-alignment','-H',f'xi-api-key: {K}','-F',f'file=@{take}','-F',f'text={text}'],capture_output=True,text=True); open(fj,'w').write(r.stdout)
    return [w for w in json.load(open(fj)).get('words',[]) if w['text'].strip()]
def warp(take,text,rw):
    ow=fa(take,text); y,_=librosa.load(take,sr=SR)
    if len(ow)!=len(rw): return None,None
    pad=0.04; x=[max(0,ow[0]['start']-pad)]; z=[rw[0]['start']-pad]
    for o,r in zip(ow,rw):
        for ko in ('start','end'):
            if o[ko]>x[-1]+0.01 and r[ko]>z[-1]+0.01: x.append(o[ko]); z.append(r[ko])
    x.append(min(len(y)/SR,ow[-1]['end']+0.12)); z.append(rw[-1]['end']+0.12); x=np.array(x); z=np.array(z)
    seg=y[int(x[0]*SR):int(x[-1]*SR)]; xs=((x-x[0])*SR).astype(int); zs=((z-z[0])*SR).astype(int)
    xs[-1]=len(seg); keep=np.concatenate([[True],np.diff(xs)>0]); xs,zs=xs[keep],zs[keep]; xs[-1]=len(seg)
    for k in range(1,len(zs)): s=xs[k]-xs[k-1]; zs[k]=zs[k-1]+int(np.clip(zs[k]-zs[k-1],s*0.5,s*2.0))
    return rb.timemap_stretch(seg,SR,list(zip(xs,zs))), z[0]
def score(out,st,a,b):
    y=librosa.resample(out,orig_sr=SR,target_sr=sr); tr=np.zeros(len(V)); s=int(st*sr); n=min(len(y),len(V)-s); tr[s:s+n]=y[:n]
    A=melf(V[int(a*sr):int((b+0.1)*sr)]); Bm=melf(tr[int(a*sr):int((b+0.1)*sr)]); return float(np.corrcoef(A.ravel(),Bm.ravel())[0,1])
TEXT={}   # 句読点違いの候補の文
for p in glob.glob('narr/takes/*_v*.mp3'): pass
VAR=json.load(open('narr/var_text.json')) if os.path.exists('narr/var_text.json') else {}
idxs=[int(x) for x in sys.argv[1].split(',')] if len(sys.argv)>1 else range(len(L))
for i in idxs:
    a,b,t=L[i]; best=(-1,None)
    for take in sorted(glob.glob(f'narr/takes/{i:02d}_*.mp3')):
        text=VAR.get(os.path.basename(take),t)
        out,st=warp(take,text,refw[i])
        if out is None: continue
        s=score(out,st,a,b)
        if s>best[0]: best=(s,take,text)
    old=B[str(i)]['take']; B[str(i)]['take']=best[1]; B[str(i)]['text']=best[2]; B[str(i)]['warp_score']=round(best[0],3)
    print(i, 'いちばん', os.path.basename(best[1]), round(best[0],3), '(前', os.path.basename(old),')', flush=True)
json.dump(B,open('narr/best.json','w'),indent=0)
