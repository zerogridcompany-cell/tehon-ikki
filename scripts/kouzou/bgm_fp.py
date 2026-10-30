# 自前の Shazam：音の山の組み合わせ（指紋）で、手本の音楽が「どの曲の・何秒目を・何倍の速さで」使っとるかを当てる
# sped up / slowed（速さと高さが一緒に動く＝resample）を、手本を逆に戻しながら 0.25% 刻みで探す
# 使い方: python3 tools/bgm_fp.py <手本の音楽の層.wav> <曲のフォルダ or ファイル,…> <出す.json> [速さの下,上,刻み]
import sys, os, glob, json, numpy as np, librosa
from scipy.ndimage import maximum_filter
from collections import defaultdict, Counter
SR = 11025; NF = 2048; HOP = 256; FAN = 12; DT = 64

def peaks(y):
    S = np.abs(librosa.stft(y, n_fft=NF, hop_length=HOP))[:600]; L = np.log(S + 1e-6)
    m = (L == maximum_filter(L, size=(15, 9))) & (L > np.percentile(L, 90))
    f, t = np.nonzero(m); o = np.argsort(t); return f[o], t[o]

def hashes(y):
    f, t = peaks(y); out = []
    for i in range(len(t)):
        n = 0
        for j in range(i + 1, len(t)):
            dt = t[j] - t[i]
            if dt < 1: continue
            if dt > DT: break
            out.append(((int(f[i]) << 16) | (int(f[j]) << 7) | int(dt), int(t[i]))); n += 1
            if n >= FAN: break
    return out

def build_db(files):
    db = defaultdict(list)
    for k, fp in enumerate(files):
        y, _ = librosa.load(fp, sr=SR)
        for h, t in hashes(y): db[h].append((k, t))
    return db

if __name__ == '__main__':
    ref = sys.argv[1]; src = sys.argv[2].split(','); out = sys.argv[3]
    lo, hi, st = (float(x) for x in (sys.argv[4].split(',') if len(sys.argv) > 4 else '0.85,1.18,0.0025'.split(',')))
    files = []
    for s in src: files += sorted(glob.glob(os.path.join(s, '*.webm')) + glob.glob(os.path.join(s, '*.m4a')) + glob.glob(os.path.join(s, '*.mp3')) + glob.glob(os.path.join(s, '*.wav'))) if os.path.isdir(s) else [s]
    files = sorted(set(files)); print(len(files), '曲を指紋に', flush=True)
    db = build_db(files); y, _ = librosa.load(ref, sr=SR); dur = len(y) / SR
    W, H = 6.0, 2.0; res = []
    for r in np.arange(lo, hi + 1e-9, st):
        # 手本＝元を r 倍速に resample した物 → 手本を r 倍ゆっくりに戻すと元と同じ高さ・速さになる
        yr = librosa.resample(y, orig_sr=SR, target_sr=int(round(SR * r)))
        hs = hashes(yr); fr = SR / HOP
        for w0 in np.arange(0, dur - W / 2, H):
            a, b = w0 * r * fr, (w0 + W) * r * fr; cnt = Counter()
            for h, t in hs:
                if a <= t < b:
                    for k, tt in db.get(h, ()): cnt[(k, tt - t)] += 1
            if cnt:
                (k, off), n = cnt.most_common(1)[0]
                res.append(dict(w0=round(float(w0), 2), r=round(float(r), 4), song=os.path.basename(files[k]), hits=n, at=round(float(off / fr + w0 * r), 3)))
        print('速さ', round(float(r), 4), flush=True) if abs((r - lo) / st % 20) < 1e-6 else None
    # 窓ごとに一番当たった（曲・速さ・位置）
    best = {}
    for x in res:
        if x['w0'] not in best or x['hits'] > best[x['w0']]['hits']: best[x['w0']] = x
    json.dump(dict(all=res, best=[best[k] for k in sorted(best)], files=files), open(out, 'w'), ensure_ascii=False)
    for k in sorted(best): b = best[k]; print(f"{b['w0']:5.1f}s  {b['song']:20s} 速さ {b['r']:.4f}  曲の {b['at']:7.2f}s  当たり {b['hits']}")
