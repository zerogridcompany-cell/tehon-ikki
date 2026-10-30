# 弱い行だけ、速さ×安定度を振って録り足し、手本の行（正確な時刻）に一番近い1本へ入れ替える
import json, os, sys, math, urllib.request
sys.path.insert(0,'tools'); from line_cmp import cmp
K=open(os.path.expanduser('~/.elevenlabs_key')).read().strip(); V=open('narr/voice.txt').read().strip()
L=json.load(open('narr/lines.json')); B=json.load(open('narr/best.json'))
def sc(c): pc=c['pitch_corr'] if c['pitch_corr']==c['pitch_corr'] else 0; return c['sim']+0.5*pc-2*abs(math.log(c['ratio']))
for i in [int(x) for x in sys.argv[1].split(',')]:
    a,b,t=L[i]; cur=B[str(i)]; base_sp=min(1.2,max(0.7,cur['speed'] if 'speed' in cur else 1.0)); r0=cur['ratio']
    for k,(stab,spm) in enumerate([(0.3,1.0),(0.5,1.0),(0.7,1.0),(0.3,1.1),(0.5,1.1),(0.3,1.18),(0.5,1.18),(0.2,1.12)]):
        out=f'narr/takes/{i:02d}_m{k}.mp3'; sp=round(min(1.2,max(0.7,spm)),2)
        if not os.path.exists(out):
            body={'text':t,'model_id':'eleven_v4','seed':2000+k,'voice_settings':{'stability':stab,'similarity_boost':0.8,'speed':sp}}
            r=urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{V}?output_format=mp3_44100_192',data=json.dumps(body).encode(),headers={'xi-api-key':K,'Content-Type':'application/json'})
            open(out,'wb').write(urllib.request.urlopen(r,timeout=120).read())
        c=cmp(out,a+0.12,b-0.12); c.update(take=out,speed=sp,stab=stab,score=round(sc(c),3))
        if c['score']>B[str(i)]['score']: B[str(i)]=c
    print(i, B[str(i)]['take'][-9:], {k:B[str(i)].get(k) for k in ['sim','ratio','pitch_corr','score']}, flush=True)
    json.dump(B,open('narr/best.json','w'),indent=0)
