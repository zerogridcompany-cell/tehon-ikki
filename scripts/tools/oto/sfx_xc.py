# 効果音の「頭」を手本の立ち上がりに当てる：棚の音の頭0.5秒と、手本の残りの立ち上がりの所を波形の相関で比べる（指紋が弱い小さい音も拾う）
# 使い方: python3 sfx_xc.py <残り.wav> <山のフォルダ,…> <出力.json> [件数]
import sys, os, glob, json, numpy as np, soundfile as sf, librosa
SR=22050; W=int(0.5*SR); L=int(0.06*SR); NFFT=32768
from scipy.ndimage import uniform_filter1d
FR=np.fft.rfftfreq(NFFT,1/SR); BAND=((FR>150)&(FR<9000)).astype(np.float32)
def white(x):
    # 低い音のうなりで相関が上がるのを防ぐ＝周波数ごとの大きさをならす
    X=np.fft.rfft(x,NFFT); m=uniform_filter1d(np.abs(X),64)+1e-6
    return np.fft.irfft(X/m*BAND,NFFT)[:len(x)].astype(np.float32)
res,_=librosa.load(sys.argv[1],sr=SR,mono=True); roots=sys.argv[2].split(','); outp=sys.argv[3]; TOP=int(sys.argv[4]) if len(sys.argv)>4 else 400
# 立ち上がり＝細かめに拾う（小さい音も）＋分類済みの時刻
on=librosa.onset.onset_detect(y=res,sr=SR,hop_length=256,backtrack=True,units='time',delta=0.03,wait=2)
ev=sorted(set([round(float(t),3) for t in on]+[e['t'] for e in json.load(open('sfx/bunrui.json'))]))
ev=[t for i,t in enumerate(ev) if i==0 or t-ev[i-1]>0.03]
print('立ち上がり', len(ev), flush=True)
# 手本の窓：t-L-0.03 から W+2L
R=[]; RS=[]; starts=[]
for t in ev:
    a=int((t-0.03)*SR)-L; seg=np.zeros(W+2*L,np.float32)
    lo=max(a,0); hi=min(a+W+2*L,len(res)); seg[lo-a:hi-a]=res[lo:hi]; seg=white(seg)
    R.append(np.fft.rfft(seg,NFFT)); cs=np.concatenate([[0],np.cumsum(seg.astype(np.float64)**2)])
    RS.append(np.sqrt(np.maximum(cs[W:W+2*L+1]-cs[:2*L+1],1e-12))); starts.append(a)
R=np.array(R); RS=np.array(RS)
files=[p for r in roots for p in glob.glob(r+'/**/*',recursive=True) if p.lower().endswith(('.wav','.mp3','.ogg','.flac','.aif','.aiff','.m4a'))]
best=[]
for k,p in enumerate(files):
    try:
        z,sr=sf.read(p,frames=int(48000*3),dtype='float32',always_2d=True); z=z.mean(1)
        if sr!=SR: z=librosa.resample(z,orig_sr=sr,target_sr=SR)
    except Exception:
        try: z,_=librosa.load(p,sr=SR,mono=True,duration=3)
        except Exception: continue
    if len(z)<SR*0.05 or np.abs(z).max()<1e-4: continue
    env=np.abs(z); o=int(np.argmax(env>env.max()*0.05)); o=max(o-int(0.01*SR),0)
    s=z[o:o+W]
    if len(s)<W: s=np.pad(s,(0,W-len(s)))
    s=white(s); ns=np.linalg.norm(s)
    if ns<1e-6: continue
    S=np.conj(np.fft.rfft(s,NFFT))
    C=np.fft.irfft(R*S,NFFT)[:, :2*L+1]/(RS*ns)
    i=np.unravel_index(np.argmax(C),C.shape); c=float(C[i])
    # この棚の音の 0 秒が手本の何秒に来るか
    best.append(dict(file=p,ev=ev[i[0]],corr=round(c,3),ref_t=round((starts[i[0]]+i[1]-o)/SR,4)))
    if k%1000==0: print(k,'/',len(files),flush=True)
best.sort(key=lambda h:-h['corr']); json.dump(best[:TOP],open(outp,'w'),ensure_ascii=False,indent=0)
print('調べた', len(best))
for h in best[:30]: print(h['corr'], h['ev'], h['ref_t'], os.path.basename(h['file']))
