"""元の動画に焼き付いとる別の字幕（白い字）を、字幕の帯の中だけ見つけて周りの絵で埋める（cv2.inpaint）。
python3 decap.py <作業フォルダ> <カット番号> [--y0 280 --y1 470 --out tmp/decap/<番号>.mp4]
- 字＝帯の中で、周りより明るい細い形（tophat）かつ白に近い所。少し太らせて埋める
"""
import argparse, os, subprocess
import cv2
import numpy as np

W, H = 1280, 720


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("--y0", type=int, default=280); ap.add_argument("--y1", type=int, default=470)
    ap.add_argument("--th", type=int, default=60); ap.add_argument("--out")
    g = ap.parse_args()
    src = f"{g.w}/cuts/{g.i}.mp4"; out = g.out or f"{g.w}/tmp/decap/{g.i}.mp4"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    F = np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).copy()
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (31, 31))
    for j, f in enumerate(F):
        gy = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        th = cv2.morphologyEx(gy, cv2.MORPH_TOPHAT, k)
        m = np.zeros((H, W), np.uint8)
        band = (th[g.y0:g.y1] > g.th) & (gy[g.y0:g.y1] > 150)
        m[g.y0:g.y1][band] = 255
        m = cv2.dilate(m, np.ones((7, 7), np.uint8))
        if m.any():
            F[j] = cv2.inpaint(f, m, 6, cv2.INPAINT_TELEA)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", "2997/100", "-i", "-",
                          "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    p.stdin.write(F.tobytes()); p.stdin.close(); p.wait()
    print("書いた", out)


if __name__ == "__main__":
    main()
