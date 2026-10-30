# 似とる度で効果音を選ぶ：手本の残り（効果音だけ）の出来事ごとに、棚から一番似た音を選んで 0〜100% を付ける
# 似とる度＝ CLAP の近さ・メルの形（時間をずらして最良）・音の強さの動き・明るさ を、
#   0%＝でたらめな棚の音の真ん中、100%＝手本の音そのもの に直して重みで合わせた値
# 使い方: python3 sfx_sim_match.py <目録.npz> <出力.json>
import sys, json, numpy as np, librosa, torch
from transformers import ClapModel, ClapProcessor
SR=22050; HL=256; NM=48; MF=int(1.5*SR/HL)+1; W=dict(clap=0.40,mel=0.30,env=0.20,bright=0.10)
Z=np.load(sys.argv[1]); paths=Z['paths']; E=Z['emb'].astype(np.float32); MEL=Z['mel'].astype(np.float32); DUR=Z['dur']
res,_=librosa.load('sfx/residual_m2.wav',sr=SR,mono=True)
ev=json.load(open('sfx/bunrui.json'))
dev='mps' if torch.backends.mps.is_available() else 'cpu'
M=ClapModel.from_pretrained("laion/clap-htsat-unfused").to(dev).eval(); P=ClapProcessor.from_pretrained("laion/clap-htsat-unfused")
def melf(y):
    m=librosa.power_to_db(librosa.feature.melspectrogram(y=y,sr=SR,n_fft=1024,hop_length=HL,n_mels=NM,fmin=60,fmax=10000)+1e-10)
    mm=np.full((NM,MF),-100.0,np.float32); mm[:,:min(MF,m.shape[1])]=m[:,:MF]; return mm
def parts(q,c,L):
    # q,c＝メル（NM×MF）。L＝比べる長さ（コマ）。形・強さの動き・明るさ
    best=-1
    for s in range(0,4):                       # 立ち上がりのずれ（0〜3コマ＝0〜35ms）を許す
        a=q[:,:L]; b=c[:,s:s+L]
        if b.shape[1]<L: break
        best=max(best,np.corrcoef(a.ravel(),b.ravel())[0,1])
    ea=np.log10(np.sum(10**(q[:,:L]/10),0)+1e-10); eb=np.log10(np.sum(10**(c[:,:L]/10),0)+1e-10)
    env=np.corrcoef(ea,eb)[0,1] if ea.std()>1e-6 and eb.std()>1e-6 else 0
    w=np.arange(NM)[:,None]; pa=10**(q[:,:L]/10); pb=10**(c[:,:L]/10)
    ca=(w*pa).sum()/pa.sum(); cb=(w*pb).sum()/pb.sum(); bright=1-min(abs(ca-cb)/12,1)
    return float(best),float(env),float(bright)
# 出来事の手本の音（残りから）
Q=[]
for e in ev:
    t=int(e['t']*SR); d=max(e['dur'],0.25); a=max(t-int(0.01*SR),0); y=res[a:a+int(min(d+0.15,1.5)*SR)]
    Q.append((y,melf(y),max(int((min(d+0.15,1.5))*SR/HL),4)))
x=P(audios=[librosa.resample(q[0],orig_sr=SR,target_sr=48000) for q in Q],sampling_rate=48000,return_tensors='pt')
with torch.no_grad(): QE=torch.nn.functional.normalize(M.get_audio_features(**{k:v.to(dev) for k,v in x.items()}),dim=-1).cpu().numpy()
rng=np.random.default_rng(0); RND=rng.choice(len(paths),min(400,len(paths)),replace=False)
out=[]
for i,e in enumerate(ev):
    y,q,L=Q[i]; L=min(L,MF-4); cs=E@QE[i]
    # でたらめな 400本の値＝0% の基準
    r=np.array([[cs[j],*parts(q,MEL[j],L)] for j in RND]); base=np.median(r,0)
    def score(v):
        n=[(v[k]-base[k])/(1-base[k]+1e-9) for k in range(4)]; n=[min(max(z,0),1) for z in n]
        return sum(w*z for w,z in zip(W.values(),n))
    top=np.argsort(-cs)[:150]                  # CLAP の近い 150本だけ細かく見る
    cand=[]
    for j in top:
        if DUR[j] < min(e['dur'],1.0)*0.4: continue   # 手本より極端に短い音は外す
        v=[cs[j],*parts(q,MEL[j],L)]; cand.append((score(v),j,v))
    cand.sort(key=lambda z:-z[0]); s,j,v=cand[0]
    out.append(dict(t=e['t'],dur=e['dur'],db=e['db'],kind=e['kind'],sim=round(100*s,1),sfx=str(paths[j]),
        clap=round(float(v[0]),3),mel=round(v[1],3),env=round(v[2],3),bright=round(v[3],3),
        alt=[(round(100*c[0],1),str(paths[c[1]])) for c in cand[1:4]]))
    print(f"{e['t']:7.3f} {e['kind'][:6]} 似とる度 {100*s:5.1f}%  {paths[j].split('/')[-1]}",flush=True)
json.dump(out,open(sys.argv[2],'w'),ensure_ascii=False,indent=1)
ok=[o for o in out if o['sim']>=50]; print('50%以上', len(ok), '/', len(out))
