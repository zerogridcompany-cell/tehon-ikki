# 低い所を「声」と「音楽＋効果音」に分けて、どっちが悪いか
import sys, numpy as np, librosa
sr=22050
def L(f): return librosa.load(f,sr=sr,mono=True)[0]
V=L('sep/htdemucs/ref/vocals.wav'); M=L('narr/music.wav'); n=len(V)
pad=lambda y: np.pad(y,(0,n))[:n]
v=pad(L('narr/narr_track_g.wav'))+pad(L('narr/real_track.wav')); m=pad(L('bgm/bgm_track.wav'))+pad(L('sfx/sfx_track_st.wav'))
def melf(y): return librosa.power_to_db(librosa.feature.melspectrogram(y=y,sr=sr,n_mels=48,hop_length=256,fmin=40,fmax=10000)+1e-10)
def c(A,B): return np.corrcoef(melf(A).ravel(),melf(B).ravel())[0,1]
def lv(y): return 20*np.log10(np.sqrt((y**2).mean())+1e-9)
for t in [float(x) for x in sys.argv[1:]]:
    a,b=int(t*sr),int((t+0.5)*sr)
    print(f"{t:5.1f} 声 形{c(V[a:b],v[a:b]):.2f} 大きさ 手本{lv(V[a:b]):6.1f} うち{lv(v[a:b]):6.1f} ｜ 音楽 形{c(M[a:b],m[a:b]):.2f} 手本{lv(M[a:b]):6.1f} うち{lv(m[a:b]):6.1f}")
