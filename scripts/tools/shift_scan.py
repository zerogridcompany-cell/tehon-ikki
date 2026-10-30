"""カット全体の時刻のずれ（コマ単位）を測って直す（10/28 r2：96 がうちが1コマ早かった＝手本の重複コマの位置が1つずれ）。
python3 shift_scan.py <作業> [--ids 1,2] [--write] [--min 0.003]
- カットの中身を −2〜+2 コマずらして（端は端のコマを伸ばす）、look 込みでなく白黒 320 の SSIM で手本と比べる
- 写真の替わる位置（前のコマとの差 >20）が手本から遠くなるずれは選ばん
- 0 より --min 以上良いずれがあれば --write で書く（前の物は .bak_shift）。カットの長さは変えん
"""
import argparse, glob, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from retime import rd
FPS = 29.97
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--ids", default=""); ap.add_argument("--write", action="store_true"); ap.add_argument("--min", type=float, default=0.003)
a = ap.parse_args(); w = os.path.abspath(a.w)
ids = set(a.ids.split(",")) if a.ids else None
ref = glob.glob(f"{w}/ref/*.mp4")[0]
RA = rd(ref, w=320, h=180)
g = lambda x: cv2.cvtColor(x, cv2.COLOR_BGR2GRAY)
for l in open(f"{w}/eye/segs.txt"):
    if ":" not in l: continue
    cut = l.split(":")[0].strip()
    if ids and cut not in ids: continue
    cp = f"{w}/cuts/{cut}.mp4"
    if not os.path.exists(cp): continue
    s0, s1 = map(float, l.split(":")[1].split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS)
    R = RA[f0:f1]; C = rd(cp, w=320, h=180)
    if len(C) < len(R) or len(R) < 4: continue
    n = len(R); res = []
    for sh in (-2, -1, 0, 1, 2):
        res.append((float(np.mean([ssim(g(R[k]), g(C[min(len(C) - 1, max(0, k + sh))])) for k in range(n)])), sh))
    base = [s for s, sh in res if sh == 0][0]
    sw = lambda X: {i for i in range(1, len(X)) if np.abs(X[i].astype(float) - X[i - 1]).mean() > 20}
    sR = sw(R); bad0 = len(sw(C[:n]) ^ sR)
    def sh_ok(sh):  # 替わる位置が手本から遠くならん時だけ（10/28 r2 の 2 で 0.567秒の切れ目を落とした）
        X = np.stack([C[min(len(C) - 1, max(0, k + sh))] for k in range(n)]); return len(sw(X) ^ sR) <= bad0
    res = [(s_, sh) for s_, sh in res if sh == 0 or sh_ok(sh)]; best = max(res)
    if best[1] != 0 and best[0] > base + a.min:
        print(f"カット {cut} ずれ {best[1]:+d} コマ {base:.4f}→{best[0]:.4f}", flush=True)
        if a.write:
            C1 = rd(cp)
            out = np.stack([C1[min(len(C1) - 1, max(0, k + best[1]))] for k in range(len(C1))])
            if not os.path.exists(cp + ".bak_shift"): shutil.copy(cp, cp + ".bak_shift")
            p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "1280x720", "-r", "2997/100", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", cp], stdin=subprocess.PIPE)
            p.stdin.write(out.tobytes()); p.stdin.close(); p.wait()
