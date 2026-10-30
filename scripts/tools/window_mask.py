"""黒地の中の「窓」に映像が入るカット（窓が開く・広がる・細い縦の帯）を、手本の各コマから窓の位置を測って切り抜く。

python3 window_mask.py <作業フォルダ> <カット番号> <合わせた動画.mp4> [--out cuts/<番号>.mp4] [--th 20]
- 窓＝手本のコマで明るさ th より上の画素を、大きい窓で開いて（字幕の細い字を消して）残った所の外接の箱
- 窓が無いコマ（黒の一瞬）は黒。外接の箱の中が7割以上詰まっとらん物（字幕の光）は窓にせん
- 合わせた動画（fit_cut --model sim 等）の窓の外を黒にして書く。前の cuts/<番号>.mp4 は .bak_win に控え
"""
import argparse, glob, json, os, shutil, subprocess
import cv2
import numpy as np


def read(p, t0, n, w, h, fps):
    a = ["ffmpeg", "-v", "error"] + (["-ss", f"{t0:.4f}"] if t0 is not None else []) + ["-i", p, "-frames:v", str(n),
         "-vf", f"fps={fps},scale={w}:{h}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    r = subprocess.run(a, capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, h, w, 3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("fit"); ap.add_argument("--out"); ap.add_argument("--th", type=float, default=20); ap.add_argument("--black", default="", help="黒にするコマ番号（カットの頭から・例 0,1）＝字幕の光だけのコマ")
    g = ap.parse_args()
    ref = glob.glob(f"{g.w}/ref/*.mp4")[0]
    shot = [s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"] if str(s["i"]) == g.i][0]
    t0, t1 = float(shot["t0"]), float(shot["t1"])
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                         "-of", "json", ref], capture_output=True, text=True)
    st = json.loads(pr.stdout)["streams"][0]
    W, H, fps = st["width"], st["height"], st["r_frame_rate"]
    a, b = fps.split("/"); fpsf = float(a) / float(b)
    n = int(round((t1 - t0) * fpsf))
    R = read(ref, t0, n, W, H, fps)
    C = read(g.fit, None, n, W, H, fps)
    n = min(len(R), len(C))
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (31, 31))
    boxes = []
    for j in range(n):
        m = (cv2.cvtColor(R[j], cv2.COLOR_BGR2GRAY) > g.th).astype(np.uint8)
        m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k)
        ys, xs = np.nonzero(m)
        if len(xs) < 400:
            boxes.append(None); continue
        bx = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        # 窓は中が詰まっとる。字幕の光（中がすかすか）は窓にせん
        fill = m[bx[1]:bx[3], bx[0]:bx[2]].mean()
        boxes.append(bx if fill >= 0.7 else None)
    for j in [int(x) for x in g.black.split(",") if x]:
        if j < len(boxes):
            boxes[j] = None
    out = g.out or f"{g.w}/cuts/{g.i}.mp4"
    if os.path.exists(out) and not os.path.exists(out + ".bak_win"):
        shutil.copy(out, out + ".bak_win")
    tmp = out + ".tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", fps,
                          "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for j in range(n):
        f = np.zeros_like(C[j])
        # 窓の外は手本の地の色（暗い紫など）。窓の無いコマも同じ
        f[:] = np.median(np.concatenate([R[j][:20].reshape(-1, 3), R[j][-20:].reshape(-1, 3)]), axis=0).astype(np.uint8)
        if boxes[j]:
            x0, y0, x1, y1 = boxes[j]
            f[y0:y1, x0:x1] = C[j][y0:y1, x0:x1]
        p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait()
    shutil.move(tmp, out)
    print(g.i, "窓", [b if b is None else f"{b[2]-b[0]}x{b[3]-b[1]}" for b in boxes[::max(1, n // 6)]], "→", out)


if __name__ == "__main__":
    main()
