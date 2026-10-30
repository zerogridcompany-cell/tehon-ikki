"""切り替えの「横に流れて白く飛ぶ」コマを、元の1コマから数字で作る（10/28 r2 13→14：手本は部屋の場面を横ぶれ＋白飛びでつなぐ・うちは手作りの白い楕円）。
python3 smear_fit.py <作業> <手本のコマ a-b> <元の絵.mp4> [--src_k 0] --cut <書くカット> [--write]
- 1コマごとに 横ずらし dx（-320〜320）・横ぶれの幅 L（0〜240）を総当たり → 色は平均と散らばりをそろえる（白飛びは濃さ 0.2〜3 で表せる）
- 点は 320 の白黒 SSIM（字幕の帯を外す）。今のカットのコマより上がったコマだけ入れる。カットのファイルが無ければ黒から作る。前の物は .bak_smear
- look 込みで比べる（retime の looks）
"""
import argparse, glob, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from retime import rd, looks, post_f, pre_f
FPS = 29.97
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("frames"); ap.add_argument("src")
ap.add_argument("--src_k", type=int, default=0); ap.add_argument("--cut", required=True); ap.add_argument("--write", action="store_true")
a = ap.parse_args(); w = os.path.abspath(a.w)
fa, fb = map(int, a.frames.split("-"))
R = rd(glob.glob(f"{w}/ref/*.mp4")[0], sel=(fa, fb)); LK = looks(w, fa, len(R))
S = rd(os.path.join(w, a.src))[a.src_k].astype(np.float32)
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{a.cut}:")][0]
c0 = round(float(seg.split(":")[1].split("-")[0]) * FPS); c1 = round(float(seg.split("-")[1]) * FPS)
cp = f"{w}/cuts/{a.cut}.mp4"
C = rd(cp).copy() if os.path.exists(cp) else np.zeros((c1 - c0, 720, 1280, 3), np.uint8)
m = np.ones((180, 320), bool); m[75:105] = False
g = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (320, 180), interpolation=cv2.INTER_AREA)


def make(dx, L, small=True):
    sc = 0.25 if small else 1.0
    x = cv2.resize(S, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA) if small else S
    M = np.float32([[1, 0, dx * sc], [0, 1, 0]])
    x = cv2.warpAffine(x, M, (x.shape[1], x.shape[0]), borderMode=cv2.BORDER_REFLECT)
    k = max(1, int(L * sc))
    return cv2.blur(x, (k, 1)) if k > 1 else x


def colmatch(x, r):
    y = np.empty_like(x)
    for c in range(3):
        k = np.clip(r[..., c].std() / max(x[..., c].std(), 1e-3), 0.2, 3.0)
        y[..., c] = (x[..., c] - x[..., c].mean()) * k + r[..., c].mean()
    return np.clip(y, 0, 255).astype(np.uint8)


n_in = 0
for i, f in enumerate(range(fa, fb + 1)):
    j = f - c0
    if j < 0 or j >= len(C): continue
    r = R[i]; rs = cv2.resize(r, (320, 180), interpolation=cv2.INTER_AREA).astype(np.float32); gr = g(r)
    best = (-1, 0, 0)
    for dx in range(-320, 321, 16):
        for L in (0, 20, 40, 60, 90, 120, 160, 200, 240):
            y = colmatch(make(dx, L), rs); sc = ssim(gr, cv2.cvtColor(y, cv2.COLOR_BGR2GRAY))
            if sc > best[0]: best = (sc, dx, L)
    full = make(best[1], best[2], small=False)
    rf = r.astype(np.float32); y = colmatch(full, rf)
    lk = LK[i]; now = ssim(gr, g(post_f(C[j], lk)))
    new_post = y  # 手本の色に直接そろえた絵＝look の後の絵
    sc_new = ssim(gr, g(new_post))
    ok = sc_new > now + 0.005
    print(f"コマ {f} dx {best[1]} L {best[2]} 今 {now:.3f} 作った {sc_new:.3f} {'入れる' if ok else ''}", flush=True)
    if ok:
        C[j] = pre_f(new_post, lk) if (lk[0] != 1).any() or lk[1].any() else new_post; n_in += 1
if a.write and n_in:
    if os.path.exists(cp) and not os.path.exists(cp + ".bak_smear"): shutil.copy(cp, cp + ".bak_smear")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "1280x720", "-r", "2997/100", "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", cp], stdin=subprocess.PIPE)
    p.stdin.write(C.tobytes()); p.stdin.close(); p.wait(); print("書いた", cp, n_in, "コマ")
