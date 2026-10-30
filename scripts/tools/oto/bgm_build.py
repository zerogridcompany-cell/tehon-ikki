# segs.json どおりに曲を切って速さを変え、手本の音楽（分けた物）に音量と音色（帯ごとの倍率）を合わせて1本に
import json, sys, numpy as np, librosa, soundfile as sf, scipy.signal as ss
SR=44100
ref,_=librosa.load('narr/music.wav',sr=SR,mono=True); N=len(ref)
segs=json.load(open(sys.argv[1] if len(sys.argv)>1 else 'bgm/segs.json')); out=np.zeros((2,N)); X=int(0.04*SR)
cache={}
bands=[(20,120),(120,400),(400,1500),(1500,5000),(5000,16000)]
def bp(y,lo,hi): sos=ss.butter(4,[lo,min(hi,SR/2-100)],btype='band',fs=SR,output='sos'); return ss.sosfiltfilt(sos,y)
for g in segs:
    if g['f'] not in cache: cache[g['f']]=librosa.load(g['f'],sr=SR,mono=False)[0]
    songS=cache[g['f']]; r=g['rate']
    s_start=g['at']+(g['t0']-g['t_at'])*r; s_len=(g['t1']-g['t0'])*r
    a=int(max(0,s_start-0.05)*SR); yS=songS[:,a:a+int((s_len+0.1+0.05)*SR)]
    if abs(r-1)>1e-4: yS=librosa.resample(yS,orig_sr=SR,target_sr=int(round(SR/r)))   # 再生速度を変える＝高さも変わる
    pre=int(round((s_start-max(0,s_start-0.05))/r*SR)); yS=yS[:,pre:]; y=yS.mean(0)
    i0=int(g['t0']*SR); n=min(int((g['t1']-g['t0'])*SR)+X, N-i0, len(y)); y=y[:n].copy(); yS=yS[:,:n]
    # 帯ごとに手本の音楽の強さへ合わせる（中央値の比・声や効果音に引っぱられんように）
    rr=ref[i0:i0+n]; yy=np.zeros((2,n))
    for lo,hi in bands:
        yb=bp(y,lo,hi); rb=bp(rr,lo,hi)
        e1=np.sqrt(np.convolve(yb**2,np.ones(4410)/4410,'same'))+1e-9; e2=np.sqrt(np.convolve(rb**2,np.ones(4410)/4410,'same'))+1e-9
        gain=float(np.median(e2/e1)); g.setdefault('gains',[]).append(round(gain,3)); yy+=np.stack([bp(yS[c],lo,hi) for c in range(2)])*gain
    f=np.ones(n); f[:X]=np.linspace(0,1,X); f[-X:]=np.linspace(1,0,X)
    out[:,i0:i0+n]+=yy*f
sf.write('bgm/bgm_track.wav',out.T,SR)
for g in segs: print(g['t0'],g['t1'],g['f'].split('/')[-1][:4],g['rate'],g['gains'])
