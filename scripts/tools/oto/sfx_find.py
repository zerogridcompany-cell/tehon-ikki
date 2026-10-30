# 手本の音楽 −（うちの BGM）の残り＝効果音。立ち上がりごとに切って、棚の575本から一番似た音を選ぶ
import json, numpy as np, librosa, soundfile as sf
from scipy.ndimage import maximum_filter
SR=22050; NF=1024; HOP=256
R,_=librosa.load('narr/music.wav',sr=SR,mono=True); B,_=librosa.load('bgm/bgm_track.wav',sr=SR); B=np.pad(B,(0,max(0,len(R)-len(B))))[:len(R)]
SRf=librosa.stft(R,n_fft=NF,hop_length=HOP); SB=np.abs(librosa.stft(B,n_fft=NF,hop_length=HOP))
mask=np.clip(1-maximum_filter(SB,size=(3,7))*1.3/(np.abs(SRf)+1e-9),0,1)
res=librosa.istft(SRf*mask,hop_length=HOP,length=len(R)); sf.write('sfx/residual_m.wav',res,SR)
rms=librosa.feature.rms(y=res,frame_length=1024,hop_length=HOP)[0]; db=20*np.log10(rms+1e-9)
on=librosa.onset.onset_strength(y=res,sr=SR,hop_length=HOP)
pk=librosa.util.peak_pick(on,pre_max=6,post_max=6,pre_avg=20,post_avg=20,delta=np.percentile(on,85)*0.6,wait=8)
fps=SR/HOP; ev=[]
for p in pk:
    if db[min(p+2,len(db)-1)]<-42: continue
    # 長さ＝残りの大きさが立ち上がりから 18dB 落ちるまで（最大 2.5 秒・次の立ち上がりまで）
    peak=db[p:p+6].max(); q=p+1
    while q<len(db) and q<p+int(2.5*fps) and db[q]>peak-18: q+=1
    ev.append(dict(t=round(p/fps,3),dur=round((q-p)/fps,3),db=round(float(peak),1)))
for a,b in zip(ev,ev[1:]): a['dur']=min(a['dur'],round(b['t']-a['t'],3))
print(len(ev),'個')
def melf(y): return librosa.power_to_db(librosa.feature.melspectrogram(y=y,sr=SR,n_fft=NF,hop_length=HOP,n_mels=48,fmin=60,fmax=10000)+1e-10)
lib=json.load(open('sfx/library.json')); LM=[]
for s in lib:
    try:
        y,_=librosa.load(s['path'],sr=SR,mono=True); y,_i=librosa.effects.trim(y,top_db=40); LM.append((s['path'],melf(y),y))
    except Exception: pass
picks=[]
for e in ev:
    a=int(e['t']*SR)-int(0.02*SR); n=int(max(e['dur'],0.08)*SR)
    q=melf(res[max(0,a):a+n]); best=(-2,None,0)
    for path,m,y in LM:
        L=min(q.shape[1],m.shape[1]);
        if L<3: continue
        mm=np.full_like(q,-100.0); mm[:,:L]=m[:,:L]
        c=np.corrcoef(q.ravel(),mm.ravel())[0,1]
        if c>best[0]: best=(c,path,m.shape[1]/fps)
    e.update(score=round(float(best[0]),3),sfx=best[1],sfx_dur=round(best[2],2)); picks.append(e)
json.dump(picks,open('sfx/picks.json','w'),ensure_ascii=False,indent=0)
for e in picks: print(e['t'],e['dur'],e['db'],e['score'],e['sfx'].split('/')[-1] if e['sfx'] else None)
