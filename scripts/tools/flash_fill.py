"""白い光・グレーの拭き取り（切り替えの光）のコマを、手本を 16x9 の色の格子で測って、なめらかな面で埋める。

python3 flash_fill.py <作業> --frames 1715,1716,1717,1727 [--grid 16x9] [--min 0.02]
- 🔴 中身のある絵（写真・人・物）には使わん＝手本のぼかし写しになるだけで作り直しやない（10/27 v35 で 153・180・528・1727・2162 に入って戻した）
- 門＝細かさ（16x9 に縮めて戻した時の差）が 5 未満、かつ 40x40 のどの升目でも細かい形（ぼかしとの差の平均）が 4 未満（小さい物が1つでも写っとったら外す）
- 入れる先は eye/out.json でそのコマを含むカットの cuts/<番号>.mp4（無ければ黒から作る）。SSIM（白黒 640x360）が --min 以上上がった時だけ
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cut_score import ssim

W, H = 1280, 720
FPS = 29.97


def read(p, ss, n):
    o = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, ss):.4f}", "-i", p, "-frames:v", str(n), "-vf", f"fps=2997/100,scale={W}:{H}",
                        "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    return np.frombuffer(o, np.uint8).reshape(-1, H, W, 3)


def g640(x):
    return cv2.resize(cv2.cvtColor(x, cv2.COLOR_BGR2GRAY), (640, 360))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("--frames", required=True); ap.add_argument("--grid", default="16x9"); ap.add_argument("--min", type=float, default=0.02)
    a = ap.parse_args()
    gw, gh = map(int, a.grid.split("x"))
    ref = glob.glob(f"{a.w}/ref/*.mp4")[0]
    shots = json.load(open(f"{a.w}/eye/out.json"))["shots"]
    cache = {}
    for f in map(int, a.frames.split(",")):
        R = read(ref, (f - 0.3) / FPS, 1)[0]
        small = cv2.resize(R, (gw, gh), interpolation=cv2.INTER_AREA)
        fill = cv2.GaussianBlur(cv2.resize(small, (W, H), interpolation=cv2.INTER_CUBIC), (0, 0), 8)
        detail = float(np.abs(fill.astype(np.int16) - R.astype(np.int16)).mean())
        sh = [x for x in shots if int(round(float(x["t0"]) * FPS)) <= f < int(round(float(x["t1"]) * FPS))][0]
        i = str(sh["i"]); c0 = int(round(float(sh["t0"]) * FPS)); n = int(round(float(sh["t1"]) * FPS)) - c0
        if i not in cache:
            cp = f"{a.w}/cuts/{i}.mp4"
            F = read(cp, 0, n)[:n].copy() if os.path.exists(cp) else np.zeros((n, H, W, 3), np.uint8)
            if len(F) < n:
                F = np.concatenate([F, np.zeros((n - len(F), H, W, 3), np.uint8)])
            cache[i] = [F, False]
        F = cache[i][0]
        now = ssim(g640(F[f - c0]), g640(R)); new = ssim(g640(fill), g640(R))
        gy = cv2.cvtColor(R, cv2.COLOR_BGR2GRAY).astype(np.float32); gy[300:420] = gy[300:420].mean()  # 字幕の帯は MG の字＝外す
        hf = np.abs(gy - cv2.GaussianBlur(gy, (0, 0), 6))  # 細かい形（物・人・字）だけが残る
        blk = max(float(hf[y:y + 40, x:x + 40].mean()) for y in range(0, H, 40) for x in range(0, W, 40))
        ok = new > now + a.min and detail < 5 and blk < 4
        print(f, "カット", i, "細かさ", round(detail, 1), "升目の幅", round(blk, 1), round(now, 3), "→", round(new, 3), "入れた" if ok else "そのまま", flush=True)
        if ok:
            F[f - c0] = fill; cache[i][1] = True
    for i, (F, ch) in cache.items():
        if not ch:
            continue
        cp = f"{a.w}/cuts/{i}.mp4"
        if os.path.exists(cp) and not os.path.exists(cp + ".bak_flash"):
            shutil.copy(cp, cp + ".bak_flash")
        tmp = cp + ".tmp.mp4"
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100", "-i", "-",
                              "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        p.stdin.write(F.tobytes()); p.stdin.close(); p.wait()
        shutil.move(tmp, cp); print("書いた", cp)


if __name__ == "__main__":
    main()
