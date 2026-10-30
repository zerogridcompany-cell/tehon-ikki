"""うちのカットの左右（上下）に黒い帯が出とるのに、手本はそこまで絵がある所を、隣の絵の折り返し＋ぼかしで埋める（10/27 r2：133・134＝元が細い）。
python3 side_fill.py <作業> <カット番号> [--th 10] [--blur 18] [--out tmp/side/<番号>.mp4] [--write]
- 黒い帯＝そのコマの列（行）の平均が th 未満で端から続く所。手本の同じ所が th 以上の時だけ埋める
- 埋め方＝帯の内側の絵を鏡写し（BORDER_REFLECT）→ 帯の中だけ σblur でぼかす（端ほど強く）→ 境目 12px でなじませる
- --write＝cuts/<番号>.mp4 を置き換え（前の物は .bak_side）
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


def band(prof, th):
    l = 0
    while l < len(prof) // 3 and prof[l] < th: l += 1
    r = len(prof)
    while r > len(prof) * 2 // 3 and prof[r - 1] < th: r -= 1
    return l, r


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("i"); ap.add_argument("--th", type=float, default=10)
    ap.add_argument("--blur", type=float, default=18); ap.add_argument("--out"); ap.add_argument("--write", action="store_true")
    g = ap.parse_args()
    global W, H
    G = geo(g.w); W, H = G["W"], G["H"]
    s = [s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"] if str(s["i"]) == str(g.i)][0]
    f0 = int(round(s["t0"] * G["FPS"])); src = f"{g.w}/cuts/{g.i}.mp4"
    F = rd(src); R = rd(sorted(glob.glob(f"{g.w}/ref/*.mp4"))[0], f0, f0 + len(F))
    out = []
    for j, f in enumerate(F):
        r = R[min(j, len(R) - 1)]
        cl, cr = band(f.mean(axis=(0, 2)), g.th); rl, rr = band(r.mean(axis=(0, 2)), g.th)
        L = cl if cl > rl + 4 else 0; Rr = cr if cr < rr - 4 else W
        if L == 0 and Rr == W: out.append(f); continue
        core = f[:, L:Rr]
        pad = cv2.copyMakeBorder(core, 0, 0, L, W - Rr, cv2.BORDER_REFLECT)
        bl = cv2.GaussianBlur(pad, (0, 0), g.blur).astype(np.float32)
        xs = np.arange(W, dtype=np.float32)
        a = np.clip(np.maximum((L + 12 - xs) / 12, (xs - (Rr - 12)) / 12), 0, 1)[None, :, None]
        o = pad.astype(np.float32) * 0 + f.astype(np.float32)
        o = o * (1 - a) + bl * a
        out.append(np.clip(o, 0, 255).astype(np.uint8))
        if j == 0: print(f"帯 うち {cl}〜{cr}・手本 {rl}〜{rr} → 埋める 0〜{L}・{Rr}〜{W}")
    o = g.out or f"{g.w}/tmp/side/{g.i}.mp4"; os.makedirs(os.path.dirname(o), exist_ok=True)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", G["FPS_FF"], "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", o], stdin=subprocess.PIPE)
    p.stdin.write(np.array(out).tobytes()); p.stdin.close(); p.wait(); print("書いた", o)
    if g.write:
        if not os.path.exists(src + ".bak_side"): shutil.copy(src, src + ".bak_side")
        shutil.copy(o, src); print("置き換えた", src)


if __name__ == "__main__":
    main()
