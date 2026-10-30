"""うちの書き出しと手本を、カットごとに「絵の大きさ（拡大率）と位置（ずれ）」で比べる。
python3 size_check.py <作業> <書き出し.mp4> [--out tmp/size_check.json]
- カットごとに最大5コマ：うち→手本 を ECC（相似＝拡大・回転・移動）で当てる（480 幅の白黒・字幕の帯を外す・ぼかし1.5）
- 当たりの強さ cc が 0.5 以上のコマだけ使い、中央値で 拡大率・ずれ(px, 手本の幅・r2 は 1280)を出す
- 表＝ずれの大きい順（|拡大率−1|×100 ＋ ずれ/10）
"""
import glob
import argparse, json, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import frames
import cut_score
from geo import geo
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("out"); ap.add_argument("--json", default="tmp/size_check.json")
a = ap.parse_args(); w = os.path.abspath(a.w)
cut_score.use_geo(w); GG = geo(w); FPS = GG["FPS"]; h480 = round(480 * GG["H"] / GG["W"])  # 10/30 geo（r2 は 270）
R = frames(glob.glob(f"{w}/ref/*.mp4")[0]); V = frames(os.path.join(w, a.out)); n = min(len(R), len(V))
mask = np.ones((h480, 480), np.uint8); mask[round(105 * h480 / 270):round(165 * h480 / 270)] = 0  # 字幕の帯（r2 の行を高さの比で）
segs = []
for l in open(f"{w}/eye/segs.txt"):
    if ":" in l:
        k, v = l.split(":"); s0, s1 = map(float, v.split("-")); segs.append((k.strip(), round(s0 * FPS), min(n, round(s1 * FPS))))
rows = []
for k, f0, f1 in segs:
    if f1 - f0 < 2: continue
    idx = np.linspace(f0, f1 - 1, min(5, f1 - f0)).astype(int)
    S, T, C = [], [], []
    for f in idx:
        r = cv2.GaussianBlur(cv2.resize(R[f], (480, h480)).astype(np.float32), (0, 0), 1.5)
        o = cv2.GaussianBlur(cv2.resize(V[f], (480, h480)).astype(np.float32), (0, 0), 1.5)
        if r.std() < 8 or o.std() < 8: continue
        M = np.eye(2, 3, dtype=np.float32)
        try:
            cc, M = cv2.findTransformECC(r, o, M, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), mask, 5)
        except cv2.error:
            continue
        if cc < 0.5: continue
        # M：手本の点 p → うちの点 M p。うちの絵の大きさ／手本の大きさ = 拡大率
        s = float(np.sqrt(abs(np.linalg.det(M[:, :2]))))
        c = np.array([240, h480 / 2, 1.0]); d = (M @ c)[:2] - c[:2]
        S.append(s); T.append(np.hypot(*d) * GG["W"] / 480); C.append(cc)
    if not S: rows.append({"cut": k, "f0": int(f0), "f1": int(f1), "n": 0}); continue
    s = float(np.median(S)); t = float(np.median(T))
    rows.append({"cut": k, "f0": int(f0), "f1": int(f1), "n": len(S), "scale": round(s, 3), "shift": round(t, 1), "cc": round(float(np.median(C)), 2),
                 "bad": round(abs(s - 1) * 100 + t / 10, 2)})
rows_ok = sorted([r for r in rows if r["n"]], key=lambda r: -r["bad"])
json.dump(rows, open(os.path.join(w, a.json), "w"), indent=1)
print("カット 拡大率(うち/手本) ずれpx 当たり コマ数")
for r in rows_ok:
    if r["bad"] >= 2: print(r["cut"], r["scale"], r["shift"], r["cc"], r["f1"] - r["f0"])
print("測れたカット", len(rows_ok), "／測れんかった", len([r for r in rows if not r["n"]]), "／ずれ大（2以上）", len([r for r in rows_ok if r["bad"] >= 2]))
