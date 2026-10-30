"""画像検索で取れた写真を、当てる道具に乗る形（数秒の動画）にして hi_img.json を作る。

python3 photo_clips.py <作業フォルダ> [--min 30]
- shirabe/img/<番号>.json の best（目印 min 以上）の画像 → src/photo/<番号>.mp4（4秒・30fps・元の大きさ）
- match.py で重ね方を出し、fit_cut.py --hi src/hi_img.json で使える形に書く
"""
import argparse, glob, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("--min", type=int, default=30)
g = ap.parse_args()
ref = glob.glob(f"{g.w}/ref/*.mp4")[0]
shots = {s["i"]: s for s in json.load(open(f"{g.w}/eye/out.json"))["shots"]}
od = f"{g.w}/src/photo"; os.makedirs(od, exist_ok=True)
out = {}
for p in sorted(glob.glob(f"{g.w}/shirabe/img/*.json")):
    d = json.load(open(p)); b = d.get("best")
    if not b or b["inliers"] < g.min:
        continue
    # 白黒の写しを選ばん：目印が一番の 60% 以上ある中で、色の濃さ（彩度）があって大きい物
    import cv2, numpy as np
    pool = [c for c in d.get("checked", []) if c["inliers"] >= max(g.min, 0.6 * b["inliers"]) and os.path.exists(c["file"])]
    def sat_area(c):
        im = cv2.imread(c["file"])
        if im is None:
            return (0, 0)
        sat = float(cv2.cvtColor(im, cv2.COLOR_BGR2HSV)[..., 1].mean())
        return (sat > 25, im.shape[0] * im.shape[1])
    if pool:
        b = max(pool, key=sat_area)
    i = d["i"]; s = shots[i]
    f = f"{od}/{i}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", b["file"], "-t", "4", "-r", "30",
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-pix_fmt", "yuv420p", "-c:v", "libx264", "-crf", "12", f])
    r = subprocess.run([sys.executable, f"{HERE}/match.py", ref, str(s["t0"]), str(s["t1"]), f, "--out", f"{od}/{i}.json"],
                       capture_output=True, text=True)
    try:
        m = json.load(open(f"{od}/{i}.json"))
    except Exception:
        print(i, "当たらんかった"); continue
    if not m.get("found"):
        print(i, "当たらんかった"); continue
    out[str(i)] = {"id": None, "url": b["img"], "page": b.get("page"), "start": 1.0, "clip_start": 0.0, "flip": m["flip"],
                   "ssim": m["ssim"], "inliers": m["inliers"], "H": m["H"], "file": f, "height": b.get("size")}
    print(i, "ssim", m["ssim"], "inliers", m["inliers"], flush=True)
json.dump(out, open(f"{g.w}/src/hi_img.json", "w"), indent=1)
