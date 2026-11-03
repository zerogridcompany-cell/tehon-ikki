#!/usr/bin/env python3
"""動きの量の照合（mg-mane assets/waza20）：手本の札（clip）とうちの All20 の各技で、隣のコマとの差（グレー 0〜255 の平均）を並べる。
python3 ugoki.py <All20.mp4> [--sec 75] [--json 出す所.json]
- 手本は 410x480 の札（右上の番号の丸と端 10px を伏せる）・うちは上の帯 150px を除いた 1080x1770 を 410 幅に縮めて測る
- 比＝うちの中央値 ÷ 手本の中央値（手本の長さぶんのコマで）。0.6〜1.6 なら🟢・それ以外は🟡（絵の密度が違うので目安）
"""
import argparse, json, os
import numpy as np, cv2
W20 = os.environ.get("WAZA20_TEHON") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "tehon")   # 手本の札（clip.mp4・keys.jpg）＝このスキルの中に写した物（元 ~/research/tehon-me/tehonM/waza20）
ap = argparse.ArgumentParser(); ap.add_argument("mp4"); ap.add_argument("--sec", type=int, default=75); ap.add_argument("--json", default="")
A = ap.parse_args()
idx = json.load(open(os.path.join(W20, "index.json")))
def frames(path, crop=None, size=None):
    cap = cv2.VideoCapture(path); out = []
    while True:
        ok, f = cap.read()
        if not ok: break
        if crop: f = f[crop[0]:crop[1]]
        if size: f = cv2.resize(f, size, interpolation=cv2.INTER_AREA)
        out.append(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32))
    return out
ours = frames(A.mp4, crop=(150, 1920), size=(410, 672))
res = []
for it in idx:
    n = it["n"]; ref = frames(os.path.join(W20, os.path.basename(it["dir"]), "clip.mp4"))
    m = np.zeros(ref[0].shape, bool); m[10:-10, 10:-10] = True; m[:64, -80:] = False
    rm = [float(np.abs(ref[i] - ref[i - 1])[m].mean()) for i in range(1, len(ref))]
    b = (n - 1) * A.sec; L = min(len(ref), A.sec)
    om = [float(np.abs(ours[b + i] - ours[b + i - 1]).mean()) for i in range(1, L)]
    r_med, o_med = float(np.median(rm)), float(np.median(om))
    ratio = o_med / r_med if r_med > 0 else 0
    # 手本で一番動くコマとうちで一番動くコマ
    res.append({"n": n, "name": it["name"], "ref_med": round(r_med, 2), "ours_med": round(o_med, 2), "ratio": round(ratio, 2),
                "ref_peak": int(np.argmax(rm)) + 1, "ours_peak": int(np.argmax(om)) + 1, "ok": 0.6 <= ratio <= 1.6})
    print(f"{n:2d} {it['name']:14s} 手本 {r_med:6.2f}  うち {o_med:6.2f}  比 {ratio:5.2f} {'🟢' if 0.6 <= ratio <= 1.6 else '🟡'}  山のコマ 手本 {np.argmax(rm)+1:2d}・うち {np.argmax(om)+1:2d}")
if A.json: json.dump(res, open(A.json, "w"), ensure_ascii=False, indent=1)
