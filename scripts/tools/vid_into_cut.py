"""生成した動画（始めと終わりを手本のコマに合わせて撃った物など）を、手本の決まったコマに時間を縮めて1コマずつはめる。
python3 vid_into_cut.py <作業> <カット番号> <動画> --frames a-b --map f0:i0,f1:i1 [--win 8] [--min 0.005]
- 手本のコマ f → 動画のコマ i を --map の2点で1次に対応させ、その前後 --win コマから一番合うコマを選ぶ（ECC 拡大・移動＋色の1次＋ぼかし0〜3）
- --force＝点に関係なく全部のコマを動画で入れる（手本が動いとる所は静止画と混ぜん・10/27 依頼者「画像ではなく動画」）
- 今のカットのコマより SSIM（手本の半分の白黒・r2 は 640）が --min 以上上がった時だけ入れる。前の物は .bak_vic
"""
import argparse, glob, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim
from geo import geo, half
W, H, FPS = 1280, 720, 29.97   # 引数を読んだ後に geo(<作業>) に替わる（10/30）
FPS_FF = "2997/100"
def rd(p, fps=None):
    vf = (f"fps={fps}," if fps else "") + f"scale={W}:{H}"
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).copy()
def ref_frames(ref, f0, f1):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", ref, "-vf", f"fps={FPS_FF},select='between(n\\,{f0}\\,{f1})',scale={W}:{H}", "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3)
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("cut"); ap.add_argument("vid"); ap.add_argument("--frames", required=True); ap.add_argument("--map", required=True)
ap.add_argument("--win", type=int, default=8); ap.add_argument("--min", type=float, default=0.005); ap.add_argument("--force", action="store_true", help="点に関係なく全部のコマを動画で入れる（静止画と混ぜん）")
a = ap.parse_args(); w = os.path.abspath(a.w)
GG = geo(w); W, H, FPS, FPS_FF = GG["W"], GG["H"], GG["FPS"], GG["FPS_FF"]; MW, MH = half(w)
seg = [l for l in open(f"{w}/eye/segs.txt") if l.startswith(f"{a.cut}:")][0]
c0 = round(float(seg.split(":")[1].split("-")[0]) * FPS)
cutp = f"{w}/cuts/{a.cut}.mp4"; C = rd(cutp); S = rd(a.vid)
f0, f1 = map(int, a.frames.split("-")); R = ref_frames(glob.glob(f"{w}/ref/*.mp4")[0], f0, f1)
(m0, i0), (m1, i1) = [tuple(map(int, x.split(":"))) for x in a.map.split(",")]
g = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (MW, MH))
txt = np.ones((H, W), bool); txt[round(300 * H / 720):round(420 * H / 720)] = False  # 字幕の帯（r2 の行を高さの比で）
h480 = round(480 * H / W); t480 = np.ones((h480, 480), np.uint8); t480[round(112 * h480 / 270):round(158 * h480 / 270)] = 0
n_in = 0
for k, f in enumerate(range(f0, f1 + 1)):
    r = R[k]; j = f - c0; cur = ssim(g(r), g(C[j]))
    ic = min(len(S) - 1, max(0, int(round(i0 + (f - m0) * (i1 - i0) / (m1 - m0)))))
    best = (-9 if a.force else cur, None, None)
    for i in range(max(0, ic - a.win), min(len(S) - 1, ic + a.win) + 1, 2):
        im = S[i]
        rg = cv2.resize(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY), (480, h480)).astype(np.float32)
        ig = cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (480, h480)).astype(np.float32)
        M = np.eye(2, 3, dtype=np.float32)
        try: _, M = cv2.findTransformECC(rg, ig, M, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 60, 1e-5), t480, 3)
        except cv2.error: pass
        Mf = M.copy(); Mf[:, 2] *= W / 480
        wc = cv2.warpAffine(im, Mf, (W, H), flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)
        fit = wc.astype(np.float32)
        for c in range(3):
            kk, b = np.polyfit(wc[..., c][txt].astype(np.float32), r[..., c][txt].astype(np.float32), 1); fit[..., c] = wc[..., c] * kk + b
        for bl in (0, 1, 2):
            fb = np.clip(cv2.GaussianBlur(fit, (0, 0), bl) if bl else fit, 0, 255).astype(np.uint8); s = ssim(g(r), g(fb))
            if s > best[0] + (0 if a.force else a.min): best = (s, fb, i)
    print(f, "今", round(float(cur), 3), "→", round(float(best[0]), 3), "動画のコマ", best[2])
    if best[1] is not None: C[j] = best[1]; n_in += 1
if n_in:
    if not os.path.exists(cutp + ".bak_vic"): shutil.copy(cutp, cutp + ".bak_vic")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", FPS_FF, "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", cutp], stdin=subprocess.PIPE)
    p.stdin.write(C.tobytes()); p.stdin.close(); p.wait(); print("書いた", n_in, "コマ")
