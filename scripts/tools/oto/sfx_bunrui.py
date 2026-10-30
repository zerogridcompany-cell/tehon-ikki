# 手本の効果音を全部拾って、音の形で細かく分ける（長さ・高さ・音程・上がり下がり・雑音っぽさ）
import json, numpy as np, librosa
SR=22050; HOP=256
res,_=librosa.load('sfx/residual_m.wav',sr=SR)
rms=librosa.feature.rms(y=res,frame_length=1024,hop_length=HOP)[0]; db=20*np.log10(rms+1e-9)
on=librosa.onset.onset_strength(y=res,sr=SR,hop_length=HOP)
pk=librosa.util.peak_pick(on,pre_max=4,post_max=4,pre_avg=12,post_avg=12,delta=np.percentile(on,80)*0.5,wait=5)
fps=SR/HOP; ev=[]
for p in pk:
    peak=db[p:p+5].max()
    if peak<-45: continue
    q=p+1
    while q<len(db) and q<p+int(3*fps) and db[q]>peak-20: q+=1
    ev.append([p,q,peak])
for a,b in zip(ev,ev[1:]): a[1]=min(a[1],b[0])
rows=[]
for p,q,peak in ev:
    y=res[p*HOP:max(q,p+4)*HOP]; d=len(y)/SR
    S=np.abs(librosa.stft(y,n_fft=1024,hop_length=128))+1e-9
    cen=librosa.feature.spectral_centroid(S=S,sr=SR)[0]; flat=float(np.mean(librosa.feature.spectral_flatness(S=S)))
    c0,c1=float(np.median(cen[:max(2,len(cen)//3)])),float(np.median(cen[-max(2,len(cen)//3):]))
    tonal=float(np.mean(S.max(0)/S.mean(0)))
    att=float((db[p:p+3].max()-db[max(0,p-3)])) 
    if d<0.08 and cen.mean()>2500: k='カチッ（クリック・短い）'
    elif cen.mean()<900 and d>=0.15: k='ドン（低い打撃・ブーム）'
    elif tonal>25 and flat<0.05: k='ピッ／ピン（電子音・音程あり）'
    elif c1>c0*1.4 and d>0.3: k='上がる音（ライザー）'
    elif c1<c0*0.7 and d>0.15: k='下がる音（ダウン・ウーッシュ）'
    elif flat>0.25 and d>0.25: k='ザー（雑音・グリッチ・静電気）'
    elif d>0.15: k='シュッ（風切り・ウーッシュ）'
    else: k='トッ（短い打撃・ポップ）'
    rows.append(dict(t=round(p/fps,3),dur=round(d,3),db=round(float(peak),1),kind=k,centroid=int(cen.mean()),tonal=round(tonal,1),flat=round(flat,3)))
json.dump(rows,open('sfx/bunrui.json','w'),ensure_ascii=False,indent=0)
from collections import Counter
print(len(rows),'個'); [print(f'{v:3d} {k}') for k,v in Counter(r['kind'] for r in rows).most_common()]
