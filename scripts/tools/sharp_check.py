"""原寸の鋭さ（ラプラシアンの分散）を手本とうちでカットごとに比べる（10/28 r2 138：元の写真は鋭さ 2831 なのに合わせの段でぼかして手本 138／うち 36。kakeru の 320 では見えん）。
python3 sharp_check.py <作業> <うちの書き出し_noaudio.mp4> [--out shirabe/鋭さ表.json]
- 字幕の帯（高さ 41.6〜58.3%）と端 16px を外す・カットの 1/4・1/2・3/4 のコマの中央値
- 比＝うち÷手本。🔴 0.5 未満（ぼかしすぎ）／🟡 0.5〜0.75／🟠 1.6 より上（鋭すぎ）
"""
import argparse, glob, json, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import geo
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("ours"); ap.add_argument("--out", default="shirabe/鋭さ表.json")
a = ap.parse_args(); w = os.path.abspath(a.w); FPS = geo(w)["FPS"]  # 10/30 geo
cr, co = cv2.VideoCapture(glob.glob(f"{w}/ref/*.mp4")[0]), cv2.VideoCapture(a.ours)
def lap(cap, n):
    cap.set(1, n); ok, f = cap.read()
    if not ok: return None
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float64); H = g.shape[0]
    L = cv2.Laplacian(g, cv2.CV_64F)[16:-16, 16:-16]; m = np.ones(L.shape, bool); m[int(H * .416) - 16:int(H * .583) - 16] = False
    return float(L[m].var())
rows = []
for l in open(f"{w}/eye/segs.txt"):
    c, t = l.strip().split(":"); s0, s1 = map(float, t.split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS)
    ks = sorted({f0 + max(1, (f1 - f0) * q // 4) for q in (1, 2, 3)})
    r = np.median([lap(cr, k) for k in ks]); o = np.median([lap(co, k) for k in ks])
    ratio = o / max(r, 1e-6)
    ok = "🔴" if ratio < 0.5 else "🟡" if ratio < 0.75 else "🟠" if ratio > 1.6 else "✅"
    rows.append({"cut": c, "f0": f0, "f1": f1, "ref": round(r, 1), "ours": round(o, 1), "ratio": round(ratio, 2), "ok": ok})
json.dump(rows, open(os.path.join(w, a.out), "w"), ensure_ascii=False, indent=1)
from collections import Counter
print(Counter(r["ok"] for r in rows))
bad = sorted([r for r in rows if r["ok"] in ("🔴", "🟡")], key=lambda r: r["ratio"])
print("ぼかしすぎ:", sum(r["f1"] - r["f0"] for r in bad), "コマ")
print(" ".join(f'{r["cut"]}:{r["ratio"]}({r["f1"]-r["f0"]})' for r in bad))
print("鋭すぎ:", " ".join(f'{r["cut"]}:{r["ratio"]}' for r in rows if r["ok"] == "🟠"))
