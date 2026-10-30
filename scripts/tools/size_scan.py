"""大きさ・位置を「画素の重なり」で直接探す（size_sift の目印の点と食い違った時の正解決め・10/28 r2）。
python3 size_scan.py <作業> <カット番号> [--file cuts/<番号>.mp4] [--write]
- カットの全コマに、真ん中を中心に s 倍＋(dx,dy) をかけて、look（shot_look）込みで手本と SSIM（640 白黒）
- s は 0.95〜1.05（0.005 刻み）→ 一番良い所の前後 0.001 刻み、dx・dy は −12〜12px（2px 刻み→1px）
- 出す値：一番合う s・dx・dy と SSIM。今（1.0・0・0）より 0.002 以上良い時だけ --write で書く（前の物は .bak_scan）
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from retime import rd, looks, post_f
import retime
from geo import geo
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut"); ap.add_argument("--file"); ap.add_argument("--write", action="store_true")
a = ap.parse_args(); w = os.path.abspath(a.w)
retime.use_geo(w); GG = geo(w); W, H, FPS = GG["W"], GG["H"], GG["FPS"]  # 10/30 geo
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{a.cut}:")][0]
s0, s1 = map(float, seg.split(":")[1].split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS)
R = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(f0, f1 - 1)); n = len(R)
fp = a.file or f"{w}/cuts/{a.cut}.mp4"; C = rd(fp)[:n]
LK = looks(w, f0, n)
# 速さのため半分の大きさで探す（ずれは手本の px に直す）
q = 0.5; w2, h2 = int(W * q), int(H * q)
Rg = [cv2.cvtColor(cv2.resize(r, (w2, h2), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY) for r in R]
Cp = [cv2.resize(post_f(c, LK[i]), (w2, h2), interpolation=cv2.INTER_AREA) for i, c in enumerate(C)]
idx = list(range(0, n, max(1, n // 8)))
def score(s, dx, dy):
    M = np.float32([[s, 0, (1 - s) * w2 / 2 + dx * q], [0, s, (1 - s) * h2 / 2 + dy * q]])
    return float(np.mean([ssim(Rg[i], cv2.cvtColor(cv2.warpAffine(Cp[i], M, (w2, h2), borderMode=cv2.BORDER_REFLECT), cv2.COLOR_BGR2GRAY)) for i in idx]))
base = score(1, 0, 0); best = (base, 1.0, 0, 0)
for s in np.arange(0.95, 1.0501, 0.005):
    sc = score(s, 0, 0)
    if sc > best[0]: best = (sc, float(s), 0, 0)
for it in range(2):
    st = 2 if it == 0 else 1
    for dx in range(-12, 13, st):
        for dy in range(-12, 13, st):
            if it and (abs(dx - best[2]) > 2 or abs(dy - best[3]) > 2): continue
            sc = score(best[1], dx, dy)
            if sc > best[0]: best = (sc, best[1], dx, dy)
    for s in np.arange(best[1] - 0.005, best[1] + 0.0051, 0.001):
        sc = score(s, best[2], best[3])
        if sc > best[0]: best = (sc, float(s), best[2], best[3])
print(f"カット {a.cut} 今 {base:.4f} → s {best[1]:.3f} dx {best[2]} dy {best[3]} = {best[0]:.4f}")
if a.write and best[0] > base + 0.002:
    M = np.float32([[best[1], 0, (1 - best[1]) * W / 2 + best[2]], [0, best[1], (1 - best[1]) * H / 2 + best[3]]])
    Cf = rd(fp)
    out = np.stack([cv2.warpAffine(c, M, (W, H), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT) for c in Cf])
    cp = f"{w}/cuts/{a.cut}.mp4"
    if not os.path.exists(cp + ".bak_scan"): shutil.copy(cp, cp + ".bak_scan")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", GG["FPS_FF"], "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", cp], stdin=subprocess.PIPE)
    p.stdin.write(out.tobytes()); p.stdin.close(); p.wait(); print("書いた", cp)
