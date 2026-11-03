# 行ごとに何本か録って、手本に一番近い1本を選ぶ（声・長さ・抑揚）
import json, os, sys, math, urllib.request, numpy as np
sys.path.insert(0,'tools'); from line_cmp import cmp
K=open(os.path.expanduser('~/.elevenlabs_key')).read().strip()
V=open('narr/voice.txt').read().strip(); M='eleven_v4'
def tts(text,out,seed,speed):
    if os.path.exists(out) and os.path.getsize(out)>1000: return
    body={'text':text,'model_id':M,'seed':seed,'voice_settings':{'speed':speed}}
    r=urllib.request.Request(f'https://api.elevenlabs.io/v1/text-to-speech/{V}?output_format=mp3_44100_192',data=json.dumps(body).encode(),headers={'xi-api-key':K,'Content-Type':'application/json'})
    open(out,'wb').write(urllib.request.urlopen(r,timeout=120).read())
def score(c): return c['sim'] + 0.5*(c['pitch_corr'] if c['pitch_corr']==c['pitch_corr'] else 0) - 2*abs(math.log(c['ratio']))
L=json.load(open('narr/lines.json')); os.makedirs('narr/takes',exist_ok=True)
best=json.load(open('narr/best.json')) if os.path.exists('narr/best.json') else {}
idx=[int(x) for x in sys.argv[1].split(',')] if len(sys.argv)>1 else range(len(L))
for i in idx:
    a,b,t=L[i]; res=[]; speed=1.0
    for k in range(6):
        out=f'narr/takes/{i:02d}_{k}.mp3'
        tts(t,out,1000+k,round(speed,2)); c=cmp(out,a,b); c.update(take=out,speed=round(speed,2),score=round(score(c),3)); res.append(c)
        # 次の1本は今の長さから速さを直す（v4 の速さは 0.7〜1.2）
        speed=min(1.2,max(0.7,speed*c['ratio']))
        if k>=3 and max(r['score'] for r in res)>0.95+0.4: break
    res.sort(key=lambda r:-r['score']); best[str(i)]=res[0]
    print(i, {k:res[0][k] for k in ['sim','ratio','pitch_corr','speed','score']}, f"({len(res)}本)", flush=True)
    json.dump(best,open('narr/best.json','w'),indent=0)
