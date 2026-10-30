# 立ち上がりごとに、棚の候補を実際に置いて「その場所の手本との近さ」が上がる物だけ残す
import json, numpy as np, librosa, soundfile as sf
SR=22050; NF=1024; HOP=256
ref,_=librosa.load('ref.wav',sr=SR,mono=True); base,_=librosa.load('mix_now.wav',sr=SR); base=np.pad(base,(0,max(0,len(ref)-len(base))))[:len(ref)]
res,_=librosa.load('sfx/residual_m.wav',sr=SR)
ev=json.load(open('sfx/picks.json')); lib=[s for s in json.load(open('sfx/library.json')) if not any(k in s['path'] for k in ['本人の動画','収益','ナレ','voice','声'])]
def melf(y): return librosa.power_to_db(librosa.feature.melspectrogram(y=y,sr=SR,n_fft=NF,hop_length=HOP,n_mels=48,fmin=60,fmax=10000)+1e-10)
LM=[]
for s in lib:
    try:
        y,_=librosa.load(s['path'],sr=SR,mono=True); y,_i=librosa.effects.trim(y,top_db=40)
        if len(y)>SR*0.03: LM.append((s['path'],y,melf(y[:int(SR*2.5)])))
    except Exception: pass
def local(mix,a,b):
    A=melf(ref[a:b]); B=melf(mix[a:b]); return float(np.corrcoef(A.ravel(),B.ravel())[0,1]) - 0.02*float(np.abs(A.mean(1)-B.mean(1)).mean())
sfx=np.zeros(len(ref)); kept=[]
for e in ev:
    t=int(e['t']*SR); d=int(max(e['dur'],0.1)*SR); a=max(0,t-int(0.1*SR)); b=min(len(ref),t+d+int(0.25*SR))
    q=melf(res[t:t+d]); cand=[]
    for path,y,m in LM:     # 形の近さで上位12本に絞る（重なる長さだけ・帯ごとに標準化）
        L=min(q.shape[1],m.shape[1])
        if L<2: continue
        x1=q[:,:L]; x2=m[:,:L]; c=np.corrcoef(x1.ravel(),x2.ravel())[0,1] - 0.15*abs(np.log((m.shape[1]+1)/(q.shape[1]+1)))
        cand.append((c,path,y))
    cand.sort(key=lambda x:-x[0]); cur=sfx+base; s0=local(cur,a,b); best=(s0,None,0,None)
    for c,path,y in cand[:12]:
        yy=y[:min(len(y),len(ref)-t)]
        g=np.sqrt((res[t:t+len(yy)][:d]**2).mean()/((yy[:d]**2).mean()+1e-12))
        g=min(g, 1.2*np.abs(res[t:t+len(yy)]).max()/(np.abs(yy).max()+1e-9))   # 山は手本の残りの1.2倍まで
        for gg in (g*0.7,g,g*1.4):
            tmp=cur.copy(); tmp[t:t+len(yy)]+=yy*gg; s=local(tmp,a,b)
            if s>best[0]+0.003: best=(s,path,gg,yy)
    if best[1]:
        sfx[t:t+len(best[3])]+=best[3]*best[2]; kept.append(dict(t=e['t'],sfx=best[1],gain=round(float(best[2]),4),before=round(s0,3),after=round(best[0],3)))
        print(e['t'], best[1].split('/')[-1], round(s0,3),'→',round(best[0],3), flush=True)
sf.write('sfx/sfx_track.wav',librosa.resample(sfx,orig_sr=SR,target_sr=44100),44100); json.dump(kept,open('sfx/kept.json','w'),ensure_ascii=False,indent=0)
print('残した', len(kept), '/', len(ev))
