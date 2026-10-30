"""書き出しをせずに、カット1本（cuts/<番号>.mp4 や試しの動画）を手本の同じコマと比べて点を出す。
全部のカットを手元で採点→良くなった物だけ入れる→最後に1回だけ書き出す（版ごとに書き出さん）。

python3 cut_score.py <作業フォルダ> [--ids 59,93] [--file 59=cuts_try/k59.mp4] [--out tmp/cutscore.json] [--dir 試しの置き場]
- 点＝灰色 640x360 の SSIM（mane_check と同じ物差しに近い）の1コマごとの平均
"""
import argparse, glob, json, os, subprocess
import cv2
import numpy as np

W, H = 640, 360
FPS = 29.97


def frames(p, ss=None, n=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", f"{ss:.4f}"] if ss is not None else []) + ["-i", p]
    cmd += (["-frames:v", str(n)] if n else []) + ["-vf", f"fps=2997/100,scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    r = subprocess.run(cmd, capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W)


def ssim(a, b):
    a = a.astype(np.float32); b = b.astype(np.float32)
    C1, C2 = 6.5, 58.5
    mu1 = cv2.GaussianBlur(a, (7, 7), 1.5); mu2 = cv2.GaussianBlur(b, (7, 7), 1.5)
    s1 = cv2.GaussianBlur(a * a, (7, 7), 1.5) - mu1 ** 2; s2 = cv2.GaussianBlur(b * b, (7, 7), 1.5) - mu2 ** 2
    s12 = cv2.GaussianBlur(a * b, (7, 7), 1.5) - mu1 * mu2
    return float((((2 * mu1 * mu2 + C1) * (2 * s12 + C2)) / ((mu1 ** 2 + mu2 ** 2 + C1) * (s1 + s2 + C2))).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("--ids"); ap.add_argument("--file", action="append", default=[]); ap.add_argument("--out"); ap.add_argument("--dir", help="<dir>/<番号>.mp4 があればそれを採点")
    g = ap.parse_args()
    ref = glob.glob(f"{g.w}/ref/*.mp4")[0]
    shots = sorted(json.load(open(f"{g.w}/eye/out.json"))["shots"], key=lambda s: float(s["t0"]))
    files = dict(x.split("=", 1) for x in g.file)
    ids = g.ids.split(",") if g.ids else [str(s["i"]) for s in shots]
    out = {}
    for j, s in enumerate(shots):
        i = str(s["i"])
        if i not in ids:
            continue
        f0 = int(round(float(s["t0"]) * FPS))
        f1 = int(round(float(shots[j + 1]["t0"]) * FPS)) if j + 1 < len(shots) else f0 + int(round((float(s["t1"]) - float(s["t0"])) * FPS))
        n = f1 - f0
        R = frames(ref, max(0, f0 - 0.3) / FPS, n)
        p = files.get(i, f"{g.dir}/{i}.mp4" if g.dir and os.path.exists(f"{g.dir}/{i}.mp4") else f"{g.w}/cuts/{i}.mp4")
        if os.path.exists(p):
            O = frames(p)[:n]
        else:
            O = np.zeros((0, H, W), np.uint8)
        if len(O) < n:
            O = np.concatenate([O, np.zeros((n - len(O), H, W), np.uint8)])
        sc = [ssim(r, o) for r, o in zip(R, O)]
        out[i] = {"frames": n, "ssim": round(float(np.mean(sc)), 4), "loss": round(float(np.sum(1 - np.array(sc))), 2), "file": p}
        print(i, n, out[i]["ssim"], flush=True)
    if g.out:
        json.dump(out, open(g.out, "w"), indent=1)


if __name__ == "__main__":
    main()
