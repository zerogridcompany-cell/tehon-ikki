# 仕上げ：ナレ・イーロン＝真ん中／BGM・効果音＝元のステレオ。2チャンネルで書き出し
import json, numpy as np, librosa, soundfile as sf
SR=44100
ref,_=librosa.load('ref.wav',sr=SR,mono=False); N=ref.shape[1]
def st(f):
    y,_=librosa.load(f,sr=SR,mono=False); y=np.atleast_2d(y)
    if y.shape[0]==1: y=np.vstack([y,y])
    return np.pad(y,((0,0),(0,max(0,N-y.shape[1]))))[:,:N]
mix=st('narr/narr_track_g.wav')+st('narr/real_track.wav')+st('bgm/bgm_track.wav')
sfx=np.zeros((2,N))
for k in json.load(open('sfx/kept.json')):
    y=st.__wrapped__(k['sfx']) if hasattr(st,'__wrapped__') else None
    y,_=librosa.load(k['sfx'],sr=SR,mono=False); y=np.atleast_2d(y)
    if y.shape[0]==1: y=np.vstack([y,y])
    y=y[:2]; yt,(i0,i1)=librosa.effects.trim(y.mean(0),top_db=40); y=y[:,i0:i1]
    t=int(k['t']*SR); n=min(y.shape[1],N-t); sfx[:,t:t+n]+=y[:,:n]*k['gain']
sf.write('sfx/sfx_track_st.wav',sfx.T,SR)
mix=mix+sfx; pk=np.abs(mix).max()
if pk>0.98: mix*=0.98/pk
sf.write('mix_final.wav',mix.T,SR); print('最大', round(float(pk),3))
