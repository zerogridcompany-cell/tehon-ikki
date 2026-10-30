"""110 の白い板（Slabs.tsx）のカメラを、手本の白い板の形（明るい所）に合わせて決める。書き出し不要（板の形を手元で投影して重ねる）。

python3 slab_cam_fit.py <作業> --frames 1653,1658,1663,1668,1673 [--out tmp/slab_cam.json]
- 板＝slabs.json の並び・落ちる時刻（Easing.in quad）・形（角を落とした長方形の柱）をそのまま投影（three.js と同じ lookAt・縦の fov）
- 手本の明るい所（白黒 >100）と、投影した板の形の重なり（Dice）を Nelder-Mead で最大に（何回か出発点を変える）
- 出力＝cam の鍵（f・x・y・z・lx・ly・lz・fov）。前の鍵から始めるので動きがつながる
"""
import argparse, glob, json, os, subprocess, sys
import cv2
import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo import geo
W, H = 320, 180   # use_geo(<作業>) で geo の SW・SH に替わる（10/30）
FPS = 29.97


def use_geo(w):
    global W, H, FPS
    G = geo(w); W, H, FPS = G["SW"], G["SH"], G["FPS"]


def ref_mask(ref, f):
    o = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{(f - 0.3) / FPS:.4f}", "-i", ref, "-frames:v", "1", "-vf", f"scale={W}:{H}",
                        "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    g = np.frombuffer(o, np.uint8).reshape(H, W)
    return (g > 100).astype(np.float32)


def octagon(w, d, c):
    return [(-w / 2 + c, -d / 2), (w / 2 - c, -d / 2), (w / 2, -d / 2 + c), (w / 2, d / 2 - c), (w / 2 - c, d / 2), (-w / 2 + c, d / 2), (-w / 2, d / 2 - c), (-w / 2, -d / 2 + c)]


def ease_in_quad(t):
    return t * t


def slab_y(s, f, dropH):
    if s["land"] <= s["drop"]:
        return 0.0
    t = min(1, max(0, (f - s["drop"]) / (s["land"] - s["drop"])))
    return dropH * (1 - ease_in_quad(t))


def render(C, f, p, fov):
    P = np.array(p[:3], float); L = np.array(p[3:6], float)
    fw = L - P; fw /= np.linalg.norm(fw) + 1e-9
    r = np.cross(fw, [0, 1, 0]); r /= np.linalg.norm(r) + 1e-9
    u = np.cross(r, fw)
    th = np.tan(np.radians(fov) / 2); asp = W / H
    oc = octagon(C["slab"]["w"], C["slab"]["d"], C["slab"]["chamfer"]); h = C["slab"]["h"]
    m = np.zeros((H, W), np.uint8)
    for s in C["slabs"]:
        if f < s["drop"]:
            continue
        y0 = slab_y(s, f, C["dropH"])
        pts = []
        for sx, sy in oc:
            for yy in (y0, y0 + h):
                X = np.array([s["x"] + sx, yy, s["z"] - sy]) - P
                zc = X @ fw
                if zc < 0.1:
                    continue
                pts.append(((X @ r) / (zc * th * asp), (X @ u) / (zc * th)))
        if len(pts) < 3:
            continue
        q = np.array([[(x + 1) / 2 * W, (1 - y) / 2 * H] for x, y in pts], np.float32)
        q = np.clip(q, -4 * W, 5 * W)
        cv2.fillConvexPoly(m, cv2.convexHull(q).astype(np.int32), 1)
    return m.astype(np.float32)


def dice(a, b):
    a = cv2.GaussianBlur(a, (0, 0), 1.5); b = cv2.GaussianBlur(b, (0, 0), 1.5)
    return 2 * (a * b).sum() / (a.sum() + b.sum() + 1e-6)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--frames", required=True); ap.add_argument("--out", default="tmp/slab_cam.json"); ap.add_argument("--fov", type=float, default=30)
    a = ap.parse_args()
    use_geo(a.w)
    ref = glob.glob(f"{a.w}/ref/*.mp4")[0]
    C = json.load(open(f"{a.w}/proj/src/slabs.json"))
    starts = [[5, 2.5, 16, 5, 0, -6], [5, 4, 14, 5, 0, -8], [8, 3, 18, 3, 0, -6], [3, 5, 12, 6, 0, -10]]
    prev = None; keys = []
    for f in map(int, a.frames.split(",")):
        R = ref_mask(ref, f)
        best = (9, None)
        # 粗い格子（カメラは前＝+z 側・横向きは小さく）で出発点を選ぶ
        grid = []
        for cx in (0, 2.5, 5, 7.5, 10):
            for cy in (2, 3.5, 5, 7, 9):
                for cz in (8, 12, 16, 20, 26):
                    for lz in (-12, -6, -2):
                        for yaw in (-4, 0, 4):
                            p = [cx, cy, cz, cx + yaw, 0, lz]
                            grid.append((1 - dice(render(C, f, p, a.fov), R), p))
        grid.sort(key=lambda t: t[0])
        cands = [g[1] for g in grid[:4]]
        for x0 in ([prev] if prev is not None else []) + cands:
            res = minimize(lambda p: 1 - dice(render(C, f, p, a.fov), R), x0, method="Nelder-Mead", options={"maxiter": 600, "xatol": 1e-3, "fatol": 1e-4})
            if res.fun < best[0]:
                best = (res.fun, res.x)
        prev = list(best[1])
        keys.append({"f": f, "x": prev[0], "y": prev[1], "z": prev[2], "lx": prev[3], "ly": prev[4], "lz": prev[5], "fov": a.fov})
        cv2.imwrite(f"{a.w}/tmp/slabfit_{f}.png", np.hstack([R, render(C, f, prev, a.fov)]) * 255)
        print(f, "重なり", round(1 - best[0], 3), [round(v, 2) for v in prev], flush=True)
    json.dump(keys, open(f"{a.w}/{a.out}", "w"), indent=1)


if __name__ == "__main__":
    main()
