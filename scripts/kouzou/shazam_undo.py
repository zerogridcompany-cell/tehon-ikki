# Shazam を「速さを戻した」手本の窓にかける：sped up / slowed の版は、そのままでは Shazam が外す→戻すと元の曲で当たる
import sys, json, asyncio, numpy as np, librosa, soundfile as sf, os
from shazamio import Shazam
ref = sys.argv[1]; out = sys.argv[2]; rates = [float(x) for x in sys.argv[3].split(',')]
y, sr = librosa.load(ref, sr=44100); dur = len(y) / sr; W, H = 8.0, 4.0
async def main():
    sh = Shazam(); res = []
    for w0 in np.arange(0, dur - 4, H):
        seg = y[int(w0 * sr):int((w0 + W) * sr)]
        for r in rates:
            yr = librosa.resample(seg, orig_sr=sr, target_sr=int(sr * r))   # r 倍にゆっくり＝r 倍速の版を元に戻す
            p = f'/tmp/_sz_{os.getpid()}.wav'; sf.write(p, yr, sr)
            try: d = await sh.recognize(p)
            except Exception as e: d = {}; print('err', e)
            t = d.get('track') or {}
            if t: res.append(dict(w0=float(w0), r=r, title=t.get('title'), artist=t.get('subtitle'), key=t.get('key'), offset=(d.get('matches') or [{}])[0].get('offset'), skew=(d.get('matches') or [{}])[0].get('frequencyskew')))
            print(round(float(w0), 1), r, t.get('subtitle'), '-', t.get('title'), flush=True)
            await asyncio.sleep(1.2)
    json.dump(res, open(out, 'w'), ensure_ascii=False, indent=0)
asyncio.run(main())
