"""cuts/<番号>.mp4 を手本のカットの順に並べて1本にする（まだ無いカットは黒）。

python3 assemble.py <作業フォルダ> <出す名前> [--stack]
- 長さ・コマ数は手本と同じ（カットの境目は手本のコマ番号に丸める）
- --stack：上＝手本・下＝こっち の比べる版も作る（<出す名前>_比べ.mp4）
- 音は手本の音（社内の練習用・外に出さん）
- 一覧＝<出す名前>.json（カットごとに 有り/黒・SSIM）
"""
import argparse, glob, json, os, subprocess
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("w"); ap.add_argument("name"); ap.add_argument("--stack", action="store_true")
g = ap.parse_args()
ref = glob.glob(f"{g.w}/ref/*.mp4")[0]
pr = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height,r_frame_rate,nb_frames", "-of", "json", ref],
                               capture_output=True, text=True).stdout)["streams"][0]
rw, rh, fps = pr["width"], pr["height"], pr["r_frame_rate"]
a, b = fps.split("/"); fpsf = float(a) / float(b)
total = int(pr["nb_frames"])
shots = sorted(json.load(open(f"{g.w}/eye/out.json"))["shots"], key=lambda s: float(s["t0"]))
allr = json.load(open(f"{g.w}/cuts/_all.json")) if os.path.exists(f"{g.w}/cuts/_all.json") else {}
out = f"{g.w}/{g.name}.mp4"
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{rw}x{rh}", "-r", fps,
                        "-i", "-", "-i", ref, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "16",
                        "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out], stdin=subprocess.PIPE)
rep, done = [], 0
for j, s in enumerate(shots):
    f0 = int(round(float(s["t0"]) * fpsf))
    f1 = int(round(float(shots[j + 1]["t0"]) * fpsf)) if j + 1 < len(shots) else total
    n = max(0, f1 - max(f0, done))
    if n == 0:
        continue
    p = f"{g.w}/cuts/{s['i']}.mp4"
    fr = None
    if os.path.exists(p):
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
        fr = np.frombuffer(r.stdout, np.uint8).reshape(-1, rh, rw, 3)
    blk = np.zeros((rh, rw, 3), np.uint8)
    for k in range(n):
        enc.stdin.write((fr[min(k, len(fr) - 1)] if fr is not None and len(fr) else blk).tobytes())
    done += n
    v = allr.get(str(s["i"]), {})
    rep.append({"i": s["i"], "t0": s["t0"], "frames": n, "kind": s.get("kind"), "have": fr is not None,
                "ssim": v.get("ssim_color")})
enc.stdin.close(); enc.wait()
json.dump(rep, open(f"{g.w}/{g.name}.json", "w"), indent=1)
have = sum(x["frames"] for x in rep if x["have"])
print(f"{out}  コマ {done}/{total}・埋まった {have}/{done}（{100 * have / max(1, done):.0f}%）")
if g.stack:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ref, "-i", out, "-filter_complex",
                    "[0:v]scale=960:-2[a];[1:v]scale=960:-2[b];[a][b]vstack=inputs=2[v]", "-map", "[v]", "-map", "0:a?",
                    "-c:v", "libx264", "-crf", "18", "-c:a", "aac", f"{g.w}/{g.name}_比べ.mp4"])
    print(f"{g.w}/{g.name}_比べ.mp4")
