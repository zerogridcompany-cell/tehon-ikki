# 決め打ちの (曲, ずれ) を、鋭い当て方で1秒ごとに採点
import sys, json, numpy as np, librosa
sr=22050; H=256; fps=sr/H; W=int(2*fps)
def mel(y): return np.log(librosa.feature.melspectrogram(y=y,sr=sr,n_mels=64,hop_length=H,fmin=60,fmax=8000)+1e-5)
def z(x): x=x-x.mean(1,keepdims=True); return x/(x.std(1,keepdims=True)+1e-6)
MR=mel(librosa.load('narr/music.wav',sr=sr)[0]); C=json.loads(sys.argv[1]); S={}
for n,f,d in C: S.setdefault(f,mel(librosa.load(f,sr=sr)[0]))
print('t   '+' '.join(f'{n:>7}' for n,_,_ in C))
for k in range(0,MR.shape[1]-W,int(fps)):
    row=[]
    for n,f,d in C:
        j=k+int(round(d*fps)); MS=S[f]
        if j<0 or j+W>MS.shape[1]: row.append('      -'); continue
        a=z(MR[:,k:k+W]); b=z(MS[:,j:j+W]); v=(a*b).sum()/np.linalg.norm(a)/np.linalg.norm(b); row.append(f'{v:7.2f}')
    print(f'{k/fps:3.0f} '+' '.join(row))
