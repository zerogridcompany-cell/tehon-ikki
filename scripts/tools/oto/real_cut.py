# 本人の声（手本に入っとる実在の人の声）を、元の動画の音から切って手本と同じ所に置く
# narr/real.json＝[{"before_line":3,"text":"…","ref_a":9.85,"ref_b":17.25,"src":"hunt/xxx.webm","offset":2981.46}]
#   offset＝元の秒−手本の秒（align_src.py で測る）。ここで波形の相関で ms まで詰め、音量の倍も測る
import json, numpy as np, librosa, soundfile as sf
from scipy.signal import correlate
SR=44100; dur=librosa.get_duration(path='ref.wav'); tr=np.zeros(int(dur*SR)+SR); R=json.load(open('narr/real.json'))
for x in R:
    a,b,off=x['ref_a'],x['ref_b'],x['offset']; m=min(1.0,(b-a)/4)
    r,_=librosa.load('sep/htdemucs/ref/vocals.wav',sr=SR,offset=a+m,duration=b-a-2*m)
    s,_=librosa.load(x['src'],sr=SR,offset=a+m+off-0.1,duration=b-a-2*m+0.2)
    c=correlate(s,r,mode='valid'); k=int(np.argmax(np.abs(c))); lag=k/SR-0.1; off2=off+lag
    g=float(np.sqrt((r**2).mean()/((s[k:k+len(r)]**2).mean()+1e-12)))
    seg,_=librosa.load(x['src'],sr=SR,offset=a+off2,duration=b-a); f=int(0.015*SR); seg[:f]*=np.linspace(0,1,f); seg[-f:]*=np.linspace(1,0,f)
    st=int(a*SR); tr[st:st+len(seg)]+=seg*g; x.update(offset_fine=round(off2,4),gain=round(g,3),wave_corr=round(float(c[k]/np.sqrt((r**2).sum()*(s[k:k+len(r)]**2).sum())),3))
    print(x['text'][:30], 'ずれ', round(lag*1000,1),'ms 波形相関', x['wave_corr'], '音量の倍', x['gain'])
sf.write('narr/real_track.wav',tr,SR); json.dump(R,open('narr/real.json','w'),indent=0)
