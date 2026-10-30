"""手本にある絵が、うちでは欠けとる・ぼやけとる所をカットごとに数える（10/28 r2 カット9：手本は横長の写真が画面いっぱい・うちは縦長の写真＋両脇が紺の帯でぼやけ）。
python3 kakeru.py <作業> <書き出し_noaudio.mp4> [--out shirabe/欠け表.json] [--top 40]
- 物差し（320x180・字幕の帯を外す・カットの中の3コマ）
  欠け＝手本はきめ（エッジ）があるのに、うちはほぼ平ら（手本の1/4未満）な面積の割合 → 帯・小さい置き方・切り抜き不足
  左右／上下の欠け＝欠けが画面の端の列・行に寄っとるか（帯の形）
  ぼけ＝うちのエッジの強さ÷手本（1.0 で同じ・0.6 未満はぼやけ）
- 🔴 の条件：欠け 8% 以上、またはぼけ 0.6 未満（手本のきめが少ないカットは外す）
- size_scan（大きさ 0.95〜1.05）では拾えん「絵の範囲そのものが違う」を拾うための物差し
"""
import argparse, glob, json, os, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retime import rd
FPS = 29.97
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("render")
ap.add_argument("--out", default="shirabe/欠け表.json"); ap.add_argument("--top", type=int, default=40)
a = ap.parse_args(); w = os.path.abspath(a.w)
RA = rd(glob.glob(f"{w}/ref/*.mp4")[0], w=320, h=180); VA = rd(os.path.join(w, a.render), w=320, h=180)
m = np.ones((180, 320), bool); m[75:105] = False  # 字幕の帯


def edge(x):
    g = cv2.cvtColor(x, cv2.COLOR_BGR2GRAY).astype(np.float32)
    e = np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))
    return cv2.blur(e, (9, 9))


rows = []
for l in open(f"{w}/eye/segs.txt"):
    if ":" not in l: continue
    cut = l.split(":")[0].strip(); s0, s1 = map(float, l.split(":")[1].split("-"))
    f0, f1 = round(s0 * FPS), round(s1 * FPS)
    if f1 - f0 < 3 or f1 > min(len(RA), len(VA)): continue
    ks = [f0 + (f1 - f0) * q // 4 for q in (1, 2, 3)]
    miss, ratio, cols, rws = [], [], np.zeros(320), np.zeros(180)
    for k in ks:
        er, eo = edge(RA[k]), edge(VA[k])
        tex = (er > 12) & m
        if tex.sum() < 0.05 * m.sum(): continue
        mi = tex & (eo < er / 4)
        miss.append(mi.sum() / m.sum()); ratio.append(eo[m].mean() / max(er[m].mean(), 1e-3))
        cols += mi.sum(0); rws += mi.sum(1)
    if not miss: continue
    ms, rt = float(np.mean(miss)), float(np.mean(ratio))
    tot = cols.sum() + 1e-6
    side = float((cols[:64].sum() + cols[-64:].sum()) / tot)  # 左右の端 1/5 ずつに寄っとる割合
    tb = float((rws[:36].sum() + rws[-36:].sum()) / tot)
    red = ms >= 0.08 or rt < 0.6
    rows.append(dict(cut=cut, f0=f0, f1=f1, kake=round(ms, 3), boke=round(rt, 2), sayu=round(side, 2), jouge=round(tb, 2), red=red))
rows.sort(key=lambda r: (-r["kake"], r["boke"]))
os.makedirs(os.path.dirname(os.path.join(w, a.out)), exist_ok=True)
json.dump(rows, open(os.path.join(w, a.out), "w"), ensure_ascii=False, indent=1)
print(f"🔴 {sum(r['red'] for r in rows)} / {len(rows)} カット")
print("カット  コマ        欠け   ぼけ  左右  上下")
for r in rows[:a.top]:
    print(f"{'🔴' if r['red'] else '  '}{r['cut']:>4} {r['f0']:>5}-{r['f1']:<5} {r['kake']*100:5.1f}% {r['boke']:5.2f} {r['sayu']:5.2f} {r['jouge']:5.2f}")
