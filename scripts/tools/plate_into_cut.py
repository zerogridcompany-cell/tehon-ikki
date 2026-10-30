"""一枚絵（Codex の描き直し・公有の絵）を、手本の決まったコマに1コマずつ ECC（拡大・移動）で詰めて、カットの該当コマに直接はめる。
python3 plate_into_cut.py <作業> <カット番号> <絵.png> --frames 1748-1758 [--invert] [--min 0.005]
- 初めの位置＝絵を手本の大きさ（r2 は 1280x720）に合わせただけ。ECC は 480 幅・字幕の帯を外す。色は色ごとの1次・ぼかし 0〜3 の良い方
- --invert＝白黒反転してから合わせる（手本の反転のコマ）
- コマごとに今より SSIM（手本の半分の白黒・r2 は 640）が --min 以上上がった時だけ入れる。前の物は .bak_pc
"""
import glob
import argparse, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from geo import geo, half
W, H, FPS = 1280, 720, 29.97   # 引数を読んだ後に geo(<作業>) に替わる（10/30）
FPS_FF = "2997/100"
def rd_range(p, a, b):
    # 手本の a〜b コマだけ読む（全部読むと r2 の 1280x720 で約6GB＝16GB の Mac が詰まる）
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"fps={FPS_FF},select='between(n\\,{a}\\,{b})',scale={W}:{H}", "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    fr = np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3)
    return {a + i: fr[i] for i in range(len(fr))}
def rd(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"fps={FPS_FF},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).copy()
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut"); ap.add_argument("img"); ap.add_argument("--frames", required=True)
ap.add_argument("--invert", action="store_true"); ap.add_argument("--min", type=float, default=0.005)
a = ap.parse_args(); w = os.path.abspath(a.w)
GG = geo(w); W, H, FPS, FPS_FF = GG["W"], GG["H"], GG["FPS"], GG["FPS_FF"]; MW, MH = half(w)
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{a.cut}:")][0]
c0 = round(float(seg.split(":")[1].split("-")[0]) * FPS)
cutp = f"{w}/cuts/{a.cut}.mp4"; C = rd(cutp)
im = cv2.resize(cv2.imread(a.img), (W, H))
if a.invert: im = 255 - im
g = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (MW, MH))
txt = np.ones((H, W), bool); txt[round(300 * H / 720):round(420 * H / 720)] = False  # 字幕の帯（r2 の行を高さの比で）
h480 = round(480 * H / W); t480 = np.ones((h480, 480), np.uint8); t480[round(112 * h480 / 270):round(158 * h480 / 270)] = 0
f0, f1 = map(int, a.frames.split("-")); n_in = 0
R = rd_range(glob.glob(f"{w}/ref/*.mp4")[0], f0, f1)
for f in range(f0, f1 + 1):
    j = f - c0
    if j < 0 or j >= len(C): continue
    r = R[f]
    s = 480 / W
    rg = cv2.resize(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY), (480, h480)).astype(np.float32)
    ig = cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (480, h480)).astype(np.float32)
    M = np.eye(2, 3, dtype=np.float32)
    try:
        _, M = cv2.findTransformECC(rg, ig, M, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-5), t480, 3)
    except cv2.error:
        pass
    Mf = M.copy(); Mf[:, 2] /= s
    wc = cv2.warpAffine(im, Mf, (W, H), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
    fit = wc.astype(np.float32)
    for c in range(3):
        k, b = np.polyfit(wc[..., c][txt].astype(np.float32), r[..., c][txt].astype(np.float32), 1); fit[..., c] = wc[..., c] * k + b
    best = None
    for bl in (0, 1, 2, 3):
        fb = np.clip(cv2.GaussianBlur(fit, (0, 0), bl) if bl else fit, 0, 255).astype(np.uint8); sc = ssim(g(r), g(fb))
        if best is None or sc > best[0]: best = (sc, fb)
    cur = ssim(g(r), g(C[j]))
    ok = best[0] > cur + a.min
    print(f, "今", round(float(cur), 3), "絵", round(float(best[0]), 3), "入れた" if ok else "そのまま")
    if ok: C[j] = best[1]; n_in += 1
if n_in:
    if not os.path.exists(cutp + ".bak_pc"): shutil.copy(cutp, cutp + ".bak_pc")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", FPS_FF, "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", cutp], stdin=subprocess.PIPE)
    p.stdin.write(C.tobytes()); p.stdin.close(); p.wait(); print("書いた", cutp, n_in, "コマ")
