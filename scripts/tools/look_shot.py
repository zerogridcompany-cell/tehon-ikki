"""look_shot.py <作業> <うち.mp4> [--out proj/src/shot_look.json]  場面ごとの見た目（51 の shot_color・lum_shot・blur_shot2 の汎用版）。
カット（eye/out.json の t0〜t1）ごとに、手本とうちを geo の SW x SH（r2 は 320x180）で 8コマ測って：
  色＝チャンネルごとのゲイン（幅の比 0.75〜1.33）＋オフセット（平均を手本へ）＝明るさもここで合う
  やわらかさ＝ぼかしの強さ σ（手本の画素・r2 は 1280 幅の px）を 0〜4 から SSIM が一番高い物
採る条件：色＝ΔE が 0.5 以上下がって SSIM が 0.002 より下がらん時だけ／ぼかし＝SSIM が 0.003 より上がる時だけ。
黒いまま（うちの明るさ 4 未満）のカットは触らん。
前の shot_look.json があれば重ねる（色＝g·(g0·x＋o0)＋o・ぼかし＝√(σ0²＋σ²)）＝書き出し→測る→書き出し を何回でも回せる。
出す物：{"<カット番号>": {"f0","f1","g":[r,g,b],"o":[r,g,b](0〜1),"blur":σ}} → R2.tsx（Main）が全部の層の上にかける。
🔴 SVG の feColorMatrix は color-interpolation-filters="sRGB" を付ける（無いと linearRGB で計算されて色がずれる）
"""
import argparse, glob, json, os, subprocess, sys
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("mine"); ap.add_argument("--out", default="proj/src/shot_look.json")
a = ap.parse_args()
ref = glob.glob(f"{a.w}/ref/*.mp4")[0]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import geo, half
G = geo(a.w); W, H = G["SW"], G["SH"]  # 10/30 geo


def frames(p):
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", p, "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)


def lab(rgb):
    c = rgb / 255.0; c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    x, y, z = (M @ c) / np.array([0.95047, 1.0, 1.08883])
    f = lambda t: np.where(t > 0.008856, np.cbrt(t), 7.787 * t + 16 / 116)
    return np.array([116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))])


def score(R, O):
    return float(np.mean([ssim(cv2.cvtColor(r, cv2.COLOR_RGB2GRAY), cv2.cvtColor(o, cv2.COLOR_RGB2GRAY), data_range=255) for r, o in zip(R, O)]))


RF, OF = frames(ref), frames(a.mine)
n = min(len(RF), len(OF)); fps = G["FPS"]
shots = json.load(open(f"{a.w}/eye/out.json"))["shots"]
import os
OLD = json.load(open(f"{a.w}/{a.out}")) if os.path.exists(f"{a.w}/{a.out}") else {}
out = dict(OLD); tot = [0, 0]
for s in shots:
    f0, f1 = int(round(s["t0"] * fps)), min(int(round(s["t1"] * fps)) - 1, n - 1)
    if f1 - f0 < 4: continue
    fs = np.linspace(f0 + 1, f1 - 1, min(8, f1 - f0 - 1)).astype(int)
    R, O = RF[fs].astype(np.float32), OF[fs].astype(np.float32)
    if O.mean() < 4: continue
    Rp, Op = R.reshape(-1, 3), O.reshape(-1, 3)
    s0 = score(R.astype(np.uint8), O.astype(np.uint8)); de0 = float(np.linalg.norm(lab(Rp.mean(0)) - lab(Op.mean(0))))
    g = np.clip(Rp.std(0) / (Op.std(0) + 1e-3), 0.75, 1.33); o = Rp.mean(0) - g * Op.mean(0)
    T = np.clip(O * g + o, 0, 255)
    de1 = float(np.linalg.norm(lab(Rp.mean(0)) - lab(T.reshape(-1, 3).mean(0)))); s1 = score(R.astype(np.uint8), T.astype(np.uint8))
    rec = {"f0": f0, "f1": f1}
    if de1 <= de0 - 0.5 and s1 >= s0 - 0.002:
        base, sb = T, s1; rec.update(g=[round(float(x), 4) for x in g], o=[round(float(x) / 255, 4) for x in o])
    else:
        base, sb = O, s0
    best = (sb, 0.0)
    for sg in (0.5, 1, 1.5, 2, 3, 4):
        k = sg * W / G["W"]
        B = np.stack([cv2.GaussianBlur(b, (0, 0), k) for b in base]).astype(np.uint8)
        sc = score(R.astype(np.uint8), B)
        if sc > best[0]: best = (sc, sg)
    if best[0] > sb + 0.003: rec["blur"] = best[1]; sb = best[0]
    if len(rec) > 2:
        old = OLD.get(str(s["i"]))
        if old:
            g0, o0 = np.array(old.get("g", [1, 1, 1])), np.array(old.get("o", [0, 0, 0]))
            g1, o1 = np.array(rec.get("g", [1, 1, 1])), np.array(rec.get("o", [0, 0, 0]))
            if "g" in rec or "g" in old: rec["g"] = [round(float(x), 4) for x in g1 * g0]; rec["o"] = [round(float(x), 4) for x in g1 * o0 + o1]
            b = float(np.hypot(old.get("blur", 0), rec.get("blur", 0)))
            if b > 0: rec["blur"] = round(b, 2)
        out[str(s["i"])] = rec
        print(f'{s["i"]:>4} f{f0}-{f1} SSIM {s0:.3f}→{sb:.3f} ΔE {de0:.1f}→{de1 if "g" in rec else de0:.1f} blur {rec.get("blur", 0)}')
    tot[0] += s0 * len(range(f0, f1 + 1)); tot[1] += sb * len(range(f0, f1 + 1))
json.dump(out, open(f"{a.w}/{a.out}", "w"))
print(f"直したカット {len(out)}・明るいカットの SSIM の和 {tot[0]:.0f}→{tot[1]:.0f}（全体の伸びの見込み +{(tot[1] - tot[0]) / n:.3f}）")
