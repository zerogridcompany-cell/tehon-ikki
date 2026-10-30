"""元の動画のカットに、手本と同じ量の粒（フィルムのざらつき）を足す（10/28 r2：粒は Green.tsx の一枚絵の層にしか無く、121 は手本 0.79／うち 0.02。粒が無いと「ぼけ」に見え、鋭さの物差しも外れる）。
python3 grain_cut.py <作業> <書き出し_noaudio.mp4> [--ids 121,124] [--write]
- 粒の量＝平らな所（輪郭の弱い下 40%・字幕の帯は外す）で、σ2 のぼかしとの差の散らばり。カットの 1/4・1/2・3/4 のコマの中央値
- 足す量＝√(手本²−うち²)。粒の粗さは σ0.6 でならした白黒の揺れ＋その 30% の色の揺れ。コマごとに種を変える
- 0.15 未満・1.5 超え（模様を拾っとる）は足さん。前の物は .bak_grain。🔴 同じカットに2回かけん（.bak_grain があったら止める）
"""
import argparse, glob, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retime import rd
import retime
from geo import geo
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("out"); ap.add_argument("--ids"); ap.add_argument("--write", action="store_true")
a = ap.parse_args(); w = os.path.abspath(a.w)
retime.use_geo(w); GG = geo(w); FPS, W, H = GG["FPS"], GG["W"], GG["H"]
cr, co = cv2.VideoCapture(glob.glob(f"{w}/ref/*.mp4")[0]), cv2.VideoCapture(os.path.join(w, a.out))


def noise(cap, n):
    cap.set(1, n); ok, f = cap.read()
    if not ok: return None
    g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32); hp = g - cv2.GaussianBlur(g, (0, 0), 2)
    gs = cv2.GaussianBlur(g, (0, 0), 3); gr = np.hypot(cv2.Sobel(gs, cv2.CV_32F, 1, 0), cv2.Sobel(gs, cv2.CV_32F, 0, 1))
    fl = gr <= np.percentile(gr, 40); H = g.shape[0]; fl[int(H * .416):int(H * .583)] = False; fl[:16] = fl[-16:] = False
    return float(hp[fl].std()) if fl.sum() > 1000 else None


ids = a.ids.split(",") if a.ids else None
rows = []
for l in open(f"{w}/eye/segs.txt"):
    c, t = l.strip().split(":")
    if ids and c not in ids: continue
    s0, s1 = map(float, t.split("-")); f0, f1 = round(s0 * FPS), round(s1 * FPS)
    cp = f"{w}/cuts/{c}.mp4"
    if not os.path.exists(cp) or f1 - f0 < 3: continue
    ks = sorted({f0 + max(1, (f1 - f0) * q // 4) for q in (1, 2, 3)})
    r = [x for x in (noise(cr, k) for k in ks) if x is not None]; o = [x for x in (noise(co, k) for k in ks) if x is not None]
    if not r or not o: continue
    r, o = float(np.median(r)), float(np.median(o)); add = float(np.sqrt(max(r * r - o * o, 0)))
    rows.append((c, r, o, add))
    print(c, "粒 手本", round(r, 2), "うち", round(o, 2), "足す", round(add, 2), flush=True)
    if not a.write or add < 0.15 or add > 1.5: continue  # 🔴 1.5 超えは粒やなく模様（網点・紙・お札）を拾っとる＝足さん（r2 46 で 68 と出た）
    if os.path.exists(cp + ".bak_grain"): print(c, "もう足してある＝飛ばす"); continue
    C = rd(cp); rng = np.random.default_rng(int(c) * 7 + 1)
    # σ0.6 でならすと散らばりが下がる＝先に測って倍率で戻す
    z = cv2.GaussianBlur(rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.6); kz = 1 / z.std()
    # hp（σ2 との差）で測ると σ0.6 の粒は約 0.93 倍に見える
    amp = add / 0.93
    out = []
    for j, f in enumerate(C):
        n1 = cv2.GaussianBlur(rng.standard_normal(f.shape[:2]).astype(np.float32), (0, 0), 0.6) * kz * amp
        nc = cv2.GaussianBlur(rng.standard_normal(f.shape).astype(np.float32), (0, 0), 0.6) * kz * amp * 0.3
        out.append(np.clip(f.astype(np.float32) + n1[..., None] + nc, 0, 255).astype(np.uint8))
    if not os.path.exists(cp + ".bak_grain"): shutil.copy(cp, cp + ".bak_grain")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", GG["FPS_FF"], "-i", "-",
                          "-c:v", "libx264", "-crf", "8", "-tune", "grain", "-pix_fmt", "yuv420p", cp], stdin=subprocess.PIPE)
    p.stdin.write(np.array(out).tobytes()); p.stdin.close(); p.wait()
