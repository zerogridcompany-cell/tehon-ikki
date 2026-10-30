# 似とる度 50% 以上の音だけを、手本の時刻に置く。置いて手本に近づく時だけ残す（大きさは手本の残りの山の1.2倍まで）
# 使い方: python3 sfx_sim_place.py <kept_sim.json> [しきい%=50]  → sfx/kept.json（前のは sfx/kept_before_sim.json に残す）
import sys, json, os, shutil, numpy as np, librosa
SR=22050; NF=1024; HOP=256; TH=float(sys.argv[2]) if len(sys.argv)>2 else 50
ref,_=librosa.load('ref.wav',sr=SR,mono=True); N=len(ref)
fit=lambda x: np.pad(x,(0,max(0,N-len(x))))[:N]
base=sum(fit(librosa.load(f,sr=SR,mono=True)[0]) for f in ['narr/narr_track_g.wav','narr/elon_track.wav','bgm/bgm_track.wav'])
res=fit(librosa.load('sfx/residual_m2.wav',sr=SR,mono=True)[0])
def melf(y): return librosa.power_to_db(librosa.feature.melspectrogram(y=y,sr=SR,n_fft=NF,hop_length=HOP,n_mels=48,fmin=60,fmax=10000)+1e-10)
def local(mix,a,b):
    A=melf(ref[a:b]); B=melf(mix[a:b]); return float(np.corrcoef(A.ravel(),B.ravel())[0,1]) - 0.02*float(np.abs(A.mean(1)-B.mean(1)).mean())
def load(p):
    y,_=librosa.load(p,sr=SR,mono=True); _,(i0,i1)=librosa.effects.trim(y,top_db=40); return y[i0:i1]
ev=[e for e in json.load(open(sys.argv[1])) if e['sim']>=TH]; ev.sort(key=lambda e:-e['sim'])
sfx=np.zeros(N); kept=[]; busy=[]
for e in ev:
    if any(a<=e['t']<b for a,b in busy): continue          # もう置いた音の本体の中＝同じ音の続き
    t=int(e['t']*SR); d=int(max(e['dur'],0.1)*SR); a=max(0,t-int(0.1*SR)); b=min(N,t+d+int(0.25*SR))
    s0=local(base+sfx,a,b); best=(0.0,None)
    for sim,p in [(e['sim'],e['sfx'])]+[tuple(x) for x in e['alt'] if x[0]>=TH]:
        try: y=load(p)[:N-t]
        except Exception: continue
        if len(y)<100: continue
        g=np.sqrt((res[t:t+d]**2).mean()/((y[:d]**2).mean()+1e-12)); g=min(g,1.2*np.abs(res[t:t+len(y)]).max()/(np.abs(y).max()+1e-9))
        b2=min(N,t+max(d,len(y))+int(0.25*SR)); r0=local(base+sfx,a,b2)   # 音の尻尾まで含めて測る（長い音が後ろを汚すのを止める）
        for gg in (g*0.5,g*0.7,g,g*1.4):
            z=sfx.copy(); z[t:t+len(y)]+=y*gg; s=local(base+z,a,b2)-r0
            if s>best[0]+0.002: best=(s,(p,gg,sim,y))
    if best[1]:
        p,gg,sim,y=best[1]; sfx[t:t+len(y)]+=y*gg; busy.append((e['t'],e['t']+min(len(y)/SR,e['dur']+0.15)))
        kept.append(dict(t=e['t'],sfx=p,gain=round(float(gg),4),sim=sim,kind=e['kind'],before=round(s0,3),gain_local=round(best[0],3)))
kept.sort(key=lambda k:k['t'])
if os.path.exists('sfx/kept.json') and not os.path.exists('sfx/kept_before_sim.json'): shutil.copy('sfx/kept.json','sfx/kept_before_sim.json')
json.dump(kept,open('sfx/kept.json','w'),ensure_ascii=False,indent=1)
print('50%以上の候補',len(ev),'→ 置いた',len(kept),'・似とる度 平均',round(np.mean([k['sim'] for k in kept]),1) if kept else 0,'% 最低',min([k['sim'] for k in kept]) if kept else 0)
