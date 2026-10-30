# 指紋の候補を「引き算」で確かめる：候補をその時刻に一番合う大きさで置いて、残りの音がどれだけ消えるか（全く同じ音なら大きく消える）
import sys, os, json, numpy as np, librosa
SR=22050; NF=1024; HOP=256
res,_=librosa.load(sys.argv[1],sr=SR,mono=True); H=json.load(open(sys.argv[2])); out=sys.argv[3]
R=np.abs(librosa.stft(res,n_fft=NF,hop_length=HOP))
for h in H:
    y,_=librosa.load(h['file'],sr=SR,mono=True,duration=900)
    t=h['ref_t']; best=(0,0,0)
    for dt in np.arange(-0.012,0.0121,0.003):   # 数ミリ秒の細かいずれも探す
        a=int((t+dt)*SR); z=np.zeros_like(res)
        if a<0: seg=y[-a:]; a=0
        else: seg=y
        n=min(len(seg),len(res)-a); z[a:a+n]=seg[:n]
        Z=np.abs(librosa.stft(z,n_fft=NF,hop_length=HOP)); m=Z>Z.max()*0.01
        if m.sum()<10: continue
        g=np.median(R[m]/(Z[m]+1e-9)); g=min(g,np.percentile(R[m]/(Z[m]+1e-9),40)*1.5)
        before=(R[m]**2).sum(); after=(np.maximum(R[m]-g*Z[m],0)**2).sum()
        red=1-after/before
        if red>best[0]: best=(red,dt,g)
    h['removed']=round(float(best[0]),3); h['dt']=round(float(best[1]),4); h['gain']=round(float(best[2]),4)
    h['ref_t']=round(t+best[1],4)
    # 🔴大きさの引き算は低い「ドゥーン」系なら別の音でも8割消える（10/29 実測）＝波形でも合うか見る（同じファイルなら波形も消える）
    a=int(h['ref_t']*SR); w0=max(a-int(0.01*SR),0); seg=res[w0:a+len(y)+int(0.01*SR)]; yy=y[:max(len(seg)-int(0.02*SR),1)]
    if len(yy)>100 and len(seg)>len(yy):
        c=np.correlate(seg,yy,'valid'); e=np.convolve(seg**2,np.ones(len(yy)),'valid')+1e-12
        h['wave']=round(float(np.max(c**2/((yy@yy+1e-12)*e))),3)
    else: h['wave']=0.0
H.sort(key=lambda h:-h['removed']); json.dump(H,open(out,'w'),ensure_ascii=False,indent=0)
for h in H[:40]: print(h['removed'], h.get('wave'), h['count'], h['ref_t'], os.path.basename(h['file']))
