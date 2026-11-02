# 1語ずつ合わせる：手本の語の時刻（Forced Alignment）と、録った1本の語の時刻をそろえて伸び縮み
import json, os, subprocess, numpy as np, librosa, soundfile as sf, pyrubberband as rb
K=open(os.path.expanduser(os.environ.get('TI_ELEVENLABS_KEY_FILE','~/.elevenlabs_key'))).read().strip(); SR=44100
FA=[w for w in json.load(open('narr/fa.json'))['words'] if w['text'].strip()]
L=json.load(open('narr/lines.json')); B=json.load(open('narr/best.json'))
REAL=json.load(open("narr/real.json")); elon_n=sum(len(x["text"].split()) for x in REAL)
# 手本の語を行ごとに分ける（ナレ3行→イーロン→残り）
idx=0; refw=[]
for i,(a,b,t) in enumerate(L):
    for x in REAL:
        if i==x['before_line']: idx+=len(x['text'].split())
    n=len(t.split()); refw.append(FA[idx:idx+n]); idx+=n
dur=librosa.get_duration(path='ref.wav'); track=np.zeros(int(dur*SR)+SR); info=[]
os.makedirs('narr/fa_takes',exist_ok=True)
for i,(a,b,t) in enumerate(L):
    take=B[str(i)]['take']; text=B[str(i)].get('text',t)
    fj=f"narr/fa_takes/{os.path.basename(take)}.json"
    if not os.path.exists(fj):
        r=subprocess.run(['curl','-s','-X','POST','https://api.elevenlabs.io/v1/forced-alignment','-H',f'xi-api-key: {K}','-F',f'file=@{take}','-F',f'text={text}'],capture_output=True,text=True)
        open(fj,'w').write(r.stdout)
    ow=[w for w in json.load(open(fj))['words'] if w['text'].strip()]
    y,_=librosa.load(take,sr=SR); rw=refw[i]
    if len(ow)!=len(rw): print('語の数が違う',i,len(ow),len(rw)); continue
    # 目印：各語の始まりと終わり（うちの秒→手本の秒）。行の頭の少し前から
    pad=0.04; x=[max(0,ow[0]['start']-pad)]; z=[rw[0]['start']-pad]
    for o,r in zip(ow,rw):
        for ko in ('start','end'):
            if o[ko]>x[-1]+0.01 and r[ko]>z[-1]+0.01: x.append(o[ko]); z.append(r[ko])
    x.append(min(len(y)/SR,ow[-1]['end']+0.12)); z.append(rw[-1]['end']+0.12)
    x=np.array(x); z=np.array(z)
    seg=y[int(x[0]*SR):int(x[-1]*SR)]; xs=((x-x[0])*SR).astype(int); zs=((z-z[0])*SR).astype(int)
    xs[-1]=len(seg); keep=np.concatenate([[True],np.diff(xs)>0]); xs,zs=xs[keep],zs[keep]; xs[-1]=len(seg)
    # 1区間の伸び縮みは 0.5〜2.0 倍まで
    for k in range(1,len(zs)):
        s=xs[k]-xs[k-1]; zs[k]=zs[k-1]+int(np.clip(zs[k]-zs[k-1],s*0.5,s*2.0))
    out=rb.timemap_stretch(seg,SR,list(zip(xs,zs)))
    f=int(0.008*SR); out=out.copy(); out[:f]*=np.linspace(0,1,f); out[-f:]*=np.linspace(1,0,f)
    st=int(z[0]*SR); n=min(len(out),len(track)-st); track[st:st+n]+=out[:n]
    info.append(dict(i=i,start=round(st/SR,3),len=round(n/SR,3),stretch=round(n/max(1,len(seg)),3)))
sf.write('narr/narr_track.wav',track,SR); json.dump(info,open('narr/placed.json','w'),indent=0)
print('1語ずつ置いた',len(info),'行')
