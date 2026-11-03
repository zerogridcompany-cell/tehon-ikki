"""音の鳴り始めを 1ms より細かく出す（10/31 依頼者「基本コンマ単位で見て。人が見るより繊細に」）。拍の網（beat_track）は使わん＝実際の音より約45ms 遅れて出る（tehonR で実測）。

python3 oto_ms.py <音.wav> <出す.json> [--band 30,150] [--delta 0.2]
from oto_ms import tachiagari;  T = tachiagari(y, sr, band=None)  → [{t, peak_t, rise_ms, strength}]
- 見つけ方：onset の強さ（hop 32＝0.7ms）の山 → 山の手前の谷まで戻る（backtrack）→ 振幅の包絡が「その打ちの山の 30%」を初めて超えた1サンプルを鳴り始め t にする（44.1kHz＝0.023ms 刻み）
- peak_t＝その打ちの一番大きい所・rise_ms＝鳴り始め→山の時間（アタックの鋭さ）
"""
import json, sys
import numpy as np, librosa, scipy.signal as ss

SR = 44100


def tachiagari(y, sr=SR, band=None, delta=0.05, wait_ms=40, tail_ms=70, min_rel=0.10, min_rise_db=2.0):   # delta 0.2→0.05（10/31 物差し：スネアの音が重なると4回に1回聞き逃した→0）
    if band:
        y = ss.sosfiltfilt(ss.butter(4, band, "band", fs=sr, output="sos"), y)
    H = 32
    oe = librosa.onset.onset_strength(y=y, sr=sr, hop_length=H, lag=1, max_size=1)
    if oe.max() <= 0: return []
    oe = oe / oe.max()
    pk = librosa.onset.onset_detect(onset_envelope=oe, sr=sr, hop_length=H, delta=delta, wait=int(wait_ms / 1000 * sr / H), backtrack=False)
    bt = librosa.onset.onset_backtrack(pk, oe)
    env = np.abs(ss.hilbert(y)) if len(y) < sr * 120 else np.abs(y)
    env = ss.sosfiltfilt(ss.butter(2, 400, "low", fs=sr, output="sos"), env)
    out = []
    for p, b in zip(pk, bt):
        a0 = max(0, b * H - int(0.010 * sr)); a1 = min(len(env), p * H + int(0.040 * sr))
        if a1 - a0 < 8: continue
        seg = env[a0:a1]; j = int(np.argmax(seg)); top = seg[j]; base = float(np.min(seg[:max(1, j)]))
        th = base + 0.3 * (top - base); k = int(np.argmax(seg[:j + 1] >= th))
        t = (a0 + k) / sr; tp = (a0 + j) / sr
        # 本当に音が大きくなった打ちだけ＝鳴り始めの前 20ms の一番小さい所から、後ろ 30ms の一番大きい所まで min_rise_db 以上（10/31 物差し：長い 808 は音が下がり続けるだけやのに 207・351・507ms に「打ち」を見とった＝音と絵の組を 13/46 間違えた）
        i0 = a0 + k; pre = env[max(0, i0 - int(0.020 * sr)):i0 + 1].min(); post = env[i0:min(len(env), i0 + int(0.030 * sr))].max()
        rise = 20 * np.log10((post + 1e-9) / (pre + 1e-9))
        if rise < min_rise_db: continue
        out.append(dict(rise_db=round(float(rise), 1), t=round(t, 5), peak_t=round(tp, 5), rise_ms=round((tp - t) * 1000, 2), strength=round(float(oe[p]), 3)))
    # 70ms 以内に続く音は1つの打ち＝一番最初の鳴り始めだけ残し、強さは塊の中の一番強い値（10/31 物差し：キックは「カチッ」と「ドン」が約34ms 離れて2つに数えとった＝余計 24・音と絵が +34ms ずれた。人が聞くのは頭）
    keep = []
    for o in out:
        if keep and o["t"] - keep[-1]["t"] < tail_ms / 1000:
            keep[-1]["strength"] = max(keep[-1]["strength"], o["strength"]); keep[-1]["n_merged"] = keep[-1].get("n_merged", 1) + 1; continue
        keep.append(o)
    # まわり ±1秒で一番強い打ちの 10% 未満は、長い余韻の揺れ＝捨てる（10/31 物差し：1.6秒のキックの尾で 0.06〜0.10 の余計が 24）
    ts = np.array([o["t"] for o in keep]); st = np.array([o["strength"] for o in keep])
    return [o for o, t, v in zip(keep, ts, st) if v >= min_rel * st[np.abs(ts - t) <= 1.0].max()]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument("wav"); ap.add_argument("out"); ap.add_argument("--band"); ap.add_argument("--delta", type=float, default=0.05)
    a = ap.parse_args()
    y, sr = librosa.load(a.wav, sr=SR)
    r = tachiagari(y, sr, band=[float(x) for x in a.band.split(",")] if a.band else None, delta=a.delta)
    json.dump(dict(src=a.wav, unit="秒（5桁＝0.01ms）", note="鳴り始め＝包絡が山の30%を超えた1サンプル", onsets=r), open(a.out, "w"), ensure_ascii=False)
    print("鳴り始め", len(r), "個")
