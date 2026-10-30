"""手本の端（上下の帯・左右の柱）が黒いのに、うちのカットに絵や色が出とる所を黒（手本の帯の色）にする。

python3 edge_black.py <作業> --ids 67,125 [--th 18] [--min 0.003]
- 1コマずつ：手本の行・列の平均の明るさが th 未満で、端から続いとる帯だけ（真ん中の暗い所は触らん）
- カットの SSIM（白黒 640x360）が --min 以上上がった時だけ書く。前の物は .bak_edge
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim

W, H, FPS = 1280, 720, 29.97


def read(p, ss, n):
    o = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, ss):.4f}", "-i", p, "-frames:v", str(n), "-vf", f"fps=2997/100,scale={W}:{H}",
                        "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    return np.frombuffer(o, np.uint8).reshape(-1, H, W, 3).copy()


def run_len(dark):
    a = 0
    while a < len(dark) and dark[a]:
        a += 1
    b = 0
    while b < len(dark) and dark[len(dark) - 1 - b]:
        b += 1
    return a, b


def g(x):
    return cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (640, 360))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("--ids", required=True); ap.add_argument("--th", type=float, default=18); ap.add_argument("--min", type=float, default=0.003)
    a = ap.parse_args()
    ref = glob.glob(f"{a.w}/ref/*.mp4")[0]
    shots = {str(s["i"]): s for s in json.load(open(f"{a.w}/eye/out.json"))["shots"]}
    for i in a.ids.split(","):
        cp = f"{a.w}/cuts/{i}.mp4"
        if not os.path.exists(cp):
            print(i, "カット無し"); continue
        s = shots[i]; f0 = int(round(float(s["t0"]) * FPS)); n = int(round(float(s["t1"]) * FPS)) - f0
        R = read(ref, (f0 - 0.3) / FPS, n); O = read(cp, 0, n); n = min(len(R), len(O))
        before = np.mean([ssim(g(O[k]), g(R[k])) for k in range(n)])
        N = O[:n].copy()
        for k in range(n):
            gy = cv2.cvtColor(R[k], cv2.COLOR_BGR2GRAY).astype(np.float32)
            gy[300:420] = 255  # 字幕の帯は数えん
            t, b = run_len(gy.mean(1) < a.th); l, r = run_len(gy.mean(0) < a.th)
            m = np.zeros((H, W), bool)
            if t < H // 3: m[:t] = True
            if b < H // 3: m[H - b:] = True
            if l < W // 3: m[:, :l] = True
            if r < W // 3: m[:, W - r:] = True
            if m.any():
                N[k][m] = np.median(R[k][m], axis=0).astype(np.uint8)
        after = np.mean([ssim(g(N[k]), g(R[k])) for k in range(n)])
        ok = after > before + a.min
        print(i, round(before, 4), "→", round(after, 4), "書いた" if ok else "そのまま", flush=True)
        if ok:
            if not os.path.exists(cp + ".bak_edge"):
                shutil.copy(cp, cp + ".bak_edge")
            p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100", "-i", "-",
                                  "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", cp + ".tmp.mp4"], stdin=subprocess.PIPE)
            p.stdin.write(N.tobytes()); p.stdin.close(); p.wait(); shutil.move(cp + ".tmp.mp4", cp)


if __name__ == "__main__":
    main()
