"""手本の「1コマだけ白く光る」所（反転の絵・光の差し込み）を見つけて、Flash 層（proj/src/flash.json＋public/flash/）で埋める。
python3 flash_auto.py <作業> <書き出し.mp4> [--comp Main] [--min 0.05]
- 見つけ方：手本の明るさ >150 で、うちが 40 以上暗いコマ（r2 で 528・532・1727・1782・1788・1440・23・1448・1687 など）
- 候補（全部うちの絵から作る・手本の画素は使わん）：①前後8コマのうちの絵（字幕を外して書き出し）を白黒反転＋色の1次合わせ ②そのまま＋色合わせ ③今のコマに横の傾きの白い光（wash）
- 一番 SSIM の高い候補が、今より --min 以上良い時だけ入れる。前の flash.json は flash.json.bak_auto
- 🔴 土台（base.mp4）には Remotion の層（一枚絵・カード）が入っとらん＝反転の元は字幕を外した書き出し（--props '{"off":["caps"]}'）から
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import frames, ssim
import cut_score
from geo import geo, half
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("out"); ap.add_argument("--comp", default="Main"); ap.add_argument("--min", type=float, default=0.05)
a = ap.parse_args(); w = os.path.abspath(a.w); cut_score.use_geo(w); G = geo(w); W, H = G["W"], G["H"]; MW, MH = half(w)
ref = glob.glob(f"{w}/ref/*.mp4")[0]
Rg = frames(ref); Vg = frames(os.path.join(w, a.out)); n = min(len(Rg), len(Vg))
mr = Rg[:n].reshape(n, -1).mean(1); mo = Vg[:n].reshape(n, -1).mean(1)
hit = [f for f in range(n) if mr[f] > 150 and mo[f] < mr[f] - 40]
print("白く光るのにうちが暗いコマ", hit)
if not hit: sys.exit(0)
def rd_range(p, s, e):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", f"fps={G['FPS_FF']},select='between(n\\,{s}\\,{e})',scale={W}:{H}", "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    fr = np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3); return {s + i: fr[i] for i in range(len(fr))}
def colfit(img, refim):
    o = img.astype(np.float32).copy()
    for c in range(3):
        x, y = o[..., c].ravel()[::5], refim[..., c].astype(np.float32).ravel()[::5]
        k, b = np.polyfit(x, y, 1); o[..., c] = o[..., c] * k + b
    return np.clip(o, 0, 255).astype(np.uint8)
g = lambda x: cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (MW, MH))
os.makedirs(f"{w}/proj/public/flash", exist_ok=True); os.makedirs(f"{w}/tmp", exist_ok=True)
FJ = f"{w}/proj/src/flash.json"; fl = json.load(open(FJ)) if os.path.exists(FJ) else []
if os.path.exists(FJ): shutil.copy(FJ, FJ + ".bak_auto")
done = {}
for f in hit:
    s, e = max(0, f - 8), min(n - 1, f + 8); nc = f"{w}/tmp/flash_nocap_{s}.mp4"
    if not os.path.exists(nc):
        subprocess.run(["npx", "remotion", "render", "src/index.ts", a.comp, nc, "--muted", "--gl=angle", "--concurrency=3", f"--frames={s}-{e}", '--props={"off":["caps"]}'], cwd=f"{w}/proj", capture_output=True)
    if not os.path.exists(nc): print(f, "字幕なしの書き出しに失敗"); continue
    B = {s + i: im for i, im in enumerate(rd_range(nc, 0, e - s).values())}
    R = rd_range(ref, f, f)[f]; O = rd_range(os.path.join(w, a.out), f, f)[f]
    cur = ssim(g(R), g(O)); best = (cur, None, None)
    for k, im in B.items():
        if k in hit: continue
        for inv in (True, False):
            c = colfit(255 - im if inv else im, R); sc = ssim(g(R), g(c))
            if sc > best[0]: best = (sc, c, f"{'反転' if inv else 'そのまま'} {k}")
    # 光の差し込み：列ごとの白の濃さを1次で
    tr, qo = R.mean((0, 2)), O.astype(np.float32).mean((0, 2)); al = np.clip((tr - qo) / np.maximum(255 - qo, 1), 0, 1)
    x = np.arange(W) / W; kk, bb = np.polyfit(x, al, 1); A = np.clip(bb + kk * x, 0, 1)[None, :, None]
    wash = np.clip((1 - A) * O + A * 255, 0, 255).astype(np.uint8); sc = ssim(g(R), g(wash))
    if sc > best[0]: best = (sc, "wash", [round(float(np.clip(bb, 0, 1)), 3), round(float(np.clip(bb + kk, 0, 1)), 3)])
    print(f, "今", round(float(cur), 3), "→", round(float(best[0]), 3), best[2] if best[1] is not None else "そのまま")
    if best[1] is None or best[0] < cur + a.min: continue
    if isinstance(best[1], str): done[f] = {"f": f, "wash": best[2]}
    else:
        cv2.imwrite(f"{w}/proj/public/flash/{f}.png", best[1]); done[f] = {"f": f, "src": f"flash/{f}.png"}
fl = [x for x in fl if x["f"] not in done] + list(done.values())
json.dump(sorted(fl, key=lambda x: x["f"]), open(FJ, "w"), indent=1); print("入れたコマ", len(done))
