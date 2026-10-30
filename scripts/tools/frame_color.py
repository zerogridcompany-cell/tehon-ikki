"""カットの色（明るさ・コントラスト）を、コマごとに色ごとの1次（ゲイン・オフセット）で手本へ合わせ、時間でならしてかける（10/28 r2：生成で埋めたカットが手本より薄い）。
python3 frame_color.py <作業> <カット番号> [--smooth 5] [--write]
- 字幕の帯（y 300〜400）は外して測る。ゲイン 0.5〜2.5・オフセット ±0.4 の中
- 手本の画素は写さん（1コマ6つの数だけ）
- 前の物は .bak_fc
"""
import argparse, glob, json, os, shutil, subprocess, sys
import cv2, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import geo, half
W, H = 1280, 720   # main で geo(<作業>) に替わる（10/30）


def rd(p, a=None, b=None):
    vf = ["-vf", f"select=between(n\\,{a}\\,{b - 1})", "-vsync", "0"] if a is not None else []
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", p] + vf + ["-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W, 3).copy()


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("--smooth", type=int, default=5); ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    global W, H
    G = geo(a.w); W, H = G["W"], G["H"]
    s = [s for s in json.load(open(f"{a.w}/eye/out.json"))["shots"] if str(s["i"]) == str(a.i)][0]
    f0 = int(round(s["t0"] * G["FPS"])); src = f"{a.w}/cuts/{a.i}.mp4"
    F = rd(src); R = rd(sorted(glob.glob(f"{a.w}/ref/*.mp4"))[0], f0, f0 + len(F)); n = min(len(F), len(R))
    m = np.ones((H, W), bool); m[round(300 * H / 720):round(400 * H / 720)] = False  # 字幕の帯（r2 の 300〜400 行）を高さの比で
    P = []
    for j in range(n):
        p = []
        for c in range(3):
            x = cv2.resize(F[j], (G["SW"], G["SH"]))[..., c].astype(np.float32)[cv2.resize(m.astype(np.uint8), (G["SW"], G["SH"])) > 0] / 255
            y = cv2.resize(R[j], (G["SW"], G["SH"]))[..., c].astype(np.float32)[cv2.resize(m.astype(np.uint8), (G["SW"], G["SH"])) > 0] / 255
            if x.std() < 1e-3: p += [1.0, 0.0]; continue
            k, b = np.polyfit(x, y, 1); p += [float(np.clip(k, 0.5, 2.5)), float(np.clip(b, -0.4, 0.4))]
        P.append(p)
    P = np.array(P); k = a.smooth
    Ps = np.array([P[max(0, i - k // 2):i + k // 2 + 1].mean(0) for i in range(n)])
    out = list(F)
    for j in range(n):
        o = F[j].astype(np.float32) / 255
        for c in range(3): o[..., c] = o[..., c] * Ps[j, 2 * c] + Ps[j, 2 * c + 1]
        out[j] = np.clip(o * 255, 0, 255).astype(np.uint8)
    o = f"{a.w}/tmp/fc/{a.i}.mp4"; os.makedirs(os.path.dirname(o), exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", G["FPS_FF"], "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", o], stdin=subprocess.PIPE)
    p.stdin.write(np.array(out).tobytes()); p.stdin.close(); p.wait(); print("書いた", o, "ゲインの中央値", np.median(Ps[:, ::2], 0).round(2))
    if a.write:
        if not os.path.exists(src + ".bak_fc"): shutil.copy(src, src + ".bak_fc")
        shutil.copy(o, src); print("置き換えた", src)


if __name__ == "__main__":
    main()
