"""110 の板：並び（縦横）の案ごとに、カメラを手本の明るい形へ合わせ、重なり（Dice）で並び案を選ぶ。
slab_cam_fit.py の投影を使い、カメラは的の周りを全周（方位角・仰角・距離）で探す。

python3 slab_fit2.py <作業> --frames 1653,1658,1663,1668,1673 --dz -3.75 --dx -10.15 [--out tmp/c110/fit_A.json]
- 並び＝2列（z：0, dz）× 行（x：0, dx, 2dx…）。落ちる時刻は slabs.json の順のまま
"""
import argparse, glob, json, os, sys
import numpy as np
from scipy.optimize import minimize
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slab_cam_fit import ref_mask, render, dice
import cv2


def layout(C, dz, dx):
    S = C["slabs"]
    for i, s in enumerate(S):
        s["x"] = round((i // 2) * dx, 3); s["z"] = round((i % 2) * dz, 3)
    return C


def cam_from(az, el, dist, tx, tz):
    a, e = np.radians(az), np.radians(el)
    return [tx + dist * np.cos(e) * np.sin(a), dist * np.sin(e), tz + dist * np.cos(e) * np.cos(a), tx, 0, tz]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--frames", required=True)
    ap.add_argument("--dz", type=float, required=True); ap.add_argument("--dx", type=float, required=True)
    ap.add_argument("--fov", type=float, default=30); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ref = glob.glob(f"{a.w}/ref/*.mp4")[0]
    C = layout(json.load(open(f"{a.w}/proj/src/slabs.json")), a.dz, a.dx)
    prev = None; keys = []; tot = 0
    for f in map(int, a.frames.split(",")):
        R = ref_mask(ref, f)
        grid = []
        for az in range(0, 360, 20):
            for el in (6, 12, 20, 30):
                for dist in (12, 18, 26):
                    for tx in (0, a.dx, 2 * a.dx):
                        p = cam_from(az, el, dist, tx, a.dz / 2)
                        grid.append((1 - dice(render(C, f, p, a.fov), R), p))
        grid.sort(key=lambda t: t[0])
        best = (9, None)
        for x0 in ([prev] if prev is not None else []) + [g[1] for g in grid[:4]]:
            res = minimize(lambda p: 1 - dice(render(C, f, p, a.fov), R), x0, method="Nelder-Mead", options={"maxiter": 600, "xatol": 1e-3, "fatol": 1e-4})
            if res.fun < best[0]:
                best = (res.fun, res.x)
        prev = list(best[1]); tot += 1 - best[0]
        keys.append({"f": f, "x": prev[0], "y": prev[1], "z": prev[2], "lx": prev[3], "ly": prev[4], "lz": prev[5], "fov": a.fov})
        cv2.imwrite(os.path.splitext(a.out)[0] + f"_{f}.png", np.hstack([R, render(C, f, prev, a.fov)]) * 255)
        print(f, "重なり", round(1 - best[0], 3), [round(v, 2) for v in prev], flush=True)
    json.dump({"dz": a.dz, "dx": a.dx, "mean": tot / len(keys), "slabs": C["slabs"], "cam": keys}, open(a.out, "w"), indent=1)
    print("平均", round(tot / len(keys), 3))


if __name__ == "__main__":
    main()
