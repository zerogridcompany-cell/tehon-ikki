"""今の書き出しから、カットごとに色（色ごとに1次＝ゲイン・オフセット）を手本へ当て直し、今の shot_look に重ねる。
color_fit と違い、点は 640x360 の白黒 SSIM（mane_check と同じ物差し）で見込み、上がるカットだけ入れる。中身を替えたカットの古い色も直る。

python3 look_refit.py <作業> <書き出し.mp4> [--min 0.005] [--dry]
- ゲインは 0.6〜1.6・オフセットは ±0.25 の中だけ。前の shot_look は shot_look.json.bak_refit に控え
"""
import glob
import argparse, json, os, shutil, subprocess, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim


def rgb(p):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-vf", "fps=2997/100,scale=640:360", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, 360, 640, 3)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("out"); ap.add_argument("--min", type=float, default=0.005); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(); w = os.path.abspath(a.w)
    R = rgb(glob.glob(f"{w}/ref/*.mp4")[0]); V = rgb(os.path.join(w, a.out)); n = min(len(R), len(V))
    gray = lambda x: cv2.cvtColor(np.clip(x, 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
    lab = lambda x: cv2.cvtColor(np.uint8([[np.clip(x.reshape(-1, 3).mean(0), 0, 255)]]), cv2.COLOR_RGB2LAB)[0, 0].astype(float) * [100 / 255, 1, 1]
    SL = json.load(open(f"{w}/proj/src/shot_look.json"))
    segs = []
    for l in open(f"{w}/eye/segs.txt"):
        if ":" in l:
            k, v = l.split(":"); s0, s1 = map(float, v.split("-")); segs.append((k.strip(), round(s0 * 29.97), min(n, round(s1 * 29.97))))
    tot = 0; changed = []
    for k, f0, f1 in segs:
        if f1 - f0 < 2: continue
        X = V[f0:f1].astype(np.float32); Y = R[f0:f1].astype(np.float32)
        g, o = [], []
        for c in range(3):
            xs, ys = X[..., c].ravel()[::7], Y[..., c].ravel()[::7]
            A = np.vstack([xs, np.ones_like(xs)]).T; kk, mm = np.linalg.lstsq(A, ys, rcond=None)[0]
            g.append(float(np.clip(kk, 0.6, 1.6))); o.append(float(np.clip(mm / 255, -0.25, 0.25)))
        g = np.array(g); o = np.array(o)
        Z = X * g + o * 255
        s0 = np.mean([ssim(gray(Y[i]), gray(X[i])) for i in range(len(X))]); s1 = np.mean([ssim(gray(Y[i]), gray(Z[i])) for i in range(len(X))])
        d0 = np.mean([np.linalg.norm(lab(Y[i]) - lab(X[i])) for i in range(len(X))]); d1 = np.mean([np.linalg.norm(lab(Y[i]) - lab(Z[i])) for i in range(len(X))])
        if s1 > s0 + a.min and d1 <= d0 + 0.3:
            old = SL.get(k, {})
            g0 = np.array(old.get("g", [1, 1, 1])); o0 = np.array(old.get("o", [0, 0, 0]))
            ng = (g * g0).round(4).tolist(); no = (g * o0 + o).round(4).tolist()
            new = {x: old[x] for x in old if x not in ("g", "o")}; new.update({"f0": f0, "f1": f1 - 1, "g": ng, "o": no})
            SL[k] = new; tot += (s1 - s0) * (f1 - f0); changed.append((k, f1 - f0, round(float(s0), 3), round(float(s1), 3), round(float(d0), 1), round(float(d1), 1)))
    for c in sorted(changed, key=lambda t: -(t[3] - t[2]) * t[1]): print(c)
    print("カット", len(changed), "全体の見込み +", round(tot / n, 4))
    if not a.dry and changed:
        shutil.copy(f"{w}/proj/src/shot_look.json", f"{w}/proj/src/shot_look.json.bak_refit")
        json.dump(SL, open(f"{w}/proj/src/shot_look.json", "w"), indent=1)


if __name__ == "__main__":
    main()
