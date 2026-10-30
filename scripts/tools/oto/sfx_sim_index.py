# 似とる度の目録：棚の音ごとに CLAP の埋め込み（音の意味・音色）と頭1.5秒のメルを作る
# 使い方: python3 sfx_sim_index.py <山のフォルダ,…> <出力.npz>
import sys, os, glob, numpy as np, librosa, torch
from multiprocessing import Pool
from transformers import ClapModel, ClapProcessor
SR=22050; HL=256; NM=48; MF=int(1.5*SR/HL)+1
def load(p):
    try:
        y,_=librosa.load(p,sr=48000,mono=True,duration=5)
        if len(y)<480 or np.abs(y).max()<1e-4: return None
        nz=np.flatnonzero(np.abs(y)>np.abs(y).max()*0.05); y=y[max(nz[0]-480,0):]   # 頭の無音を切る
        y48=y[:3*48000]; y22=librosa.resample(y[:int(1.6*48000)],orig_sr=48000,target_sr=SR)
        m=librosa.power_to_db(librosa.feature.melspectrogram(y=y22,sr=SR,n_fft=1024,hop_length=HL,n_mels=NM,fmin=60,fmax=10000)+1e-10)
        mm=np.full((NM,MF),-100.0,np.float32); mm[:,:min(MF,m.shape[1])]=m[:,:MF]
        return p,y48.astype(np.float32),mm.astype(np.float16),min(len(y)/48000,5.0)
    except Exception: return None
if __name__=='__main__':
    roots=sys.argv[1].split(','); out=sys.argv[2]
    files=sorted(set(p for r in roots for p in glob.glob(r+'/**/*',recursive=True)+glob.glob(r+'/*') if p.lower().endswith(('.wav','.mp3','.ogg','.flac','.aif','.aiff','.m4a'))))
    print('棚', len(files), flush=True)
    dev='mps' if torch.backends.mps.is_available() else 'cpu'
    M=ClapModel.from_pretrained("laion/clap-htsat-unfused").to(dev).eval(); P=ClapProcessor.from_pretrained("laion/clap-htsat-unfused")
    paths=[]; embs=[]; mels=[]; durs=[]; buf=[]
    def flush():
        if not buf: return
        x=P(audios=[b[1] for b in buf],sampling_rate=48000,return_tensors='pt')
        with torch.no_grad(): e=M.get_audio_features(**{k:v.to(dev) for k,v in x.items()})
        e=torch.nn.functional.normalize(e,dim=-1).cpu().numpy().astype(np.float16)
        for b,ee in zip(buf,e): paths.append(b[0]); embs.append(ee); mels.append(b[2]); durs.append(b[3])
        buf.clear()
    with Pool(6) as pool:
        for i,r in enumerate(pool.imap(load,files,chunksize=16)):
            if r: buf.append(r)
            if len(buf)>=32: flush()
            if i%2000==0: print(i,'/',len(files),flush=True)
    flush()
    np.savez(out,paths=np.array(paths),emb=np.array(embs),mel=np.array(mels),dur=np.array(durs,np.float32))
    print('目録', len(paths), flush=True)
