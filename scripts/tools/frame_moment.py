"""コマごとに明るさ・濃さ（Lab の平均と散らばり）を手本へ合わせてカットのファイルに焼き込み、そのカットの shot_look の色は外す（10/28 r2 111：手本は白く光る切り替えがコマごとに違う＝カット1つの色の設定では「薄めてごまかす」しかなかった）。
python3 frame_moment.py <作業> <カット> [--write]
- --from j＝j コマ目から（前は今の色を焼くだけ）。r2 111 は --from 5 で 0.667→0.684（前の5コマは前のカットからの切り替えで中身が違う）
- 字幕の帯は外して測る。--write で cuts/<番号>.mp4（前は .bak_fm）と shot_look（g=1・o=0・ぼかしは残す）を書く
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from retime import rd, looks, post_f
import retime
from geo import geo, half
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut"); ap.add_argument("--write", action="store_true"); ap.add_argument("--from", dest="jfrom", type=int, default=0, help="このコマ（カットの中の番号）から合わせる。前のコマは今の色をそのまま焼く（切り替えの途中で中身が違うコマ）")
a = ap.parse_args(); w = os.path.abspath(a.w); c = a.cut
retime.use_geo(w); GG = geo(w); FPS = GG["FPS"]; MW, MH = half(w)
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{c}:")][0]
s0, s1 = map(float, seg.split(":")[1].split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS)
R = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(f0, f1 - 1)); n = len(R); LK = looks(w, f0, n); cp = f"{w}/cuts/{c}.mp4"; C = rd(cp)[:n]
H, W = R.shape[1:3]; m = np.ones((H, W), bool); m[int(H * .416):int(H * .583)] = False
out = []
for j in range(n):
    if j < a.jfrom: out.append(post_f(C[j], (LK[j][0], LK[j][1], 0))); continue
    xl = cv2.cvtColor(C[j], cv2.COLOR_BGR2LAB).astype(np.float32); rl = cv2.cvtColor(R[j], cv2.COLOR_BGR2LAB).astype(np.float32)
    for ch in range(3):
        k = np.clip(rl[..., ch][m].std() / max(xl[..., ch][m].std(), 1e-3), 0.3, 3.0)
        xl[..., ch] = (xl[..., ch] - xl[..., ch][m].mean()) * k + rl[..., ch][m].mean()
    out.append(cv2.cvtColor(np.clip(xl, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR))
out = np.stack(out)
L = json.load(open(f"{w}/proj/src/shot_look.json")); lk = dict(L.get(c, {"f0": f0, "f1": f1 - 1})); blur = lk.get("blur", 0)
LK2 = [(np.ones(3, np.float32), np.zeros(3, np.float32), blur, *x[3:]) if isinstance(x, tuple) else x for x in LK]
g = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (MW, MH), interpolation=cv2.INTER_AREA)
sb = np.mean([ssim(g(R[j]), g(post_f(C[j], LK[j]))) for j in range(n)])
# 色の設定を外した形で比べる（ぼかしだけ残す）
pf = lambda x: cv2.GaussianBlur(x, (0, 0), blur) if blur else x
sa = np.mean([ssim(g(R[j]), g(pf(out[j]))) for j in range(n)])
print(f"カット {c}：点 {sb:.4f} → {sa:.4f}")
if a.write and sa > sb:
    shutil.copy(cp, cp + ".bak_fm") if not os.path.exists(cp + ".bak_fm") else None
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", GG["FPS_FF"], "-i", "-", "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", cp], stdin=subprocess.PIPE)
    p.stdin.write(out.tobytes()); p.stdin.close(); p.wait()
    lk["g"] = [1.0, 1.0, 1.0]; lk["o"] = [0.0, 0.0, 0.0]; L[c] = lk
    shutil.copy(f"{w}/proj/src/shot_look.json", f"{w}/proj/src/shot_look.json.bak_fm")
    json.dump(L, open(f"{w}/proj/src/shot_look.json", "w"), ensure_ascii=False, indent=1); print("書いた")
