# 手本のナレと、声の見本の「声の指紋」の近さで順位
import json, sys, numpy as np, librosa
from resemblyzer import VoiceEncoder, preprocess_wav
enc=VoiceEncoder()
def emb(path):
    y,_=librosa.load(path,sr=16000); y=preprocess_wav(y,source_sr=16000)
    return enc.embed_utterance(y), y
R,_=emb('narr/ref_narr.wav')
# 区間ごとの指紋も（ぶれの幅を見る）
V=json.load(open('narr/voices.json')); res=[]
for v in V:
    try: e,y=emb(f"narr/prev/{v['id']}.mp3")
    except Exception: continue
    f=librosa.pyin(y[:16000*6],fmin=60,fmax=400,sr=16000)[0]
    res.append((float(e@R), v['id'], v['name'], v['src'], round(float(np.nanmedian(f)),1)))
res.sort(reverse=True)
json.dump(res,open('narr/rank.json','w'),ensure_ascii=False)
for r in res[:25]: print(f"{r[0]:.3f} {r[1]} {r[3]} F0={r[4]} {r[2][:60]}")
