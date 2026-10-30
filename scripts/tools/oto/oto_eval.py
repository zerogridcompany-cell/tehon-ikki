# 音の近さの物差し：0.5秒ごとのメルの相関（形）と、帯ごとの大きさの差（dB）
import sys, numpy as np, librosa
sr=22050; H=256
def mel(f): return librosa.power_to_db(librosa.feature.melspectrogram(y=librosa.load(f,sr=sr,mono=True)[0],sr=sr,n_mels=64,hop_length=H,fmin=40,fmax=10000)+1e-10)
A=mel(sys.argv[1]); B=mel(sys.argv[2]); n=min(A.shape[1],B.shape[1]); A,B=A[:,:n],B[:,:n]
w=int(0.5*sr/H); cs=[]; dd=[]
for k in range(0,n-w,w):
    a=A[:,k:k+w].ravel(); b=B[:,k:k+w].ravel()
    if a.max()<-60: continue
    cs.append(np.corrcoef(a,b)[0,1]); dd.append(np.abs(A[:,k:k+w].mean(1)-B[:,k:k+w].mean(1)).mean())
cs=np.array(cs); print(f"形の相関 平均 {cs.mean():.3f}（低い10% {np.percentile(cs,10):.3f}）・帯の大きさの差 平均 {np.mean(dd):.1f}dB")
if len(sys.argv)>3:
    worst=np.argsort(cs)[:8]; print('低い所（秒）', sorted(round(i*0.5,1) for i in worst))
