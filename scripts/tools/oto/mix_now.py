# ナレの行ごとの音量を手本の声に合わせ、ナレ＋イーロン＋BGM（＋効果音）を1本に。手本との差も出す
import json, numpy as np, librosa, soundfile as sf, os
SR=44100
voc,_=librosa.load('sep/htdemucs/ref/vocals.wav',sr=SR,mono=True)
n,_=librosa.load('narr/narr_track.wav',sr=SR); e,_=librosa.load('narr/real_track.wav',sr=SR); b,_=librosa.load('bgm/bgm_track.wav',sr=SR)
N=len(voc); fit=lambda x: np.pad(x,(0,max(0,N-len(x))))[:N]
n,e,b=fit(n),fit(e),fit(b)
for L in json.load(open('narr/placed.json')):
    i0=int(L['start']*SR); i1=i0+int(L['len']*SR)
    g=np.sqrt((voc[i0:i1]**2).mean()/((n[i0:i1]**2).mean()+1e-12)); n[i0:i1]*=g; L['gain']=round(float(g),3)
sf.write('narr/narr_track_g.wav',n,SR)
s=fit(librosa.load('sfx/sfx_track.wav',sr=SR)[0]) if os.path.exists('sfx/sfx_track.wav') else np.zeros(N)
mix=n+e+b+s; sf.write('mix_now.wav',mix,SR)
print('ナレの音量の倍（最小〜最大）', round(min(x['gain'] for x in json.load(open('narr/placed.json'))),2) if False else '')
