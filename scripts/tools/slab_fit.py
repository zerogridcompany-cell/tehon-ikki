"""3D の板の場面（Slabs.tsx）のカメラを、手本の1コマに合わせる。白い板の形（明るい所）の重なり（IoU）が一番良い所を探す。

python3 slab_fit.py <proj> <手本のコマ jpg> <コマ番号> [--key k]
- カメラは「見る先（lx,ly,lz）」の周りの球の上：距離 dist・見下ろす角 el・横の回り az・画角 fov
- slabs.json の cam[k]（既定は全部）を書き換えて remotion still で描き、IoU を比べる（座標の降り方）
"""
import argparse, json, math, os, subprocess
import cv2
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("proj"); ap.add_argument("ref"); ap.add_argument("frame", type=int)
ap.add_argument("--key", type=int); ap.add_argument("--iters", type=int, default=3)
g = ap.parse_args()
cfgp = f"{g.proj}/src/slabs.json"
out = "/private/tmp/claude-501/-Users-USER/08108b8f-776e-4cad-acdd-edef8a467f67/scratchpad/slabfit.png"
ref = cv2.cvtColor(cv2.imread(g.ref), cv2.COLOR_BGR2GRAY)
rm = ref > 150
rm[:130, :260] = False  # 左上の札は外す
# 字幕の帯は外す（字は Remotion の字幕が重なる）
band = np.zeros_like(rm); band[300:400] = True


def to_cam(p):
    el, az = math.radians(p["el"]), math.radians(p["az"])
    return {"x": p["lx"] + p["dist"] * math.cos(el) * math.sin(az), "y": p["ly"] + p["dist"] * math.sin(el),
            "z": p["lz"] + p["dist"] * math.cos(el) * math.cos(az), "lx": p["lx"], "ly": p["ly"], "lz": p["lz"], "fov": p["fov"]}


def score(p):
    C = json.load(open(cfgp))
    cam = to_cam(p)
    for i, k in enumerate(C["cam"]):
        if g.key is None or i == g.key:
            k.update(cam)
    json.dump(C, open(cfgp, "w"), indent=1)
    subprocess.run(["npx", "remotion", "still", "src/index.ts", "R2", out, f"--frame={g.frame}", "--gl=angle"],
                   cwd=g.proj, capture_output=True)
    b = cv2.cvtColor(cv2.imread(out), cv2.COLOR_BGR2GRAY) > 150
    b[:130, :260] = False
    m = ~band
    return float((rm & b & m).sum()) / max(1, float(((rm | b) & m).sum()))


p = json.loads(os.environ.get("SLAB_P", "{\"dist\": 22, \"el\": 25, \"az\": 15, \"lx\": 0, \"ly\": 0, \"lz\": 0, \"fov\": 30}"))
best = score(p)
print("始め", round(best, 3))
steps = {"dist": 4.0, "el": 5.0, "az": 8.0, "lx": 1.5, "lz": 1.5, "fov": 5.0}
for it in range(g.iters):
    for k, st in steps.items():
        for sgn in (1, -1):
            while True:
                q = dict(p); q[k] += sgn * st
                v = score(q)
                if v > best + 1e-3:
                    best, p = v, q
                    print(k, round(q[k], 2), round(v, 3), flush=True)
                else:
                    break
    steps = {k: v / 2 for k, v in steps.items()}
score(p)
print("最後", round(best, 3), json.dumps(p))
json.dump({"frame": g.frame, "iou": best, "p": p}, open(f"{g.proj}/src/slabfit_{g.frame}.json", "w"))
