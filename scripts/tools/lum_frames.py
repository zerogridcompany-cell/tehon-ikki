"""lum_frames.py  一枚絵のコマごとの明るさの比（手本÷うちの絵）を測る＝タイムラプス・点滅・明るさが毎コマ変わる場面に（51 の lum_subway.py・lum_shot.py の汎用版）。
使い方：python3 lum_frames.py <作業> <id> [<id> …] [--write] [--min 0.03]
入れる物：proj/public/green/<id>.png・green.json（M）・手本・caps.json（字幕の箱は測らん）
コマごとに：絵を M[f] で置いた所（縁 3px を削る）だけで、手本の灰の平均 ÷ 置いた絵の灰の平均 → 0.4〜1.8 で頭打ち
出す物：比の幅を出す。--write で green.json のその絵に "lum": {"<f>": 比}（1.00±--min の内のコマは書かん）
効いた数字（51）：44〜45秒（地下鉄のタイムラプス）ΔE 4.8/4.1→2.8/2.3
採る条件：比の幅（最大−最小）が 0.1 以上ある絵だけ＝コマで明るさが動く場面。幅が小さい絵は look_shot（カットごと）で足りる
🔴 Green.tsx に brightness(lum[f]) を足す所が要る（CAMERA_LOOK_README.md「lum」）
"""
import argparse, json, os, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tk_common import ref_path, probe, gray, load_caps, cap_mask, footprint

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("ids", nargs="+"); ap.add_argument("--write", action="store_true"); ap.add_argument("--min", type=float, default=0.03)
a = ap.parse_args()
GJ = os.path.join(a.w, "proj", "src", "green.json"); G = json.load(open(GJ))
ref = ref_path(a.w); W, H, _, _ = probe(ref); caps = load_caps(a.w)
for pid in a.ids:
    if pid not in G:
        print(pid, "green.json に無い"); continue
    p = G[pid]; pl = cv2.imread(os.path.join(a.w, "proj", "public", "green", f"{pid}.png"), cv2.IMREAD_GRAYSCALE)
    R = gray(ref, p["f0"], p["f1"] - p["f0"] + 1, W, H); out = {}
    for i, f in enumerate(range(p["f0"], p["f1"] + 1)):
        if i >= len(R) or str(f) not in p["M"]:
            continue
        M = np.array(p["M"][str(f)], np.float64).reshape(2, 3)
        mk = footprint(p, M, W, H) & ~cap_mask(caps, f, W, H)
        if mk.sum() < 500:
            continue
        o = cv2.warpAffine(pl, M, (W, H), flags=cv2.INTER_LINEAR)
        out[f] = round(float(np.clip(R[i][mk].mean() / max(o[mk].mean(), 1.0), 0.4, 1.8)), 3)
    if not out:
        print(pid, "測れん"); continue
    v = list(out.values())
    print(pid, f"比 {min(v):.2f}〜{max(v):.2f}（幅 {max(v) - min(v):.2f}）中央値 {np.median(v):.2f}", "🟢 コマで明るさが動く" if max(v) - min(v) >= 0.1 else "")
    if a.write:
        p["lum"] = {str(f): r for f, r in out.items() if abs(r - 1) > a.min}
if a.write:
    json.dump(G, open(GJ, "w")); print("green.json に lum を書いた")
