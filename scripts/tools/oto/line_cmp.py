# 録った1行と手本の同じ行を比べる：声の指紋・喋りの長さ・高さ・抑揚（DTW 後の相関）
import sys, json, numpy as np, librosa
from resemblyzer import VoiceEncoder, preprocess_wav
enc=VoiceEncoder(verbose=False); sr=16000
REF,_=librosa.load('sep/htdemucs/ref/vocals.wav',sr=sr)
def trim(y): yt,_=librosa.effects.trim(y,top_db=30); return yt
def stats(y):
    f=librosa.pyin(y,fmin=60,fmax=400,sr=sr,hop_length=160)[0]
    return f
def cmp(path, a, b):
    y,_=librosa.load(path,sr=sr); y=trim(y); r=trim(REF[max(0,int((a-0.15)*sr)):int((b+0.15)*sr)])
    e1=enc.embed_utterance(preprocess_wav(y,source_sr=sr)); e2=enc.embed_utterance(preprocess_wav(r,source_sr=sr))
    f1,f2=stats(y),stats(r)
    m1=librosa.feature.mfcc(y=y,sr=sr,hop_length=160); m2=librosa.feature.mfcc(y=r,sr=sr,hop_length=160)
    D,wp=librosa.sequence.dtw(m1,m2); wp=wp[::-1]
    a1=np.array([f1[min(i,len(f1)-1)] for i,_ in wp]); a2=np.array([f2[min(j,len(f2)-1)] for _,j in wp])
    ok=~np.isnan(a1)&~np.isnan(a2)
    pc=np.corrcoef(np.log(a1[ok]),np.log(a2[ok]))[0,1] if ok.sum()>10 else float('nan')
    return dict(sim=round(float(e1@e2),3), dur=round(len(y)/sr,2), ref_dur=round(len(r)/sr,2), ratio=round(len(y)/len(r),3),
                f0=round(float(np.nanmedian(f1)),1), ref_f0=round(float(np.nanmedian(f2)),1), pitch_corr=round(float(pc),3))
if __name__=='__main__':
    L=json.load(open('narr/lines.json')); d=sys.argv[1]
    for i in [int(x) for x in sys.argv[2].split(',')]:
        print(i, cmp(f'{d}/{i:02d}.mp3', L[i][0], L[i][1]))
